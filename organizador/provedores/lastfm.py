"""Last.fm (opcional, chave gratuita): tags de gênero feitas pela comunidade. Uso pessoal/não comercial."""
import json
import urllib.parse

BASE = "https://ws.audioscrobbler.com/2.0/"


def tags(cli, chave: str, artista: str, titulo: str) -> dict:
    q = urllib.parse.urlencode({"method": "track.gettoptags", "artist": artista, "track": titulo, "api_key": chave,
                                "format": "json", "autocorrect": 1})
    status, corpo = cli.get(f"{BASE}?{q}")
    if status != 200:
        return {}
    lista = json.loads(corpo).get("toptags", {}).get("tag", [])
    if isinstance(lista, dict):
        lista = [lista]
    return {t["name"]: int(t.get("count", 0) or 0) for t in lista if t.get("name")}
