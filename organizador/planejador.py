"""Planeja a estrutura de pastas (prévia) e copia os arquivos com segurança.

Regras de segurança: só COPIA (nunca move nem apaga), confere o tamanho depois de copiar,
nunca sobrescreve um arquivo diferente e grava um log de tudo que fez.
"""
import json
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from . import escrita
from .limpeza import nome_de_arquivo
from .generos import artista_principal
from .modelos import Faixa
from .taxonomia import grupo as grupo_genero

PADROES = {
    "A": ("Gênero → BPM → Camelot", ["genero", "bpm", "camelot"]),
    "B": ("BPM → Gênero → Camelot", ["bpm", "genero", "camelot"]),
    "C": ("Gênero → Camelot → BPM", ["genero", "camelot", "bpm"]),
    "D": ("Gênero → BPM", ["genero", "bpm"]),
}

# níveis de pasta que o usuário pode combinar na ordem que quiser
NIVEIS = {"genero": "Gênero", "bpm": "BPM", "camelot": "Tom (Camelot)", "artista": "Artista", "ano": "Ano"}
NIVEIS_EN = {"genero": "Genre", "bpm": "BPM", "camelot": "Key (Camelot)", "artista": "Artist", "ano": "Year"}
# nomes de pastas e motivos que o programa cria, por idioma (a chave é o texto em português)
PASTAS_EN = {"Revisão": "Review", "Arquivo com erro": "File with error", "Sem gênero": "No genre", "BPM não detectado": "BPM not detected",
             "Tom não detectado": "Key not detected", "BPM incerto": "Uncertain BPM", "Tom incerto": "Uncertain key",
             "Sem artista": "No artist", "Sem ano": "No year", "Melhoradas": "Improved"}
PASTAS_REVISAO = ("Revisão", "Review")


def nome_pasta(texto: str, idioma: str = "pt") -> str:
    return PASTAS_EN.get(texto, texto) if idioma == "en" else texto


def nomes_niveis(idioma: str = "pt") -> dict:
    return NIVEIS_EN if idioma == "en" else NIVEIS


def validar_ordem(ordem) -> list[str] | None:
    """Lista de níveis sem repetição e só com nomes conhecidos; None se não servir."""
    if not isinstance(ordem, (list, tuple)):
        return None
    limpa = [str(n) for n in dict.fromkeys(ordem) if str(n) in NIVEIS]
    return limpa if limpa and len(limpa) == len(list(ordem)) else None


_INVALIDOS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def limpar_nome(texto: str) -> str:
    texto = re.sub(r"\s*[/\\]\s*", " - ", texto)  # "Alternative/Indie" vira "Alternative - Indie" (barra não pode em nome de pasta)
    limpo = _INVALIDOS.sub("_", texto).strip().rstrip(". ")
    return limpo or "_"


def rotulo_bpm(bpm: float, modo: str = "exato", tamanho: int = 5) -> str:
    b = int(round(bpm))
    if modo == "faixas" and tamanho > 1:
        inicio = (b // tamanho) * tamanho
        return f"{inicio}-{inicio + tamanho - 1} BPM"
    return f"{b} BPM"


def rotulo_camelot(codigo: str) -> str:
    """"8A" -> "08A": com zero à esquerda, qualquer programa ordena na sequência da roda (01A, 01B, 02A, 02B...),
    deixando as tonalidades que combinam (mesmo número, ±1 e A/B) a no máximo 2 pastas de distância."""
    return f"{int(codigo[:-1]):02d}{codigo[-1]}" if codigo and codigo[:-1].isdigit() else (codigo or "")


@dataclass
class ItemPlano:
    origem: str
    destino: str  # caminho relativo à pasta de destino, com "/"
    revisao: str | None = None
    tags: dict | None = None   # metadados finais (limpos), gravados só na CÓPIA
    capa: str | None = None
    limpar: bool = False       # refaz as tags da cópia só com o que é útil (mp3, flac, m4a)
    ajustou: bool = False      # o usuário/internet mudou algo desta música (grava mesmo em formatos sem limpeza)
    nome: str = ""             # nome de exibição (Artista - Título)
    outros_nomes: list = field(default_factory=list)  # nomes que a cópia teria com outras opções de BPM/tom no nome


def _motivo_revisao(f: Faixa, partes: list[str], min_bpm_conf: float, min_tom_conf: float, incluir_incertas: bool):
    if f.erro:
        return "Arquivo com erro"
    if "genero" in partes and not f.genero:
        return "Sem gênero"
    if "bpm" in partes and f.bpm is None:
        return "BPM não detectado"
    if "camelot" in partes and f.camelot is None:
        return "Tom não detectado"
    if not incluir_incertas:
        if "bpm" in partes and f.bpm_conf < min_bpm_conf:
            return "BPM incerto"
        if "camelot" in partes and f.tom_conf < min_tom_conf:
            return "Tom incerto"
    return None


def agrupar_bpms(contagem: dict[int, int], minimo: int = 3, largura: int = 5, salto: int = 3) -> dict[int, str]:
    """Junta BPMs vizinhos que têm poucas músicas. contagem: {bpm: quantidade} -> {bpm: nome da pasta}.

    Um grupo cresce até ter pelo menos `minimo` músicas, sem passar de `largura` BPM entre o menor e o maior
    (128 e 133, por exemplo: ainda dá para mixar ajustando o pitch) e sem pular buracos maiores que `salto`."""
    grupos: list[list[int]] = []
    atual: list[int] = []
    cheio = lambda g: sum(contagem[x] for x in g) >= minimo  # noqa: E731
    for b in sorted(contagem):
        sozinho = contagem[b] >= minimo  # BPM que já tem bastante música fica com a pasta só dele
        if atual and (sozinho or b - atual[0] > largura or b - atual[-1] > salto or cheio(atual)):
            grupos.append(atual)
            atual = []
        atual.append(b)
        if sozinho:
            grupos.append(atual)
            atual = []
    if atual:
        grupos.append(atual)
    mudou = True
    while mudou:  # grupo que ficou pequeno entra no vizinho mais próximo (antes ou depois), se couber
        mudou = False
        for i, g in enumerate(grupos):
            if cheio(g):
                continue
            opcoes = []
            if i > 0 and g[-1] - grupos[i - 1][0] <= largura and g[0] - grupos[i - 1][-1] <= salto:
                opcoes.append((g[0] - grupos[i - 1][-1], i - 1))
            if i + 1 < len(grupos) and grupos[i + 1][-1] - g[0] <= largura and grupos[i + 1][0] - g[-1] <= salto:
                opcoes.append((grupos[i + 1][0] - g[-1], i + 1))
            if opcoes:
                j = min(opcoes)[1]
                grupos[min(i, j)] = sorted(grupos[i] + grupos[j])
                del grupos[max(i, j)]
                mudou = True
                break
    return {b: (f"{g[0]} BPM" if g[0] == g[-1] else f"{g[0]}-{g[-1]} BPM") for g in grupos for b in g}


def planejar(
    faixas: list[Faixa],
    padrao: str = "A",
    bpm_modo: str = "exato",
    bpm_tam: int = 5,
    min_bpm_conf: float = 3.0,
    min_tom_conf: float = 0.01,
    incluir_incertas: bool = False,
    agrupar_generos: bool = False,
    grupos_proprios: dict | None = None,
    ordem: list | None = None,
    tom_no_nome: bool = False,
    bpm_no_nome: bool = False,
    idioma: str = "pt",
) -> list[ItemPlano]:
    partes = validar_ordem(ordem) or PADROES[padrao][1]  # ordem montada pelo usuário vale mais que o modelo pronto
    # o que já vai no nome do arquivo não vira pasta também (seria a mesma informação duas vezes)
    no_nome = [p for p, ligado in (("bpm", bpm_no_nome), ("camelot", tom_no_nome)) if ligado]
    partes = [p for p in partes if p not in no_nome] or ["genero"]
    usados: set[str] = set()
    plano: list[ItemPlano] = []
    antes_do_bpm = partes[:partes.index("bpm")] if "bpm" in partes else []

    def pasta_genero(f):
        return limpar_nome(grupo_genero(f.genero, grupos_proprios) if agrupar_generos else f.genero) if f.genero else ""

    def valor(f, p):  # nome da pasta deste nível para esta música (o BPM é resolvido à parte)
        if p == "genero":
            return pasta_genero(f)
        if p == "camelot":
            return rotulo_camelot(f.camelot)
        if p == "artista":
            return limpar_nome(artista_principal(f.artista)) if f.artista else nome_pasta("Sem artista", idioma)
        if p == "ano":
            return f.ano[:4] if (f.ano or "")[:4].isdigit() else nome_pasta("Sem ano", idioma)
        return ""

    def contexto(f):  # pastas que vêm antes do BPM: os BPMs são juntados dentro de cada uma (ex.: dentro de cada gênero)
        return tuple(valor(f, p) for p in antes_do_bpm)

    motivos = {f.caminho: nome_pasta(_motivo_revisao(f, partes + no_nome, min_bpm_conf, min_tom_conf, incluir_incertas) or "", idioma) or None for f in faixas}
    rotulos_auto: dict[tuple, dict[int, str]] = {}
    if bpm_modo == "auto" and "bpm" in partes:
        contagens: dict[tuple, dict[int, int]] = {}
        for f in faixas:
            if not motivos[f.caminho] and f.bpm is not None:
                c = contagens.setdefault(contexto(f), {})
                c[int(round(f.bpm))] = c.get(int(round(f.bpm)), 0) + 1
        rotulos_auto = {k: agrupar_bpms(c) for k, c in contagens.items()}
    for f in sorted(faixas, key=lambda x: x.caminho.lower()):
        motivo = motivos[f.caminho]
        if motivo:
            pastas = [nome_pasta("Revisão", idioma), motivo]
        else:
            if f.bpm is None:
                bpm = ""
            elif bpm_modo == "auto":
                bpm = rotulos_auto.get(contexto(f), {}).get(int(round(f.bpm))) or rotulo_bpm(f.bpm)
            else:
                bpm = rotulo_bpm(f.bpm, bpm_modo, bpm_tam)
            pastas = [bpm if p == "bpm" else valor(f, p) for p in partes]
        ext = Path(f.caminho).suffix.lower()
        base_nome = limpar_nome(nome_de_arquivo(f.titulo, f.artista, Path(f.caminho).stem))
        # BPM e/ou tom no começo do nome: dentro da pasta os arquivos ficam em ordem de BPM (3 dígitos, para 90 vir antes
        # de 128 em qualquer aparelho) e, no mesmo BPM, na ordem da roda harmônica, sem precisar de subpastas
        p_bpm = f"{int(round(f.bpm)):03d} - " if f.bpm is not None else ""
        p_tom = f"{rotulo_camelot(f.camelot)} - " if f.camelot else ""
        prefixo = (p_bpm if bpm_no_nome else "") + (p_tom if tom_no_nome else "")
        outros = [x + base_nome + ext for x in dict.fromkeys(["", p_tom, p_bpm, p_bpm + p_tom]) if x != prefixo]
        nome = prefixo + base_nome + ext
        destino = "/".join(pastas + [nome])
        base = Path(nome)
        n = 2
        while destino.lower() in usados:
            destino = "/".join(pastas + [f"{base.stem} ({n}){base.suffix}"])
            n += 1
        usados.add(destino.lower())
        aj = f.ajustes or {}
        tags = {"titulo": f.titulo, "artista": f.artista, "album": f.album or f.titulo, "genero": f.genero, "ano": f.ano}
        if f.bpm is not None and f.bpm_conf >= min_bpm_conf:
            tags["bpm"] = int(f.bpm)
        if f.camelot and f.tom_conf >= min_tom_conf:
            tags["camelot"] = f.camelot
        plano.append(ItemPlano(origem=f.caminho, destino=destino, revisao=motivo,
                               tags={k: v for k, v in tags.items() if v not in ("", None)} or None, capa=aj.get("capa_arquivo"),
                               limpar=ext in escrita.FORMATOS_LIMPEZA, ajustou=bool(aj), nome=base_nome, outros_nomes=outros))
    return plano


def arvore(plano: list[ItemPlano]) -> list[dict]:
    """Resumo da prévia: cada pasta com a quantidade de músicas dentro (inclui subpastas)."""
    contagem: dict[tuple, int] = {}
    for item in plano:
        partes = tuple(item.destino.split("/")[:-1])
        for i in range(1, len(partes) + 1):
            contagem[partes[:i]] = contagem.get(partes[:i], 0) + 1
    return [{"caminho": "/".join(k), "nome": k[-1], "nivel": len(k) - 1, "qtd": v} for k, v in sorted(contagem.items())]


def _livre(alvo: Path) -> Path:
    n = 2
    while True:
        candidato = alvo.with_name(f"{alvo.stem} ({n}){alvo.suffix}")
        if not candidato.exists():
            return candidato
        n += 1


def _assinatura(caminho: Path):
    st = caminho.stat()
    return st.st_size, st.st_mtime_ns


def _carregar_indice(destino: Path) -> dict:
    """O que o programa já colocou neste destino: {caminho do original: {"rel": lugar da cópia, "tam", "mtime", "tags", "capa"}}.
    Na primeira vez, é montado a partir dos registros (logs) de cópias anteriores."""
    pasta = destino / ".organizador"
    try:
        return json.loads((pasta / "indice.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    indice: dict = {}
    for log in sorted(pasta.glob("log-*.json")) if pasta.is_dir() else []:
        try:
            for r in json.loads(log.read_text(encoding="utf-8")):
                if r.get("status") in ("copiado", "ja_existia", "movido"):
                    indice[r["origem"]] = {"rel": Path(r["destino"]).relative_to(destino).as_posix()}
        except (OSError, ValueError, KeyError):
            continue
    return indice


def _apagar_pastas_vazias(destino: Path) -> int:
    """Depois de mover cópias, tira as pastas que ficaram vazias (nunca apaga arquivos)."""
    n = 0
    for pasta in sorted((p for p in destino.rglob("*") if p.is_dir() and ".organizador" not in p.parts), key=lambda p: -len(p.parts)):
        try:
            pasta.rmdir()  # só funciona se estiver vazia
            n += 1
        except OSError:
            pass
    return n


def reaproveitar(saida, pedidos: list[tuple[str, str]], marca=None, refazer: bool = False) -> tuple[list[int], dict, dict]:
    """Evita refazer trabalho numa pasta de resultados (ex.: "Melhoradas") quando a organização das pastas muda.

    pedidos: [(caminho do original, lugar novo do resultado, relativo a `saida`)]. Para cada um:
      - se o resultado já existe no lugar novo, fica;
      - se existe em outro lugar (pelo índice da pasta ou, em pastas feitas por versões antigas, pelo mesmo nome de
        arquivo), é MOVIDO para o lugar novo;
      - senão (música nova, original trocado ou `marca` diferente, ex.: outro volume alvo), precisa ser feito.
    Devolve (posições dos pedidos que precisam ser feitos, contagens, índice atualizado). Nunca apaga arquivos."""
    saida = Path(saida)
    indice = {} if refazer else _carregar_indice(saida)
    cont = {"no_lugar": 0, "movidos": 0, "ja_bom": 0}
    por_nome: dict[str, list[Path]] | None = None
    usados: set[Path] = set()
    fazer: list[int] = []
    for n, pedido in enumerate(pedidos):
        origem, rel = pedido[0], pedido[1]
        outros_nomes = list(pedido[2]) if len(pedido) > 2 else []  # nomes que o arquivo pode ter tido antes (ex.: sem o tom na frente)
        if refazer:
            fazer.append(n)
            continue
        novo = saida / rel
        try:
            sig = _assinatura(Path(origem))
        except OSError:
            fazer.append(n)
            continue
        ant = indice.get(origem)
        if ant:
            mesma = ant.get("tam") in (None, sig[0]) and ant.get("mtime") in (None, sig[1]) and ant.get("marca") in (None, marca)
            if mesma and ant.get("ja_bom"):
                cont["ja_bom"] += 1
                continue
            velho = saida / ant["rel"] if mesma and ant.get("rel") else None
        else:
            if por_nome is None:  # pasta feita por versão antiga, sem índice: procura pelo nome do arquivo
                por_nome = {}
                for p in (saida.rglob("*") if saida.is_dir() else []):
                    if p.is_file() and ".organizador" not in p.parts:
                        por_nome.setdefault(p.name.casefold(), []).append(p)
            achados = [p for nome in dict.fromkeys([novo.name] + outros_nomes)
                       for p in por_nome.get(nome.casefold(), []) if p not in usados]
            if len(achados) > 1:  # mesmo nome em mais de um lugar: só vale o que está no mesmo gênero (1ª pasta)
                achados = [p for p in achados if p.relative_to(saida).parts[0] == Path(rel).parts[0]]
            velho = novo if novo.is_file() and novo not in usados else (achados[0] if len(achados) == 1 else None)
        if velho is None or not velho.is_file():
            fazer.append(n)
            continue
        if velho.resolve() != novo.resolve():
            if novo.exists():
                fazer.append(n)
                continue
            novo.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(velho), str(novo))
            cont["movidos"] += 1
        else:
            cont["no_lugar"] += 1
        usados.add(novo)
        indice[origem] = {"rel": Path(rel).as_posix(), "tam": sig[0], "mtime": sig[1], "marca": (ant or {}).get("marca")}
    if cont["movidos"]:
        _apagar_pastas_vazias(saida)
    return fazer, cont, indice


def salvar_indice(saida, indice: dict) -> None:
    pasta = Path(saida) / ".organizador"
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def executar(plano: list[ItemPlano], destino, ao_progresso=None, cancelar=None, gravar_tags: bool = True) -> dict:
    destino = Path(destino)
    copiados = ignorados = erros = gravadas = falhas_tags = capas_trocadas = originais_alterados = movidos = atualizados = 0
    registro, revisao, detalhes_erro = [], [], []
    indice = _carregar_indice(destino)

    def gravar(alvo, item, reg):
        nonlocal gravadas, falhas_tags, capas_trocadas
        if not (gravar_tags and (item.limpar or item.ajustou or item.capa)):
            return
        try:  # só a cópia é alterada; as tags de antes ficam no log para restaurar
            r = escrita.gravar(alvo, item.tags or {}, item.capa, limpar=item.limpar)
            reg.update(r)
            gravadas += 1
            capas_trocadas += 1 if r.get("capa_gravada") else 0
        except Exception as e:  # noqa: BLE001
            falhas_tags += 1
            reg["erro_tags"] = str(e)

    for i, item in enumerate(plano, 1):
        if cancelar is not None and cancelar.is_set():
            break
        origem = Path(item.origem)
        alvo = destino / item.destino
        try:
            alvo.parent.mkdir(parents=True, exist_ok=True)
            antes = _assinatura(origem)
            tamanho = antes[0]
            ant = indice.get(str(origem))
            mesma_musica = bool(ant) and ant.get("tam") in (None, tamanho) and ant.get("mtime") in (None, antes[1])
            antiga = destino / ant["rel"] if ant else None
            marcas = {"tam": tamanho, "mtime": antes[1], "tags": item.tags, "capa": item.capa}
            reg = None
            if mesma_musica and antiga.is_file() and antiga.resolve() == alvo.resolve():
                # a cópia desta música já está no lugar certo: não copia de novo; só atualiza as tags se algo mudou
                reg = {"origem": str(origem), "destino": str(alvo), "status": "ja_existia"}
                if "tags" in ant and (ant.get("tags") != item.tags or ant.get("capa") != item.capa):
                    gravar(alvo, item, reg)
                    atualizados += 1
                ignorados += 1
            elif mesma_musica and antiga.is_file() and not alvo.exists():
                # a cópia já existe em outra pasta (mudou o gênero, o BPM da pasta ou o nome): MOVE em vez de duplicar
                shutil.move(str(antiga), str(alvo))
                reg = {"origem": str(origem), "destino": str(alvo), "status": "movido", "de": str(antiga)}
                gravar(alvo, item, reg)
                movidos += 1
            if reg is None:
                if alvo.exists():
                    if alvo.stat().st_size == tamanho:
                        ignorados += 1
                        registro.append({"origem": str(origem), "destino": str(alvo), "status": "ja_existia"})
                        indice[str(origem)] = {"rel": alvo.relative_to(destino).as_posix(), **marcas}
                        if item.revisao:
                            revisao.append({"arquivo": item.nome or origem.stem, "motivo": item.revisao})
                        continue
                    alvo = _livre(alvo)
                shutil.copy2(origem, alvo)
                if alvo.stat().st_size != tamanho:
                    raise OSError("tamanho diferente depois de copiar")
                copiados += 1
                reg = {"origem": str(origem), "destino": str(alvo), "status": "copiado"}
                gravar(alvo, item, reg)
            indice[str(origem)] = {"rel": alvo.relative_to(destino).as_posix(), **marcas}
            if _assinatura(origem) != antes:
                originais_alterados += 1
            if item.revisao:
                revisao.append({"arquivo": item.nome or origem.stem, "motivo": item.revisao})
            registro.append(reg)
        except Exception as e:  # noqa: BLE001 - uma música com problema não pode parar as outras
            erros += 1
            detalhes_erro.append({"arquivo": origem.name, "detalhe": str(e)})
            registro.append({"origem": str(origem), "destino": str(alvo), "status": "erro", "detalhe": str(e)})
        if ao_progresso:
            ao_progresso(i, len(plano))
    pastas_vazias = _apagar_pastas_vazias(destino) if movidos else 0
    pasta_log = destino / ".organizador"
    pasta_log.mkdir(parents=True, exist_ok=True)
    arq_log = pasta_log / f"log-{time.strftime('%Y%m%d-%H%M%S')}.json"
    arq_log.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        (pasta_log / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    # conferência final: tudo que deveria estar no destino está lá?
    no_destino = ("copiado", "ja_existia", "movido")
    ausentes = sum(1 for r in registro if r["status"] in no_destino and not Path(r["destino"]).exists())
    primeiro = {}
    for r in registro:
        if r["status"] in no_destino:
            nome = Path(r["destino"]).relative_to(destino).parts[0]
            primeiro[nome] = primeiro.get(nome, 0) + 1
    return {"copiados": copiados, "ignorados": ignorados, "erros": erros, "tags_gravadas": gravadas,
            "movidos": movidos, "atualizados": atualizados, "pastas_vazias_removidas": pastas_vazias,
            "tags_falhas": falhas_tags, "log": str(arq_log), "capas_trocadas": capas_trocadas,
            "originais_alterados": originais_alterados, "ausentes": ausentes, "pasta_destino": str(destino),
            "revisao": revisao[:300], "revisao_total": len(revisao), "erros_detalhe": detalhes_erro[:50],
            "primeiro_nivel": [{"nome": k, "qtd": v} for k, v in sorted(primeiro.items(), key=lambda kv: (kv[0] in PASTAS_REVISAO, kv[0].casefold()))],
            "cancelado": bool(cancelar is not None and cancelar.is_set())}
