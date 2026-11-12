"""AcoustID + Chromaprint (impressão digital do áudio). Precisa do fpcalc na pasta 'ferramentas' e de uma chave gratuita."""
import json
import urllib.parse

from ..ferramentas import achar, executar

BASE = "https://api.acoustid.org/v2/lookup"


def disponivel() -> bool:
    try:
        achar("fpcalc")
        return True
    except FileNotFoundError:
        return False


def impressao(caminho) -> tuple[int, str] | None:
    r = executar([achar("fpcalc"), "-json", "-length", "120", str(caminho)])
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
        return int(d["duration"]), d["fingerprint"]
    except (ValueError, KeyError):
        return None


def consultar(cli, chave: str, duracao: int, fingerprint: str) -> list[dict]:
    """[{"mbid", "score"}] ordenado do melhor para o pior."""
    q = urllib.parse.urlencode({"client": chave, "meta": "recordings", "duration": duracao, "fingerprint": fingerprint, "format": "json"})
    status, corpo = cli.get(f"{BASE}?{q}", guardar=False)
    if status != 200:
        return []
    d = json.loads(corpo)
    saida = []
    for r in d.get("results", []):
        for rec in r.get("recordings", []):
            saida.append({"mbid": rec["id"], "score": float(r.get("score", 0))})
    return sorted(saida, key=lambda x: -x["score"])
