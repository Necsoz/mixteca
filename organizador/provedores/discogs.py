"""Discogs (opcional, exige um token gratuito): estilos de lançamentos com a música (ex.: Electro House)."""
import json
import re
import urllib.parse

BASE = "https://api.discogs.com/database/search"
_SEP = re.compile(r"\s*(?:/|;|,|&|\bfeat\.?|\bft\.?|\bfeaturing\b|\bvs\.?|\bx\b|\band\b)\s*", re.I)


def _limpar_titulo(t: str) -> str:
    return re.sub(r"\s*[\(\[][^\)\]]*(?:mix|edit|version|remaster|extended|original|radio)[^\)\]]*[\)\]]", "", t or "", flags=re.I).strip()


def _buscar(cli, token: str, **filtros) -> dict:
    q = urllib.parse.urlencode({**filtros, "type": "release", "per_page": 5, "token": token})
    status, corpo = cli.get(f"{BASE}?{q}", usar_cache=False, guardar=False)  # o token nunca vai para o cache
    if status != 200:
        return {}
    conta: dict[str, int] = {}
    for r in json.loads(corpo).get("results", [])[:5]:
        for st in r.get("style") or []:
            conta[st] = conta.get(st, 0) + 2
        for g in r.get("genre") or []:
            conta[g] = conta.get(g, 0) + 1
    return conta


def estilos(cli, token: str, artista: str, titulo: str) -> dict:
    titulo = _limpar_titulo(titulo)
    primeiro = next((p.strip() for p in _SEP.split(artista or "") if p.strip()), "")
    return (_buscar(cli, token, artist=primeiro, track=titulo)
            or _buscar(cli, token, q=f"{primeiro} {titulo}".strip()))
