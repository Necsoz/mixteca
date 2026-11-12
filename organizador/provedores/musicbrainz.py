"""MusicBrainz (dados centrais em domínio público, CC0). Limite: 1 pedido por segundo, com User-Agent identificado."""
import json
import urllib.parse

BASE = "https://musicbrainz.org/ws/2"
FONTE = "MusicBrainz"


def _lucene(texto: str) -> str:
    return '"' + (texto or "").replace("\\", " ").replace('"', " ").strip() + '"'


def _artistas(credito: list) -> tuple[str, str]:
    nome, primeiro = "", ""
    for c in credito or []:
        nome += c.get("name") or c.get("artist", {}).get("name", "")
        nome += c.get("joinphrase", "")
        primeiro = primeiro or c.get("artist", {}).get("id", "")
    return nome.strip(), primeiro


def escolher_lancamento(releases: list, album_atual: str = "") -> dict | None:
    """Escolhe o lançamento mais provável: o mesmo álbum da tag, senão o oficial mais antigo que não seja coletânea/ao vivo."""
    if not releases:
        return None
    from .. import casamento

    def tipo(r):
        g = r.get("release-group") or {}
        return g.get("primary-type") or "", set(g.get("secondary-types") or [])

    if album_atual:
        for r in releases:
            if casamento.sim(album_atual, r.get("title", "")) >= 0.9:
                return r
    bons = [r for r in releases if r.get("status", "Official") == "Official" and not (tipo(r)[1] & {"Compilation", "Live", "Remix", "DJ-mix", "Mixtape/Street"})]
    return sorted(bons or releases, key=lambda r: (r.get("date") or "9999") or "9999")[0]


def candidato_de_gravacao(g: dict, album_atual: str = "") -> dict:
    artista, artista_id = _artistas(g.get("artist-credit"))
    rel = escolher_lancamento(g.get("releases") or [], album_atual)
    grupo = (rel or {}).get("release-group") or {}
    tags = {t["name"]: int(t.get("count", 1) or 1) for t in (g.get("tags") or []) if t.get("name")}
    for ge in g.get("genres") or []:
        tags[ge["name"]] = max(tags.get(ge["name"], 0), int(ge.get("count", 1) or 1))
    return {
        "fonte": FONTE, "mbid": g.get("id", ""), "titulo": g.get("title", ""), "artista": artista, "artista_mbid": artista_id,
        "album": (rel or {}).get("title", ""), "tipo": grupo.get("primary-type", ""),
        "ano": ((rel or {}).get("date") or "")[:4], "duracao": (g.get("length") or 0) / 1000.0,
        "release_id": (rel or {}).get("id", ""), "release_group_id": grupo.get("id", ""),
        "generos": {}, "tags_gravacao": tags,
    }


def buscar(cli, artista: str, titulo: str, album_atual: str = "", limite: int = 8) -> list[dict]:
    consulta = f"recording:{_lucene(titulo)}" + (f" AND artist:{_lucene(artista)}" if artista else "")
    url = f"{BASE}/recording?{urllib.parse.urlencode({'query': consulta, 'fmt': 'json', 'limit': limite})}"
    status, corpo = cli.get(url)
    if status != 200:
        return []
    return [candidato_de_gravacao(g, album_atual) for g in json.loads(corpo).get("recordings", [])]


def por_id(cli, mbid: str, album_atual: str = "") -> dict | None:
    url = f"{BASE}/recording/{mbid}?inc=artist-credits+releases+release-groups+tags+genres&fmt=json"
    status, corpo = cli.get(url)
    return candidato_de_gravacao(json.loads(corpo), album_atual) if status == 200 else None


def generos_do_artista(cli, artista_mbid: str) -> dict:
    if not artista_mbid:
        return {}
    status, corpo = cli.get(f"{BASE}/artist/{artista_mbid}?inc=genres+tags&fmt=json")
    if status != 200:
        return {}
    d = json.loads(corpo)
    saida = {t["name"]: int(t.get("count", 1) or 1) for t in d.get("tags", []) if t.get("name")}
    for g in d.get("genres", []):
        saida[g["name"]] = max(saida.get(g["name"], 0), int(g.get("count", 1) or 1))
    return saida
