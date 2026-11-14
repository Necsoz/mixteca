"""Servidor local: a interface roda no navegador, só neste computador (127.0.0.1).

Cada pedido exige um código secreto gerado a cada execução, para que nenhuma página da internet
consiga mandar o programa copiar arquivos. Nada aqui apaga ou move arquivos.
"""
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import urllib.parse

from . import ajustes, config, extras, identificacao, limpeza, planejador
from .analise import analisar_arquivo
from .camelot import nome_tom
from .classificador import ClassificadorSom
from .ferramentas import escolher_pasta, pasta_dados
from .generos import PADRAO, artista_principal, chave_artista, faixa_bpm, limpar_genero
from .melhoria import melhorar
from .pipeline import analisar_pasta, esperar, finalizar
from .provedores import acoustid, capas
from .rede import Cliente, ErroRede
from .escrita import gravar as gravar_tags_copia
from .store import Cache
from .taxonomia import RENOMEAR, Taxonomia, grupo as grupo_genero, ler_grupos, mover_grupo, renomear_pasta

WEB = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent)) / "organizador" / "web"
TOKEN = secrets.token_urlsafe(24)


class Erro(Exception):
    pass


class Estado:
    def __init__(self, arquivo_cache=None, pasta_config=None):
        self.lock = threading.Lock()
        self.pasta_config = pasta_config
        self.cache = Cache(arquivo_cache or pasta_dados() / "analises.db")
        prefs = config.carregar_preferencias(pasta_config)  # preferências locais (opcionais)
        self.tax = Taxonomia(prefs)
        limpeza.definir_termos(prefs.get("limpar_termos") or [])
        ajustes.normalizar_genero = self.tax.normalizar
        self.classificador = ClassificadorSom()
        self.faixas = []
        self.origem = ""
        self.destino_copia = ""
        self.ultimo_sinal = 0.0  # último pedido da página (modo navegador)
        self.lados_capa: dict[str, int] = {}
        self.cancelar = threading.Event()
        self.pausa = threading.Event()
        self.job = self._job_vazio()

    @staticmethod
    def _job_vazio():
        return {"tipo": None, "fase": "parado", "feitos": 0, "total": 0, "atual": "", "resultado": None, "erro": None, "pausado": False}

    def iniciar(self, tipo, trabalho):
        """Roda `trabalho(progresso)` numa thread. Só uma tarefa por vez."""
        with self.lock:
            if self.job["fase"] == "rodando":
                raise Erro("Já existe uma tarefa em andamento. Espere terminar ou cancele.")
            self.cancelar.clear()
            self.pausa.clear()
            self.job = {**self._job_vazio(), "tipo": tipo, "fase": "rodando"}

        def progresso(feitos, total, atual=""):
            with self.lock:
                self.job.update(feitos=feitos, total=total, atual=atual)

        def rodar():
            try:
                resultado = trabalho(progresso)
                with self.lock:
                    self.job.update(fase="cancelado" if self.cancelar.is_set() else "concluido", resultado=resultado)
            except Exception as e:  # noqa: BLE001
                with self.lock:
                    self.job.update(fase="erro", erro=str(e) or type(e).__name__)

        threading.Thread(target=rodar, daemon=True).start()


E: Estado | None = None


# ----------------------------------------------------------------- rotas
def _pasta_valida(texto: str, nome: str) -> Path:
    if not texto or not texto.strip():
        raise Erro(f"Informe a {nome}.")
    p = Path(texto.strip().strip('"'))
    if not p.is_dir():
        raise Erro(f"A {nome} não existe: {p}")
    return p


def _renomes(cred: dict) -> dict:
    try:
        d = json.loads(cred.get("pastas_renomeadas") or "{}")
        return {str(k): str(v) for k, v in d.items()} if isinstance(d, dict) else {}
    except ValueError:
        return {}


def _grupos_proprios() -> dict:
    """Grupos de gêneros escolhidos pelo usuário + nomes que ele deu às pastas."""
    cred = config.carregar_credenciais(E.pasta_config)
    return {**ler_grupos(cred["grupos_pastas"]), RENOMEAR: _renomes(cred)}


def _parametros_plano(c: dict) -> dict:
    padrao = c.get("padrao", "A")
    if padrao not in planejador.PADROES:
        raise Erro("Padrão de pastas inválido.")
    return {
        "padrao": padrao,
        "ordem": planejador.validar_ordem(c.get("ordem")),
        "bpm_modo": c.get("bpm_modo") if c.get("bpm_modo") in ("faixas", "auto") else "exato",
        "bpm_tam": max(2, min(20, int(c.get("bpm_tam") or 5))),
        "incluir_incertas": bool(c.get("incluir_incertas")),
        "agrupar_generos": bool(c.get("agrupar_generos")),
        "grupos_proprios": _grupos_proprios(),
    }


def r_pasta(c):
    return {"caminho": escolher_pasta(c.get("titulo", "Escolha a pasta")), "dialogo": sys.platform.startswith("win")}


def r_analisar(c):
    origem = _pasta_valida(c.get("origem", ""), "pasta das músicas")

    def trabalho(progresso):
        def ao_progresso(feitos, total, faixa):
            progresso(feitos, total, Path(faixa.caminho).name if faixa else "")

        faixas = analisar_pasta(origem, E.cache, ao_progresso, E.cancelar, pausa=E.pausa, tax=E.tax)
        resultado = {"total": len(faixas)}
        if not E.cancelar.is_set():
            E.faixas, E.origem = faixas, str(origem)
            resultado.update(_identificar_apos_analise(progresso))
        return resultado

    E.iniciar("analisar", trabalho)
    return {"ok": True}


def r_estado(_):
    with E.lock:
        return {"job": {**E.job, "pausado": E.pausa.is_set()}, "n_faixas": len(E.faixas), "origem": E.origem}


def r_faixas(_):
    saida = []
    for f in E.faixas:
        saida.append({
            "caminho": f.caminho, "arquivo": Path(f.caminho).name, "titulo": f.titulo, "artista": f.artista,
            "genero": f.genero, "bpm": f.bpm, "bpm_conf": f.bpm_conf, "camelot": f.camelot,
            "tom": nome_tom(f.tom_pc, f.tom_menor) if f.tom_pc is not None else "", "tom_conf": f.tom_conf,
            "corte_hz": f.corte_hz, "baixa": f.qualidade_baixa, "pico_db": f.pico_db, "erro": f.erro,
            "fora": f.bpm_fora_da_faixa, "genero_manual": f.genero_manual,
            "album": f.album or f.titulo, "album_da_faixa": bool(not f.album and f.titulo), "ano": f.ano, "genero_fonte": f.genero_fonte, "tem_capa": f.tem_capa,
            "ajustes": sorted(f.ajustes),
        })
    return {"faixas": saida}


def _plano(c):
    if not E.faixas:
        raise Erro("Analise uma pasta primeiro.")
    return planejador.planejar(E.faixas, **_parametros_plano(c))


def r_padroes(c):
    """Mostra cada padrão aplicado a músicas da própria biblioteca, para o usuário escolher."""
    if not E.faixas:
        raise Erro("Analise uma pasta primeiro.")
    base = {k: v for k, v in _parametros_plano(c).items() if k not in ("padrao", "ordem")}
    saida = []
    for pid, (nome, _) in planejador.PADROES.items():
        plano = planejador.planejar(E.faixas, padrao=pid, **base)
        exemplos = [i.destino for i in plano if not i.revisao][:3]
        pastas = {i.destino.rsplit("/", 1)[0] for i in plano if not i.revisao}
        saida.append({"id": pid, "nome": nome, "exemplos": exemplos, "pastas": len(pastas), "ordem": planejador.PADROES[pid][1]})
    return {"padroes": saida, "niveis": planejador.NIVEIS}


def r_previa(c):
    plano = _plano(c)
    motivos: dict[str, int] = {}
    for i in plano:
        if i.revisao:
            motivos[i.revisao] = motivos.get(i.revisao, 0) + 1
    itens = [{"arquivo": i.nome or Path(i.origem).stem, "motivo": i.revisao} for i in plano if i.revisao]
    return {"total": len(plano), "revisao": motivos, "revisao_itens": itens[:300], "arvore": planejador.arvore(plano)}


def _destino(c, origem_ok=True) -> Path:
    destino = Path((c.get("destino") or "").strip().strip('"'))
    if not str(destino).strip() or str(destino) == ".":
        raise Erro("Informe a pasta de destino.")
    origem = Path(E.origem).resolve()
    alvo = destino.resolve()
    if alvo == origem or origem in alvo.parents or alvo in origem.parents:
        raise Erro("A pasta de destino precisa ser diferente da pasta das músicas (e não pode ficar dentro dela).")
    return destino


def r_copiar(c):
    plano = _plano(c)
    destino = _destino(c)

    def trabalho(progresso):
        E.destino_copia = str(destino)
        return planejador.executar(plano, destino, lambda i, n: progresso(i, n), E.cancelar, gravar_tags=c.get("gravar_tags", True))

    E.iniciar("copiar", trabalho)
    return {"ok": True, "total": len(plano)}


def r_grupos(_):
    """Gêneros da biblioteca e a pasta em que cada um cai com "juntar gêneros próximos" ligado."""
    proprios = _grupos_proprios()
    conta: dict[str, int] = {}
    for f in E.faixas:
        if not f.erro and f.genero:
            conta[f.genero] = conta.get(f.genero, 0) + 1
    generos = [{"genero": g, "qtd": n, "pasta": grupo_genero(g, proprios), "proprio": grupo_genero(g, proprios) != grupo_genero(g)}
               for g, n in sorted(conta.items(), key=lambda kv: kv[0].casefold())]
    return {"generos": generos}


def r_grupos_mover(c):
    genero = str(c.get("genero") or "").strip()
    if not genero:
        raise Erro("Escolha um gênero.")
    cred = config.carregar_credenciais(E.pasta_config)
    config.salvar_credenciais({"grupos_pastas": mover_grupo(cred["grupos_pastas"], genero, str(c.get("pasta") or ""))}, E.pasta_config)
    return r_grupos({})


def r_grupos_renomear(c):
    de, para = str(c.get("de") or "").strip(), str(c.get("para") or "").strip()
    if not de or not para:
        raise Erro("Escreva o novo nome da pasta.")
    cred = config.carregar_credenciais(E.pasta_config)
    config.salvar_credenciais({"pastas_renomeadas": json.dumps(renomear_pasta(_renomes(cred), de, para), ensure_ascii=False)}, E.pasta_config)
    return r_grupos({})


def r_abrir_pasta(_):
    """Abre a pasta de destino da última cópia no Explorer (só no Windows; nos outros sistemas devolve o caminho)."""
    if not E.destino_copia or not Path(E.destino_copia).is_dir():
        raise Erro("Ainda não há uma cópia feita.")
    if os.name == "nt":
        os.startfile(E.destino_copia)  # noqa: S606 - caminho fixo do último destino, não vem da página
        return {"ok": True}
    return {"ok": False, "caminho": E.destino_copia}


def r_melhorar(c):
    plano = _plano(c)
    destino = _destino(c)
    escopo = c.get("escopo")
    por_caminho = {f.caminho: f for f in E.faixas}
    itens = [i for i in plano if (escopo == "estouram" and (por_caminho[i.origem].pico_db or -99) > 0)
             or (escopo == "baixa" and por_caminho[i.origem].qualidade_baixa) or escopo not in ("estouram", "baixa")]
    if not itens:
        raise Erro("Nenhuma música se encaixa nessa escolha.")
    alvo = float(c.get("alvo_lufs") or -10)
    if not -20 <= alvo <= -5:
        raise Erro("Volume alvo fora do intervalo permitido.")
    saida = destino / "Melhoradas"

    refazer = bool(c.get("refazer"))

    def trabalho(progresso):
        from .melhoria import _codec
        cont = {"melhoradas": 0, "ja_bom": 0, "erros": 0, "mensagens": [], "pasta": str(saida)}
        # o que já foi melhorado antes é aproveitado: fica onde está ou é movido para a pasta nova, sem processar de novo
        rels = [Path(i.destino).with_suffix(_codec(Path(i.origem).suffix)[0]).as_posix() for i in itens]
        fazer, aproveitado, indice = planejador.reaproveitar(saida, [(i.origem, r) for i, r in zip(itens, rels)], alvo, refazer)
        cont.update(reaproveitadas=aproveitado["no_lugar"] + aproveitado["movidos"], movidas=aproveitado["movidos"])
        cont["ja_bom"] += aproveitado["ja_bom"]
        feitos = len(itens) - len(fazer)
        progresso(feitos, len(itens), "")

        def marcar(it, rel=None, ja_bom=False):
            try:
                st = os.stat(it.origem)
                indice[it.origem] = {"tam": st.st_size, "mtime": st.st_mtime_ns, "marca": alvo, **({"ja_bom": True} if ja_bom else {"rel": rel})}
            except OSError:
                pass

        with ThreadPoolExecutor(max_workers=3) as pool:
            futuros = {}
            for n in fazer:
                i = itens[n]
                futuros[pool.submit(lambda it=i: None if E.cancelar.is_set() else melhorar(it.origem, saida / it.destino, alvo))] = n
            for fut in as_completed(futuros):
                feitos += 1
                it = itens[futuros[fut]]
                try:
                    r = fut.result()
                    if r is not None:
                        cont["melhoradas" if r["status"] == "melhorado" else "ja_bom"] += 1
                        if r["status"] == "melhorado":
                            marcar(it, rels[futuros[fut]])
                            if (it.tags or it.capa) and c.get("gravar_tags", True):
                                gravar_tags_copia(r["destino"], it.tags or {}, it.capa)
                        else:
                            marcar(it, ja_bom=True)
                except Exception as e:  # noqa: BLE001
                    cont["erros"] += 1
                    if len(cont["mensagens"]) < 5:
                        cont["mensagens"].append(f"{Path(it.origem).name}: {e}")
                progresso(feitos, len(itens), Path(it.origem).name)
        planejador.salvar_indice(saida, indice)
        return cont

    E.iniciar("melhorar", trabalho)
    return {"ok": True, "total": len(itens)}


GENEROS_COMUNS = ["Big Room", "Electro House", "Progressive House", "Future House", "Bass House", "House", "Dubstep",
                  "Trap", "Techno", "Trance", "Drum & Bass", "Hardstyle", "EDM", "Rock", "Alternative", "Indie", "Pop"]


def _sem_tag(f) -> bool:
    return not f.erro and (not f.genero or f.genero_manual)


def r_sem_genero(_):
    por_chave: dict[str, list] = {}
    com_tag: dict[str, dict[str, int]] = {}
    for f in E.faixas:
        if _sem_tag(f):
            por_chave.setdefault(chave_artista(f.artista), []).append(f)
        elif f.genero and not f.erro:
            conta = com_tag.setdefault(chave_artista(f.artista), {})
            conta[f.genero] = conta.get(f.genero, 0) + 1
    grupos = []
    for chave, fs in por_chave.items():
        sug = max(com_tag[chave], key=com_tag[chave].get) if chave in com_tag else ""
        grupos.append({
            "chave": chave, "artista": artista_principal(fs[0].artista) or "(sem artista)", "qtd": len(fs),
            "exemplos": [f.titulo or Path(f.caminho).name for f in fs[:3]],
            "atual": next((f.genero for f in fs if f.genero_manual), ""), "sugestao": sug,
        })
    grupos.sort(key=lambda g: (-g["qtd"], g["artista"].casefold()))
    conhecidos = sorted({f.genero for f in E.faixas if f.genero} | set(GENEROS_COMUNS))
    return {"grupos": grupos, "generos": conhecidos}


def _reanalisar(alvos, progresso) -> int:
    """Refaz a análise (o gênero ajuda a escolher o BPM certo) e mantém ajustes e nomes padronizados."""
    generos = E.cache.generos_artista()
    sobre = E.cache.sobrescritas()
    posicao = {f.caminho: i for i, f in enumerate(E.faixas)}
    feitos = 0
    for f in alvos:
        esperar(E.pausa, E.cancelar)
        if E.cancelar.is_set():
            break
        ov = sobre.get(f.caminho)
        dica = ((ov or {}).get("campos", {}).get("genero") or {}).get("valor", "")
        nova = analisar_arquivo(f.caminho, generos, dica)
        if nova.erro is None:
            st = os.stat(f.caminho)
            E.cache.salvar(nova, st.st_size, st.st_mtime)
            E.faixas[posicao[f.caminho]] = finalizar(nova, E.tax, ov)
        feitos += 1
        progresso(feitos, len(alvos), Path(f.caminho).name)
    return feitos


def _bpm_destoa(f) -> bool:
    lo, hi = faixa_bpm(f.genero)
    return (lo, hi) != PADRAO and (f.bpm is None or f.bpm < lo - 3 or f.bpm > hi + 3)


def r_definir_genero(c):
    if not E.faixas:
        raise Erro("Analise uma pasta primeiro.")
    defs = c.get("definicoes") or []
    if not defs:
        raise Erro("Nenhum gênero para aplicar.")
    chaves = set()
    for d in defs:
        chave = str(d.get("chave", ""))
        E.cache.definir_genero_artista(chave, limpar_genero(str(d.get("genero", "")).strip()))
        chaves.add(chave)
    alvos = [f for f in E.faixas if _sem_tag(f) and chave_artista(f.artista) in chaves]

    def trabalho(progresso):
        return {"reanalisadas": _reanalisar(alvos, progresso)}

    E.iniciar("reanalisar", trabalho)
    return {"ok": True, "total": len(alvos)}


# ------------------------------------------------- identificação, gêneros e metadados
def _sugerido(f) -> bool:
    return (f.genero_fonte or "").startswith("sugestão")


def _sugerir_generos() -> int:
    """Para quem ficou sem gênero: cruza o que existe (outras músicas do mesmo artista na biblioteca, sonoridade e
    palpites fracos da internet) e aplica o mais provável como SUGESTÃO, marcada como não confirmada."""
    from collections import Counter
    from .casamento import _SEP_ARTISTAS, norm
    partes = lambda a: {norm(p) for p in _SEP_ARTISTAS.split(a or "") if norm(p)}  # noqa: E731
    por_artista: dict[str, Counter] = {}
    for f in E.faixas:
        if not f.erro and f.genero and not _sugerido(f) and not E.tax.generico(f.genero) and not E.tax.suspeito(f.genero):
            for a in partes(f.artista):
                por_artista.setdefault(a, Counter())[f.genero] += 1
    palpites = {p["caminho"]: p["campos"]["genero"] for p in E.cache.propostas_todas()
                if "genero" in p["campos"] and not p["campos"]["genero"].get("recusado")}
    sobre = E.cache.sobrescritas()
    n = 0
    for f in E.faixas:
        if f.erro or (f.genero and not E.tax.suspeito(f.genero)):
            continue
        pontos: dict[str, float] = {}
        motivos: dict[str, list[str]] = {}

        def somar(g, peso, motivo):
            pontos[g] = pontos.get(g, 0) + peso
            motivos.setdefault(g, []).append(motivo)

        conta = Counter()
        for a in partes(f.artista):
            conta.update(por_artista.get(a, {}))
        if conta:
            g, q = conta.most_common(1)[0]
            somar(g, 0.45 + 0.35 * q / sum(conta.values()), "outras músicas do mesmo artista")
        som = E.classificador.prever(f.vetor) if E.classificador.pronto else None
        if som and som[1] >= 0.34:
            somar(som[0], som[1], "sonoridade parecida")
        pal = palpites.get(f.caminho)
        if pal and pal.get("novo"):
            somar(E.tax.normalizar(pal["novo"]), 0.4, "palpite da internet")
        if not pontos:
            continue
        g = max(pontos, key=pontos.get)
        ajustes.registrar(E.cache, sobre, f, {"genero": {"novo": g, "fonte": "sugestão: " + " + ".join(dict.fromkeys(motivos[g])), "nivel": "sugestao"}})
        n += 1
    return n


def _precisa(f) -> bool:
    return (not f.erro) and (_sugerido(f) or not f.titulo or not f.artista or not f.album or not f.genero or E.tax.generico(f.genero) or E.tax.suspeito(f.genero)
                             or (not f.tem_capa and "capa_arquivo" not in f.ajustes)
                             or bool(limpeza.grupos_estranhos(f.titulo) or limpeza.grupos_estranhos(f.album)))  # texto a conferir na internet


def _treinar() -> dict:
    E.classificador = ClassificadorSom()
    exemplos = [f for f in E.faixas if not f.erro and f.vetor and f.genero and not E.tax.generico(f.genero) and not E.tax.suspeito(f.genero)
                and not f.genero_fonte.startswith("som") and not _sugerido(f)]
    return E.classificador.treinar([f.vetor for f in exemplos], [f.genero for f in exemplos])


def r_config(c):
    cred = config.carregar_credenciais(E.pasta_config)
    return {"contato": cred["contato"], "tem_acoustid": bool(cred["acoustid"]), "tem_lastfm": bool(cred["lastfm"]), "tem_discogs": bool(cred["discogs"]), "ordem_pastas": [n for n in cred["ordem_pastas"].split(",") if n], "grupos_pastas": cred["grupos_pastas"], "agrupar_generos": cred["agrupar_generos"], "procurar_capa_melhor": cred["procurar_capa_melhor"],
            "aplicar_alta_automatico": cred["aplicar_alta_automatico"], "fpcalc": acoustid.disponivel(),
            "pasta_dados": str(E.pasta_config or pasta_dados())}


def r_config_salvar(c):
    novos = {}
    for k in ("contato", "acoustid", "lastfm", "discogs"):
        if k in c and (k == "contato" or c[k] != "__manter__"):
            novos[k] = c[k]
    for k in ("aplicar_alta_automatico", "procurar_capa_melhor", "agrupar_generos"):
        if k in c:
            novos[k] = bool(c[k])
    if "ordem_pastas" in c:
        novos["ordem_pastas"] = ",".join(planejador.validar_ordem(c["ordem_pastas"]) or [])
    if "grupos_pastas" in c:
        novos["grupos_pastas"] = str(c["grupos_pastas"])[:4000]
    config.salvar_credenciais(novos, E.pasta_config)
    return r_config({})


def _aplicar_auto(propostas: list[dict], por_caminho: dict) -> tuple[int, list]:
    """Alta e média confiança em campos que estavam vazios: aceita sozinho (dá para desfazer). Alterações de valores existentes sempre pedem conferência."""
    sobre = E.cache.sobrescritas()
    n, afetadas = 0, []
    for p in propostas:
        f = por_caminho.get(p["caminho"])
        if f is None:
            continue
        auto = {k: v for k, v in p["campos"].items() if v["nivel"] in ("alta", "media") and not v["alteracao"]}
        if auto:
            ajustes.registrar(E.cache, sobre, f, auto)
            for v in auto.values():
                v["aplicado"] = True
            n += len(auto)
            if "genero" in auto:
                afetadas.append(f)
        _atualizar_status(p)
    return n, afetadas


def _atualizar_status(p: dict) -> None:
    if all(v.get("aplicado") or v.get("recusado") for v in p["campos"].values()):
        p["status"] = "resolvida"


def _medir_capas(faixas: list, progresso=None) -> None:
    """Mede o tamanho da capa embutida das músicas (para saber se vale procurar uma melhor). É a parte lenta entre a
    análise e a busca, então roda em paralelo, mostra o andamento e fica guardada em disco para as próximas vezes."""
    arq = pasta_dados() / "capas-medidas.json"
    if not E.lados_capa:
        try:
            E.lados_capa = json.loads(arq.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            E.lados_capa = {}

    def chave(f):
        try:
            st = os.stat(f.caminho)
            return f"{f.caminho}|{st.st_size}|{st.st_mtime_ns}"
        except OSError:
            return f.caminho

    falta = [(f, chave(f)) for f in faixas]
    falta = [(f, k) for f, k in falta if k not in E.lados_capa]
    if falta:
        feitos = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futuros = {pool.submit(capas.lado_embutido, f.caminho): k for f, k in falta}
            for fut in as_completed(futuros):
                E.lados_capa[futuros[fut]] = fut.result()
                feitos += 1
                if progresso and (feitos % 10 == 0 or feitos == len(falta)):
                    progresso(feitos, len(falta), "Conferindo o tamanho das capas")
                if E.cancelar.is_set():
                    break
        try:
            arq.write_text(json.dumps(E.lados_capa), encoding="utf-8")
        except OSError:
            pass
    for f in faixas:
        E.lados_capa.setdefault(f.caminho, E.lados_capa.get(chave(f), 0))


def _alvos_identificacao(escopo: str, procurar_capa: bool = True, progresso=None) -> tuple[list, list]:
    """(músicas incompletas, músicas completas cuja capa embutida é pequena e vale conferir se há uma melhor)."""
    base = [f for f in E.faixas if not f.erro and (escopo == "todas" or _precisa(f))]
    so_capa = []
    if procurar_capa:
        ja = {f.caminho for f in base}
        candidatas = [f for f in E.faixas if not f.erro and f.tem_capa and f.caminho not in ja]
        _medir_capas(candidatas, progresso)
        so_capa = [f for f in candidatas if 0 < E.lados_capa.get(f.caminho, 0) < capas.LADO_BOM]
    return base, so_capa


def _versao_online(cred: dict) -> int:
    """Resultados guardados valem só para as fontes que estavam ligadas: ligar o Discogs, por exemplo, pesquisa de novo."""
    return (identificacao.VERSAO_ONLINE * 100 + (1 if cred.get("discogs") else 0) + (2 if extras.carregar_todos(pasta_dados()) else 0)
            + (4 if cred.get("lastfm") else 0) + (8 if cred.get("acoustid") else 0) + (16 if cred.get("procurar_capa_melhor", True) else 0))


def _identificar_tudo(progresso, internet: bool = True, escopo: str = "faltando", rotulo: str = "") -> dict | None:
    """Busca na internet (ou só pela sonoridade) o que falta, aplica o que é seguro e guarda o resto como sugestão."""
    cred = config.carregar_credenciais(E.pasta_config)
    base, so_capa = _alvos_identificacao(escopo, cred["procurar_capa_melhor"] and internet, progresso)
    alvos = base + so_capa
    modo_capa = {f.caminho for f in so_capa}
    if not alvos:
        return None
    cli = Cliente(cred["contato"], E.cache)
    versao = _versao_online(cred)
    pasta_capas = pasta_dados() / "capas"
    online, falhas, seguidas, feitas_antes = {}, 0, 0, 0
    if internet:
        for i, f in enumerate(alvos, 1):
            esperar(E.pausa, E.cancelar)
            if E.cancelar.is_set():
                break
            st = os.stat(f.caminho)
            dados = E.cache.online_obter(f.caminho, st.st_size, st.st_mtime, versao + (1000 if f.caminho in modo_capa else 0))
            if dados is not None:
                feitas_antes += 1
            else:
                try:
                    dados = identificacao.pesquisar_online(f, cli, cred, pasta_capas, so_capa=f.caminho in modo_capa)
                    E.cache.online_salvar(f.caminho, st.st_size, st.st_mtime, versao + (1000 if f.caminho in modo_capa else 0), dados)
                    seguidas = 0
                except ErroRede:
                    falhas += 1
                    seguidas += 1
                    if seguidas >= 5:
                        raise RuntimeError("Sem acesso às fontes da internet. O que já foi pesquisado ficou guardado: "
                                           "verifique a conexão e clique em Buscar de novo para continuar de onde parou.")
                except Exception:  # noqa: BLE001 - resposta inesperada de uma fonte não pode derrubar o lote
                    falhas += 1
            online[f.caminho] = dados
            progresso(i, len(alvos), rotulo + Path(f.caminho).name)
        considerar = [f for f in alvos if f.caminho in online]
    else:
        considerar = alvos
    _treinar()
    por_caminho = {f.caminho: f for f in E.faixas}
    antigas = {p["caminho"]: p for p in E.cache.propostas_todas()}
    novas = []
    for f in considerar:
        p = identificacao.montar_proposta(f, online.get(f.caminho), E.classificador.prever(f.vetor), E.tax)
        if not p:
            continue
        ant = antigas.get(f.caminho)
        if ant:  # o que o usuário já recusou não volta; o que já foi aceito não é proposto de novo
            for k, v in ant["campos"].items():
                if k in p["campos"] and p["campos"][k]["novo"] == v["novo"] and (v.get("recusado") or v.get("aplicado")):
                    del p["campos"][k]
            if not p["campos"]:
                continue
        novas.append(p)
    E.cache.propostas_apagar([f.caminho for f in considerar])
    n_auto, afetadas = 0, []
    if cred["aplicar_alta_automatico"]:
        n_auto, afetadas = _aplicar_auto(novas, por_caminho)
    for p in novas:
        _atualizar_status(p)
    E.cache.propostas_salvar(novas)
    reanalise = [f for f in afetadas if _bpm_destoa(f)]
    if reanalise and not E.cancelar.is_set():
        _reanalisar(reanalise, lambda i, n, nome="": progresso(i, n, "Ajustando BPM: " + nome))
    sugeridas = _sugerir_generos() if not E.cancelar.is_set() else 0
    pend = [p for p in novas if p["status"] == "pendente"]
    conta = lambda nv: sum(1 for p in pend for v in p["campos"].values() if v["nivel"] == nv and not v.get("aplicado"))  # noqa: E731
    return {"pesquisadas": len(online), "ja_pesquisadas": feitas_antes, "falhas_rede": falhas,
            "aplicadas_auto": n_auto, "sugeridas": sugeridas, "media": conta("media"), "baixa": conta("baixa"), "alta_pendente": conta("alta"),
            "sem_resultado": len(considerar) - len(novas), "autoteste": E.classificador.autoteste if E.classificador.pronto else None,
            "aviso_som": E.classificador.motivo or None,
            "extra_indisponivel": cli.extra_off if internet else "",
            "pasta_dados": str(pasta_dados())}


def _identificar_apos_analise(progresso) -> dict:
    """Roda sozinho depois de analisar: sem internet ou com falha, cai para a sonoridade, sem perguntar nada."""
    saida = {}
    try:
        saida["ident"] = _identificar_tudo(progresso, True, "faltando", "Internet · ")
    except Exception as e:  # noqa: BLE001 - qualquer falha da busca não pode perder a análise
        if E.cancelar.is_set():
            return saida
        saida["ident_aviso"] = ("Não consegui falar com a internet agora, então usei só a sonoridade das suas músicas. "
                                "Quando a conexão voltar, clique em Buscar de novo.")
        try:
            saida["ident"] = _identificar_tudo(progresso, False, "faltando", "Sonoridade · ")
        except Exception:  # noqa: BLE001
            pass
    return saida


def r_identificar(c):
    if not E.faixas:
        raise Erro("Analise uma pasta primeiro.")
    internet = c.get("internet", True)
    escopo = "todas" if c.get("escopo") == "todas" else "faltando"
    # a medição das capas (lenta) acontece dentro da tarefa, com barra de andamento, e não aqui
    E.iniciar("identificar", lambda progresso: _identificar_tudo(progresso, internet, escopo))
    return {"ok": True}


def r_propostas(_):
    nomes = {f.caminho: f for f in E.faixas}
    saida = []
    for p in E.cache.propostas_todas():
        f = nomes.get(p["caminho"])
        if f is None or p["status"] != "pendente":
            continue
        campos = {k: v for k, v in p["campos"].items() if not (v.get("aplicado") or v.get("recusado"))}
        if not campos:
            continue
        saida.append({"caminho": p["caminho"], "arquivo": Path(p["caminho"]).name, "titulo": f.titulo, "artista": f.artista,
                      "campos": campos, "faltando": p["faltando"], "identificacao": p["identificacao"]})
    ordem = {"alta": 0, "media": 1, "baixa": 2}
    saida.sort(key=lambda p: (min(ordem[v["nivel"]] for v in p["campos"].values()), p["arquivo"].casefold()))
    resumo = {"identificadas": sum(1 for f in E.faixas if f.ajustes), "pendentes": len(saida)}
    return {"propostas": saida, "resumo": resumo}


def r_decidir(c):
    acao, nivel = c.get("acao"), c.get("nivel")
    if acao not in ("aceitar", "recusar"):
        raise Erro("Ação inválida.")
    if acao == "aceitar" and nivel == "baixa":
        raise Erro("Sugestões de baixa confiança precisam ser conferidas e aceitas uma a uma.")
    sel = set(c.get("caminhos") or [])
    campos_sel = set(c.get("campos") or [])
    if not sel and not nivel and not c.get("todas"):
        raise Erro("Nada selecionado.")
    em_lote = not sel  # em lote, baixa confiança nunca é aceita (só uma a uma)
    por_caminho = {f.caminho: f for f in E.faixas}
    sobre = E.cache.sobrescritas()
    mudadas, afetadas, n = [], [], 0
    for p in E.cache.propostas_todas():
        f = por_caminho.get(p["caminho"])
        if f is None or p["status"] != "pendente" or (sel and p["caminho"] not in sel):
            continue
        esc = {k: v for k, v in p["campos"].items()
               if not (v.get("aplicado") or v.get("recusado")) and (not campos_sel or k in campos_sel)
               and (not nivel or v["nivel"] == nivel) and not (acao == "aceitar" and em_lote and v["nivel"] == "baixa")}
        if not esc:
            continue
        if acao == "aceitar":
            ajustes.registrar(E.cache, sobre, f, esc)
            if "genero" in esc:
                afetadas.append(f)
        if acao == "recusar" and "genero" in esc and _sugerido(f) and f.genero == E.tax.normalizar(esc["genero"]["novo"]):
            ov = sobre.get(f.caminho)  # o palpite recusado tinha virado sugestão de gênero: a sugestão sai junto
            if ov and "genero" in ov["campos"]:
                f.genero = ov["campos"].pop("genero").get("anterior", "")
                f.genero_fonte = "tag" if f.genero else ""
                if not ov["campos"]:
                    sobre.pop(f.caminho, None)
                E.cache.sobrescrita_salvar(f.caminho, ov if ov["campos"] else None)
                ajustes.aplicar_em_faixa(f, ov if ov["campos"] else None)
        for v in esc.values():
            v["aplicado" if acao == "aceitar" else "recusado"] = True
        n += len(esc)
        _atualizar_status(p)
        mudadas.append(p)
    E.cache.propostas_salvar(mudadas)
    reanalise = [f for f in afetadas if _bpm_destoa(f)]
    if reanalise:
        try:
            E.iniciar("reanalisar", lambda prog: {"reanalisadas": _reanalisar(reanalise, prog)})
        except Erro:
            pass
    return {"ok": True, "campos": n, "reanalisando": len(reanalise)}


def r_conferir(_):
    """Músicas sem gênero confirmado (sem gênero ou só com sugestão), uma por linha, para o usuário decidir."""
    itens = []
    for f in E.faixas:
        if f.erro or (f.genero and not _sugerido(f)):
            continue
        nome = f"{f.artista} — {f.titulo}" if f.artista and f.titulo else (f.titulo or Path(f.caminho).stem)
        itens.append({"caminho": f.caminho, "nome": nome, "arquivo": Path(f.caminho).name, "genero": f.genero,
                      "motivo": (f.genero_fonte or "").replace("sugestão: ", "") if f.genero else ""})
    itens.sort(key=lambda i: (not i["genero"], i["nome"].casefold()))
    conhecidos = sorted({f.genero for f in E.faixas if f.genero} | set(GENEROS_COMUNS))
    return {"itens": itens, "generos": conhecidos}


def r_genero_faixa(c):
    """O usuário define o gênero de uma ou mais músicas (vale mais que qualquer fonte; vai para a cópia, o original não muda)."""
    pedidos = c.get("itens") or [{"caminho": c.get("caminho"), "genero": c.get("genero")}]
    por_caminho = {f.caminho: f for f in E.faixas}
    sobre = E.cache.sobrescritas()
    feitos, ultimo = 0, ""
    for p in pedidos[:5000]:
        f = por_caminho.get(p.get("caminho"))
        genero = limpar_genero(str(p.get("genero") or ""))[:60] if p.get("genero") else ""
        if f is None or f.erro or not genero:
            continue
        ajustes.registrar(E.cache, sobre, f, {"genero": {"novo": E.tax.normalizar(genero), "fonte": "você", "nivel": "alta"}})
        feitos, ultimo = feitos + 1, f.genero
    if not feitos:
        raise Erro("Escreva o gênero antes de confirmar.")
    return {"ok": True, "feitos": feitos, "genero": ultimo}


def r_desfazer(c):
    sobre = E.cache.sobrescritas()
    n = 0
    for f in E.faixas:
        if f.caminho in (c.get("caminhos") or []):
            ajustes.desfazer(E.cache, sobre, f)
            n += 1
    return {"ok": True, "desfeitas": n}


def r_precisao_som(_):
    teste = _treinar()
    return {"pronto": E.classificador.pronto, "motivo": E.classificador.motivo, "autoteste": teste}


def r_pausar(c):
    (E.pausa.set if c.get('pausar', True) else E.pausa.clear)()
    return {"ok": True}


def r_cancelar(_):
    E.pausa.clear()
    E.cancelar.set()
    return {"ok": True}


ROTAS_GET = {"/api/vivo": lambda _: {"ok": True}, "/api/estado": r_estado, "/api/faixas": r_faixas, "/api/sem-genero": r_sem_genero,
             "/api/config": r_config, "/api/grupos": r_grupos, "/api/conferir": r_conferir, "/api/propostas": r_propostas, "/api/precisao-som": r_precisao_som}
ROTAS_POST = {
    "/api/pasta": r_pasta, "/api/analisar": r_analisar, "/api/padroes": r_padroes, "/api/previa": r_previa,
    "/api/definir-genero": r_definir_genero, "/api/copiar": r_copiar, "/api/melhorar": r_melhorar, "/api/cancelar": r_cancelar,
    "/api/config": r_config_salvar, "/api/identificar": r_identificar, "/api/decidir": r_decidir,
    "/api/desfazer": r_desfazer, "/api/pausar": r_pausar, "/api/abrir-pasta": r_abrir_pasta, "/api/grupos-mover": r_grupos_mover, "/api/grupos-renomear": r_grupos_renomear, "/api/genero-faixa": r_genero_faixa,
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _enviar(self, codigo, corpo: bytes, tipo="application/json; charset=utf-8"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, codigo, dados):
        self._enviar(codigo, json.dumps(dados, ensure_ascii=False).encode("utf-8"))

    def _autorizado(self) -> bool:
        porta = self.server.server_address[1]
        host_ok = self.headers.get("Host", "") in (f"127.0.0.1:{porta}", f"localhost:{porta}")
        return host_ok and secrets.compare_digest(self.headers.get("X-Token", ""), TOKEN)

    def _capa(self, consulta):
        porta = self.server.server_address[1]
        q = urllib.parse.parse_qs(consulta)
        ok = self.headers.get("Host", "") in (f"127.0.0.1:{porta}", f"localhost:{porta}") and \
            secrets.compare_digest((q.get("t") or [""])[0], TOKEN)
        nome = Path((q.get("arq") or [""])[0]).name
        arq = pasta_dados() / "capas" / nome
        if not ok or not nome or not arq.is_file():
            return self._json(404, {"erro": "Não encontrado."})
        tipo = "image/png" if arq.suffix == ".png" else "image/jpeg"
        return self._enviar(200, arq.read_bytes(), tipo)

    def do_GET(self):
        partes = urllib.parse.urlsplit(self.path)
        if partes.path == "/api/capa":
            return self._capa(partes.query)
        self.path = partes.path
        if self.path in ("/", "/index.html"):
            html = (WEB / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", TOKEN)
            return self._enviar(200, html.encode("utf-8"), "text/html; charset=utf-8")
        return self._rota(ROTAS_GET.get(self.path), {})

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length") or 0)
        if tamanho > 1_000_000:
            return self._json(413, {"erro": "Pedido grande demais."})
        try:
            corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        except ValueError:
            return self._json(400, {"erro": "Pedido inválido."})
        return self._rota(ROTAS_POST.get(self.path), corpo)

    def _rota(self, funcao, corpo):
        if funcao is None:
            return self._json(404, {"erro": "Não encontrado."})
        if not self._autorizado():
            return self._json(403, {"erro": "Acesso negado."})
        E.ultimo_sinal = time.monotonic()
        try:
            self._json(200, funcao(corpo))
        except Erro as e:
            self._json(400, {"erro": str(e)})
        except Exception as e:  # noqa: BLE001
            self._json(500, {"erro": f"Erro inesperado: {e}"})


class Servidor(ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # O navegador fecha conexões o tempo todo (recarregar, trocar de aba): não é erro do programa.
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return
        super().handle_error(request, client_address)


def criar_servidor(porta: int = 0, arquivo_cache=None, pasta_config=None) -> Servidor:
    global E
    E = Estado(arquivo_cache, pasta_config)
    return Servidor(("127.0.0.1", porta), Handler)


def _abrir_janela(url: str) -> None:
    """No Windows abre como janela de aplicativo (Edge ou Chrome, sem barra de abas); senão, no navegador padrão."""
    if os.name == "nt":
        bases = [os.environ.get(v) for v in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
        for base in filter(None, bases):
            for rel in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                exe = Path(base) / rel
                if exe.is_file():
                    try:
                        subprocess.Popen([str(exe), f"--app={url}", "--window-size=1200,900"],
                                         creationflags=subprocess.CREATE_NO_WINDOW)
                        return
                    except OSError:
                        pass
    webbrowser.open(url)


def _preparar_saida() -> None:
    """Sem janela de terminal (programa instalado) não existe saída padrão: mensagens e erros vão para um arquivo de log."""
    if sys.stdout is None or sys.stderr is None:
        try:
            log = open(pasta_dados() / "mixteca.log", "a", encoding="utf-8", buffering=1)
            sys.stdout = sys.stdout or log
            sys.stderr = sys.stderr or log
        except OSError:
            pass


def _janela_propria(url: str) -> bool:
    """Abre o programa em uma janela própria (WebView do Windows). Só volta quando a janela é fechada.
    Devolve False se não der (biblioteca ou WebView ausente): aí o programa usa o navegador."""
    try:
        import webview
        webview.create_window("Mixteca", url, width=1240, height=860, min_size=(900, 600))
        webview.start()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"Janela própria indisponível ({e}); usando o navegador.")
        return False


def _vigia_do_navegador() -> None:
    """No modo navegador não há janela para fechar o programa: ele encerra sozinho quando a página some
    (sem sinal de vida por alguns minutos) e nenhuma tarefa está rodando."""
    while True:
        time.sleep(15)
        with E.lock:
            ocupado = E.job["fase"] == "rodando"
        if E.ultimo_sinal and not ocupado and time.monotonic() - E.ultimo_sinal > 180:
            os._exit(0)


def iniciar(abrir_navegador: bool = True) -> None:
    _preparar_saida()
    srv = criar_servidor()
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Mixteca rodando em {url}")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    if abrir_navegador:
        if _janela_propria(url):
            return  # janela fechada: encerra o programa
        _abrir_janela(url)
        threading.Thread(target=_vigia_do_navegador, daemon=True).start()
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
