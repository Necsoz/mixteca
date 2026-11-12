"""Nomes de gêneros: normalização, o que é "genérico demais" e preferências locais opcionais.

A versão pública usa só ALIASES_PADRAO. Regras pessoais (agrupar subgêneros, dicas por artista) vêm
exclusivamente do arquivo local de preferências e nunca fazem parte do código distribuído.
"""
import re
import unicodedata

ALIASES_PADRAO = {
    "big room": "Big Room", "big room house": "Big Room", "mainstage": "Big Room",  # outro nome usado para o mesmo estilo
    "electro house": "Electro House", "progressive house": "Progressive House", "prog house": "Progressive House",
    "future house": "Future House", "bass house": "Bass House", "tech house": "Tech House",
    "deep house": "Deep House", "tropical house": "Tropical House", "house": "House",
    "techno": "Techno", "trance": "Trance", "psytrance": "Psytrance", "hardstyle": "Hardstyle",
    "drum and bass": "Drum & Bass", "drum n bass": "Drum & Bass", "dnb": "Drum & Bass",
    "dubstep": "Dubstep", "trap": "Trap", "future bass": "Future Bass", "electro": "Electro",
    "hip hop": "Hip-Hop", "hiphop": "Hip-Hop", "rap": "Hip-Hop", "r b": "R&B", "rnb": "R&B",
    "rock": "Rock", "indie rock": "Indie Rock", "alternative rock": "Alternative Rock", "alternative": "Alternative",
    "indie": "Indie", "pop": "Pop", "metal": "Metal", "punk": "Punk", "punk rock": "Punk Rock",
    "electronic": "Electronic", "electronica": "Electronic", "electronic dance music": "EDM", "edm": "EDM",
    "dance": "Dance", "bass music": "Bass Music",
}
# Rótulos amplos demais: servem de ponto de partida, mas ainda vale tentar achar um gênero mais específico.
GENERICOS = {"electronic", "edm", "dance", "dance pop", "bass music", "other", "misc", "unknown", "various", "genre", "musica eletronica"}
_PALAVRAS = re.compile(
    r"\b(house|techno|trance|step|bass|rock|pop|metal|hip hop|rap|drum|trap|indie|punk|hardcore|hardstyle|edm|dance|"
    r"electro|electronic|funk|reggae|jazz|blues|country|folk|soul|disco|ambient|chill|classical|latin|"
    r"grunge|emo|ska|breakbeat|garage|jungle|big room|downtempo|synthwave|phonk|riddim|sertanejo|pagode|samba)\b"
)


# Gênero na tag que é claramente lixo (nome de site, número, "unknown"...): só estes são tratados como vazios.
# Qualquer outro gênero que o usuário já tenha na música é respeitado, mesmo que o programa não o conheça.
_LIXO_GENERO = re.compile(r"spotify|youtube|soundcloud|download|www\.|\.com\b|\bmp3\b|\b(?:audio|video|official|playlist|favou?rites?|my music|new|none|n a|track|songs?|music|musica|sem genero|desconhecido|unknown|no genre)\b")
_ELETRONICA = re.compile(r"\b(house|techno|trance|step|dubstep|riddim|bass|edm|electro|electronic|dance|big room|mainstage|drum|dnb|trap|hardstyle|hardcore|psy|breakbeat|garage|jungle|future|synthwave|phonk|deathstep|tearout)\b")
_OUTRAS = re.compile(r"\b(rock|metal|punk|grunge|emo|country|folk|jazz|blues|classical|reggae|sertanejo|pagode|samba|forro|mpb|gospel|hip hop|rap|soul|r and b|latin|pop)\b")

_PARTES = re.compile(r"\s*(?:/|;|,|&|\bfeat\.?|\bft\.?|\bvs\.?| x )\s*", re.I)


def chave(texto: str) -> str:
    s = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    s = s.replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\band\b", "and", s)
    s = re.sub(r"\s+", " ", s).strip()
    return {"drum and bass": "drum and bass", "drum n bass": "drum and bass"}.get(s, s)


class Taxonomia:
    def __init__(self, preferencias: dict | None = None):
        p = preferencias or {}
        self._manter = {chave(g): str(g) for g in p.get("manter_generos", []) if g}
        self._mapa = {chave(k): str(v) for k, v in (p.get("mapa_generos") or {}).items() if k and v}
        self._dicas = []
        for d in p.get("artistas_dica", []):
            if d.get("genero") and d.get("artistas"):
                anos = d.get("anos") or [0, 9999]
                self._dicas.append({
                    "artistas": {chave(a) for a in d["artistas"]}, "genero": str(d["genero"]),
                    "anos": (int(anos[0]), int(anos[1])), "converter": {chave(c) for c in d.get("converter", [])},
                })
        self.personalizada = bool(self._manter or self._mapa or self._dicas)

    def normalizar(self, texto: str) -> str:
        k = chave(texto)
        if not k:
            return ""
        if k in self._manter:
            return self._manter[k]
        if k in self._mapa:
            return self._mapa[k]
        if k in ALIASES_PADRAO:
            return ALIASES_PADRAO[k]
        original = (texto or "").strip()
        return original.title() if original.islower() or original.isupper() else original

    def generico(self, genero: str) -> bool:
        return chave(genero) in GENERICOS or not chave(genero)

    @staticmethod
    def suspeito(genero: str) -> bool:
        """Gênero gravado que não faz sentido (nome de site, só números...). Gêneros desconhecidos mas plausíveis NÃO entram aqui."""
        k = chave(genero)
        return bool(genero and genero.strip()) and (not k or k.isdigit() or len(k) > 40 or bool(_LIXO_GENERO.search(k)))

    @staticmethod
    def familia(genero: str) -> str | None:
        """"eletronica", "outra" (rock, pop, sertanejo...) ou None quando não dá para saber."""
        k = chave(genero)
        if _ELETRONICA.search(k):
            return "eletronica"
        return "outra" if _OUTRAS.search(k) else None

    @staticmethod
    def parece_genero(tag: str) -> bool:
        k = chave(tag)
        return k in ALIASES_PADRAO or bool(_PALAVRAS.search(k))

    def dica(self, artista: str, ano: str | int | None):
        """Dica local por artista e época: (gênero, {gêneros que ela pode substituir}) ou None."""
        partes = {chave(artista)} | {chave(p) for p in _PARTES.split(artista or "")}
        try:
            y = int(str(ano)[:4])
        except ValueError:
            y = None
        for d in self._dicas:
            if partes & d["artistas"] and (y is None or d["anos"][0] <= y <= d["anos"][1]):
                return d["genero"], d["converter"], y is not None
        return None


# Famílias de gêneros próximos (opção "agrupar gêneros próximos" na hora de montar as pastas). A ordem importa:
# a primeira regra que casar decide. O gênero gravado na tag continua o específico; só a PASTA usa a família.
_GRUPOS = [
    ("Dubstep", r"dubstep|brostep|riddim|deathstep|tearout|chillstep|drumstep|\b140\b"),
    ("Drum & Bass", r"drum and bass|drum n bass|\bdnb\b|\bd n b\b|jungle|neurofunk|liquid funk|jump up"),
    ("Hardstyle & Hardcore", r"hardstyle|rawstyle|hardcore|frenchcore|gabber|hard dance|uptempo"),
    ("Trance", r"trance|goa"),
    ("Techno", r"techno|minimal"),
    ("Big Room", r"big room|mainstage|festival"),
    ("Trap & Future Bass", r"future bass|\btrap\b|bass music|midtempo|glitch hop|wave\b"),
    ("House", r"house|uk garage|garage|nu disco|disco|funky|electro\b|complextro|moombah"),
    ("Hip-Hop & R&B", r"hip hop|\brap\b|r and b|\brnb\b|\bsoul\b|drill|grime|funk carioca"),
    ("Metal", r"metal|metalcore|deathcore|djent"),
    ("Rock", r"rock|punk|grunge|emo\b|indie|alternative|post hardcore|shoegaze"),
    ("Reggae", r"reggae|dancehall|\bska\b|dub\b"),
    ("Pop", r"\bpop\b|synthpop|k pop|j pop"),
    ("Sertanejo & Brasil", r"sertanej|pagode|samba|forro|\bmpb\b|axe\b|piseiro|arrocha|funk\b|bossa"),
    ("Latina", r"reggaeton|latin|salsa|bachata|cumbia"),
    ("Jazz & Blues", r"jazz|blues|swing"),
    ("Clássica & Trilha", r"classical|classica|orchestra|soundtrack|score\b|trilha"),
    ("Chill & Ambient", r"ambient|chill|downtempo|lo fi|lofi|new age"),
    ("Eletrônica (outros)", r"electronic|edm|dance|breakbeat|breaks|synthwave|phonk|idm|electro"),
]
_GRUPOS = [(nome, re.compile(padrao)) for nome, padrao in _GRUPOS]


def grupo(genero: str) -> str:
    """Família do gênero (ex.: Riddim -> Dubstep, Tech House -> House). Sem família conhecida, devolve o próprio gênero."""
    k = chave(genero)
    if "hardcore" in k and ("punk" in k or "post" in k):
        return "Rock"
    for nome, rx in _GRUPOS:
        if rx.search(k):
            return nome
    return genero
