"""Compara o que sabemos da música (tags/nome do arquivo/duração) com um candidato da internet e dá uma nota de confiança."""
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from . import limpeza

_SEP_ARTISTAS = re.compile(r"\s*(?:/|;|,|&|\bfeat\.?|\bft\.?|\bfeaturing\b|\bvs\.?|(?-i:(?<=\s)x(?=\s))|\band\b)\s*", re.I)
_VERSOES = re.compile(r"[\(\[][^\)\]]*(?:mix|edit|version|remaster|feat|ft\.|bootleg|remix|radio|extended|original)[^\)\]]*[\)\]]", re.I)


def _ascii(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


def norm(s: str, tirar_versao: bool = True) -> str:
    s = _VERSOES.sub(" ", s or "") if tirar_versao else (s or "")
    s = re.sub(r"\s-\s(?:original|extended|radio|club|album|single)\s*(?:mix|edit|version)?\s*$", " ", s, flags=re.I)
    s = _ascii(s).replace("&", " and ")
    s = re.sub(r"\b(feat|ft|featuring)\b.*$", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a: str, b: str) -> float:
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    r = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    if ta and tb:
        r = max(r, len(ta & tb) / max(len(ta), len(tb)) * (0.95 if ta != tb else 1.0))
    return r


def sim_artistas(a: str, b: str) -> float:
    if not norm(a) or not norm(b):
        return 0.0
    conjunto = lambda t: {norm(p) for p in _SEP_ARTISTAS.split(t or "") if norm(p)}  # noqa: E731
    ca, cb = conjunto(a), conjunto(b)
    melhor = max([sim(a, b)] + [sim(x, y) for x in ca for y in cb])
    inter = sum(1 for x in ca if any(sim(x, y) >= 0.9 for y in cb))
    return max(melhor * 0.97 if ca != cb else melhor, inter / max(1, min(len(ca), len(cb))) * 0.95)


def consulta_do_arquivo(titulo: str, artista: str, caminho: str) -> tuple[str, str, str]:
    """(artista, título, origem). Completa o que falta nas tags com o nome do arquivo ("Artista - Título")."""
    if titulo and artista:
        return artista, titulo, "tags"
    nome = re.sub(r"^\s*\d{1,3}\s*[-._)]\s*", "", Path(caminho).stem).replace("_", " ").strip()
    partes = [p.strip() for p in re.split(r"\s+-\s+", nome, maxsplit=1)]
    if len(partes) == 2 and all(partes):
        return artista or partes[0], titulo or partes[1], "arquivo" if not (titulo or artista) else "tags+arquivo"
    return artista, titulo or nome, "arquivo" if not titulo else "tags"


def sem_sobras(texto: str, referencia: str) -> str:
    """Compara o nome que está na música com o nome encontrado na internet e tira o que sobra e não faz parte dele
    (ex.: nome do site de onde o arquivo veio). Versões e créditos ("Extended Mix", "feat. X") são preservados.
    Só devolve o texto limpo se ele realmente bater com a referência; na dúvida devolve o original."""
    if not texto or not referencia:
        return texto
    ref = set(norm(referencia, False).split())

    def troca(m):
        miolo = m.group(1)
        toks = norm(miolo, False).split()
        if limpeza.PROTEGE.search(miolo) or (toks and all(t in ref for t in toks)):
            return m.group(0)
        return ""

    novo = limpeza.GRUPO.sub(troca, texto)
    cauda = re.match(r"^(.*\S)\s+[-–|]\s+([^-–|]+)$", novo)  # "Nome - Sobra" / "Nome | Sobra"
    if cauda and not limpeza.PROTEGE.search(cauda.group(2)) and not (set(norm(cauda.group(2), False).split()) & ref):
        novo = cauda.group(1)
    else:  # palavras soltas no fim: "Nome SOBRA"
        a, r = norm(novo, False).split(), norm(referencia, False).split()
        extra = a[len(r):]
        if r and a[:len(r)] == r and 0 < len(extra) <= 3 and not limpeza.PROTEGE.search(" ".join(extra)):
            palavras = novo.split()
            if len(palavras) == len(a):
                novo = " ".join(palavras[:len(r)])
    novo = re.sub(r"\s{2,}", " ", novo).strip(" -–|_.\t")
    return novo if novo and novo != texto and sim(novo, referencia) >= 0.9 else texto


def pontuar(cons_artista: str, cons_titulo: str, duracao: float, cand: dict, origem: str = "tags") -> dict:
    cons_titulo = sem_sobras(cons_titulo, cand.get("titulo", ""))
    st = sim(cons_titulo, cand.get("titulo", ""))
    sa = sim_artistas(cons_artista, cand.get("artista", "")) if cons_artista else None
    sd = None
    dd = None
    if duracao and cand.get("duracao"):
        dd = abs(duracao - cand["duracao"])
        sd = 1.0 if dd <= 3 else 0.7 if dd <= 8 else 0.35 if dd <= 20 else 0.0
    itens = [(0.5, st)] + ([(0.35, sa)] if sa is not None else []) + ([(0.15, sd)] if sd is not None else [])
    score = sum(w * s for w, s in itens) / sum(w for w, _ in itens)
    if st < 0.6:
        score = min(score, 0.5)
    if sd == 0.0:
        score *= 0.75
    alta = score >= 0.88 and st >= 0.85 and sa is not None and sa >= 0.8 and sd != 0.0
    if origem == "arquivo" and (sd is None or sd < 0.7):
        alta = False  # só o nome do arquivo e sem duração batendo: pede conferência
    nivel = "alta" if alta else "media" if score >= 0.7 else "baixa"
    return {"score": round(score, 3), "nivel": nivel, "titulo": round(st, 2), "artista": None if sa is None else round(sa, 2),
            "duracao_dif": None if dd is None else round(dd, 1)}
