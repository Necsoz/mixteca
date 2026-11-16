"""Músicas repetidas: a pasta de origem nova tem músicas que já foram organizadas antes no mesmo destino.

O que já está no destino vem dos registros do próprio programa (.organizador/indice.json do destino e da pasta
Melhoradas). Duas músicas são a mesma quando artista e título batem e a duração é quase igual (versões com duração
diferente, como Extended e Radio Edit, contam como músicas diferentes). Para cada repetida o programa sugere ficar
com a de melhor qualidade; o usuário pode escolher outra coisa. Nada é apagado: o que é trocado vai para a pasta
"Substituídas" dentro do destino.
"""
import re
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import casamento
from .generos import artista_principal

ESCOLHAS = ("destino", "nova", "ambas")   # manter a que já está no destino / trocar pela nova / manter as duas
PASTAS_SUBSTITUIDAS = ("Substituídas", "Replaced")   # nos dois idiomas da tela
TOLERANCIA_S = 3.0
_SEM_PERDAS = {"flac", "alac", "wav", "pcm_s16le", "pcm_s24le", "aiff", "ape", "wavpack"}
_PREFIXO = re.compile(r"^(?:\d{3} - )?(?:\d{2}[AB] - )?")       # "128 - 08A - " que o programa põe no nome
_VERSAO_PADRAO = re.compile(r"[\(\[]\s*(?:original|extended|radio|club|album|single)?\s*(?:mix|edit|version)\s*[\)\]]", re.I)


def _chave_titulo(titulo: str) -> str:
    """Título comparável: sem "(Original Mix)" e afins, mas mantendo remix/bootleg/VIP (são outras músicas)."""
    return casamento.norm(_VERSAO_PADRAO.sub(" ", titulo or ""), tirar_versao=False)


def _do_nome(arquivo: Path) -> tuple[str, str]:
    """Artista e título a partir do nome que o programa deu à cópia ("128 - 08A - Artista - Título.mp3")."""
    stem = _PREFIXO.sub("", arquivo.stem)
    stem = re.sub(r" \(\d+\)$", "", stem)
    artista, sep, titulo = stem.partition(" - ")
    return (artista, titulo) if sep else ("", stem)


def existentes(destino, pasta_melhoradas) -> list[dict]:
    """O que o programa já colocou no destino, agrupado pelo original de onde veio cada cópia."""
    from .planejador import _carregar_indice
    destino, melh = Path(destino), Path(pasta_melhoradas)
    por_origem: dict[str, dict] = {}
    for pasta, tipo in ((destino, "copia"), (melh, "melhorada")):
        if not (pasta / ".organizador").is_dir():
            continue
        for origem, dados in _carregar_indice(pasta).items():
            rel = dados.get("rel")
            if not rel or set(PASTAS_SUBSTITUIDAS) & set(Path(rel).parts):
                continue
            arq = pasta / rel
            if not arq.is_file():
                continue
            e = por_origem.setdefault(origem, {"origem_antiga": origem, "copia": None, "melhorada": None, "tags": None})
            e[tipo] = str(arq)
            if tipo == "copia" and isinstance(dados.get("tags"), dict):
                e["tags"] = dados["tags"]
    return list(por_origem.values())


def _qualidade(info: dict | None, faixa=None) -> dict:
    """Resumo comparável da qualidade: sem perdas, corte de agudos (quando analisado) e kbps."""
    info = info or {}
    codec = (faixa.codec if faixa else "") or info.get("codec") or ""
    kbps = (faixa.bitrate_kbps if faixa else None) or info.get("bitrate_kbps")
    corte = faixa.corte_hz if faixa else None
    return {"sem_perdas": codec.lower() in _SEM_PERDAS, "kbps": kbps, "corte_hz": corte, "codec": codec,
            "baixa": bool(faixa.qualidade_baixa) if faixa else None}


def comparar(a: dict, b: dict) -> int:
    """>0 se `a` tem qualidade melhor, <0 se `b` tem, 0 se não dá para dizer (parecidas)."""
    if a["sem_perdas"] != b["sem_perdas"]:
        return 1 if a["sem_perdas"] else -1
    if a.get("corte_hz") and b.get("corte_hz") and abs(a["corte_hz"] - b["corte_hz"]) >= 1000:
        return 1 if a["corte_hz"] > b["corte_hz"] else -1
    ka, kb = a.get("kbps") or 0, b.get("kbps") or 0
    if ka and kb and abs(ka - kb) >= 0.1 * max(ka, kb):
        return 1 if ka > kb else -1
    return 0


def detectar(itens, por_caminho: dict, ja_existe: list[dict], ler_info, faixa_antiga=None) -> list[dict]:
    """Acha as músicas da origem atual que já estão no destino.

    itens: plano da organização atual (tags finais de cada música); por_caminho: {caminho: Faixa};
    ler_info(caminho) -> {"titulo","artista","duracao","bitrate_kbps","codec"} (FFprobe);
    faixa_antiga(caminho) -> Faixa analisada do original antigo, se ainda existir (melhor medida de qualidade)."""
    atuais = {i.origem for i in itens}
    candidatos: dict[str, list[dict]] = {}
    for e in ja_existe:
        if e["origem_antiga"] in atuais:   # é a mesma música da mesma origem (organizar de novo), não repetida
            continue
        t = e.get("tags") or {}
        artista, titulo = (t.get("artista") or "", t.get("titulo") or "")
        if not titulo:
            artista, titulo = _do_nome(Path(e["copia"] or e["melhorada"]))
        e = {**e, "artista": artista, "titulo": titulo}
        candidatos.setdefault(_chave_titulo(titulo), []).append(e)

    pares = []
    for it in itens:
        tags = it.tags or {}
        titulo, artista = tags.get("titulo") or "", tags.get("artista") or ""
        chave = _chave_titulo(titulo)
        for e in candidatos.get(chave, []) if chave else []:
            if casamento.sim_artistas(artista_principal(artista) or artista, e["artista"]) >= 0.8 or \
                    casamento.sim_artistas(artista, e["artista"]) >= 0.8:
                pares.append((it, e))

    # só os candidatos que bateram pelo nome são lidos do disco (duração e qualidade)
    arquivos = {p for _, e in pares for p in ([e["origem_antiga"]] if Path(e["origem_antiga"]).is_file() else []) + [e["copia"] or e["melhorada"]]}
    with ThreadPoolExecutor(max_workers=6) as pool:
        lidos = dict(zip(arquivos, pool.map(lambda p: _ler(ler_info, p), arquivos)))

    saida, usados = [], set()
    for it, e in pares:
        f = por_caminho.get(it.origem)
        if f is None or it.origem in usados:
            continue
        orig_ok = Path(e["origem_antiga"]).is_file()
        ref = lidos.get(e["origem_antiga"]) if orig_ok else None
        ref = ref or lidos.get(e["copia"] or e["melhorada"]) or {}
        dur = ref.get("duracao") or 0
        if f.duracao and dur and abs(f.duracao - dur) > TOLERANCIA_S:
            continue
        antiga = faixa_antiga(e["origem_antiga"]) if (faixa_antiga and orig_ok) else None
        # qualidade do que está no destino: do original antigo (se existir) ou da cópia; a melhorada foi recodificada,
        # então os kbps dela não dizem a qualidade de verdade
        so_melhorada = not orig_ok and not e["copia"]
        q_dest = _qualidade(ref, antiga)
        q_nova = _qualidade(None, f)
        cmp = 0 if so_melhorada else comparar(q_nova, q_dest)
        usados.add(it.origem)
        saida.append({
            "caminho": it.origem, "nome": it.nome or Path(it.origem).stem,
            "nova": {"arquivo": Path(it.origem).name, "duracao": f.duracao, **q_nova},
            "destino": {"copia": e["copia"], "melhorada": e["melhorada"], "origem_antiga": e["origem_antiga"],
                        "arquivo": Path(e["copia"] or e["melhorada"]).name, "duracao": dur, "so_melhorada": so_melhorada, **q_dest},
            "sugestao": "nova" if cmp > 0 else "destino",
            "motivo": "melhor" if cmp > 0 else ("pior" if cmp < 0 else ("desconhecida" if so_melhorada else "parecida")),
        })
    return saida


def _ler(ler_info, caminho):
    try:
        return ler_info(caminho)
    except Exception:  # noqa: BLE001 - arquivo ilegível: só não entra na comparação
        return None


def guardar_substituida(arquivo, raiz, nome_pasta: str = "Substituídas") -> str | None:
    """Tira uma cópia antiga do caminho, sem apagar: vai para <raiz>/Substituídas/<mesmo caminho relativo>."""
    arquivo, raiz = Path(arquivo), Path(raiz)
    if not arquivo.is_file():
        return None
    try:
        rel = arquivo.relative_to(raiz)
    except ValueError:
        rel = Path(arquivo.name)
    alvo = raiz / nome_pasta / rel
    alvo.parent.mkdir(parents=True, exist_ok=True)
    n = 2
    while alvo.exists():
        alvo = alvo.with_name(f"{Path(rel).stem} ({n}){Path(rel).suffix}")
        n += 1
    shutil.move(str(arquivo), str(alvo))
    return str(alvo)
