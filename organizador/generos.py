"""Gêneros: limpeza do texto da tag e faixa de BPM típica.

A faixa de BPM serve só para decidir entre "andamento, metade ou dobro" (ex.: Dubstep a 140 que soa como 70).
"""
import re

FAIXAS = {
    "big room": (126, 132),
    "electro house": (126, 132),
    "future house": (120, 130),
    "progressive house": (120, 130),
    "tech house": (122, 130),
    "bass house": (124, 132),
    "house": (118, 130),
    "techno": (122, 142),
    "trance": (128, 142),
    "dubstep": (138, 150),
    "brostep": (138, 150),
    "melodic dubstep": (138, 150),
    "riddim": (138, 150),
    "future bass": (130, 160),
    "trap": (130, 160),
    "drum & bass": (160, 180),
    "drum and bass": (160, 180),
    "dnb": (160, 180),
    "hardstyle": (145, 160),
    "electro": (120, 135),
    "dance": (100, 150),
    "edm": (118, 152),
}
PADRAO = (85, 175)  # gêneros sem faixa conhecida (Rock, Indie, Pop...)
EXIBICAO = {"edm": "EDM", "dnb": "DnB"}


def limpar_genero(texto: str) -> str:
    """Pega o primeiro gênero da tag (se houver vários) e arruma maiúsculas."""
    if not texto:
        return ""
    primeiro = re.split(r"[;/|,\x00]", texto)[0].strip()
    if not primeiro:
        return ""
    baixo = primeiro.lower()
    if baixo in EXIBICAO:
        return EXIBICAO[baixo]
    if primeiro.islower() or primeiro.isupper():
        return primeiro.title()
    return primeiro


def faixa_bpm(genero: str) -> tuple[int, int]:
    baixo = (genero or "").lower().strip()
    if baixo in FAIXAS:
        return FAIXAS[baixo]
    for chave in sorted(FAIXAS, key=len, reverse=True):
        if chave in baixo:
            return FAIXAS[chave]
    return PADRAO


_SEPARADORES = re.compile(r"\s*(?:/|;|,|&|\bfeat\.?|\bft\.?)\s*", re.I)


def artista_principal(artista: str) -> str:
    """Primeiro artista de uma lista ("Tony Junior/Kura" -> "Tony Junior")."""
    texto = (artista or "").strip()
    if texto.casefold().startswith("ac/dc"):
        return "AC/DC"
    return _SEPARADORES.split(texto, maxsplit=1)[0].strip()


def chave_artista(artista: str) -> str:
    return artista_principal(artista).casefold()
