"""Tira lixo de endereços de sites e de vídeos ("Official Video", "www...", "320kbps"...) de títulos, artistas,
álbuns e nomes de arquivo, para a biblioteca ficar com cara profissional. Versões e créditos de remix
("Original Mix", "Extended Mix", "Hardwell Remix", "feat. ...") são preservados.

Nomes específicos de sites ou programas que você queira remover (sem endereço .com) ficam na lista `limpar_termos`
do arquivo local de preferências, não no código."""
import re

# trechos que denunciam site de download / vídeo (dentro de parênteses, colchetes ou chaves)
_LIXO = re.compile(
    r"spotify|youtube|"
    r"free\s*(?:download|dl)|\bdownload\b|\bbaixar\b|"
    r"official\s*(?:music\s*)?(?:video|audio|lyric|visuali[sz]er|clip)|\bofficial\b|lyric\s*video|\blyrics?\b|visuali[sz]er|"
    r"v[ií]deo\s*oficial|[aá]udio\s*oficial|clipe\s*oficial|\boficial\b|"
    r"out\s*now|ncs\s*release|copyright\s*free|no\s*copyright|"
    r"\b(?:hd|hq|4k|1080p|720p)\b|\d{2,3}\s*kbps|"
    r"www\.|\.(?:com|net|org|io)\b",
    re.I,
)
# se o grupo tem algo disso, é versão/crédito (não lixo), mesmo que também cite "official"
_VERSAO = re.compile(r"\b(?:mix|remix|edit|vip|bootleg|rework|version|dub|instrumental|acoustic|live|feat|ft|featuring|with|vs|remaster(?:ed)?)\b", re.I)
# grupos que podem fazer parte do nome de verdade: nunca são removidos só por não aparecerem na internet
PROTEGE = re.compile(
    r"\b(?:mix|remix|edit|vip|bootleg|rework|version|dub|instrumental|acoustic|live|feat|ft|featuring|with|vs|remaster(?:ed)?|"
    r"radio|extended|original|club|short|long|clean|dirty|explicit|bonus|deluxe|single|album|mashup|flip|refix|cut|"
    r"sped|slowed|nightcore|karaoke|cover|tribute|reprise|intro|outro|interlude|demo|session|unplugged|"
    r"part|pt|vol|volume|ao vivo|ac[uú]stic[oa]|vers[aã]o|remasterizad[oa]|\d{4})\b", re.I)
GRUPO = re.compile(r"\s*[\(\[\{]([^\)\]\}]*)[\)\]\}]")
_extra_grupo = None  # nomes locais (preferências): dentro de parênteses/colchetes
_extra_solto = None  # nomes locais soltos no texto


def definir_termos(termos) -> None:
    """Registra os nomes de sites/programas (da lista `limpar_termos` das preferências) que devem ser removidos."""
    global _extra_grupo, _extra_solto
    lista = sorted({re.escape(t.strip()).replace(r"\ ", r"\s*") for t in (termos or []) if isinstance(t, str) and t.strip()}, key=len, reverse=True)
    if not lista:
        _extra_grupo = _extra_solto = None
        return
    alt = "|".join(lista)
    _extra_grupo = re.compile(alt, re.I)
    _extra_solto = re.compile(r"\s*[-–|]?\s*(?:" + alt + r")(?:\.\w+)?\b", re.I)
_DOMINIO = re.compile(r"\s*\S*\b(?:www\.\S+|[\w-]+\.(?:com|net|org|io))\b", re.I)
_SUFIXO_CANAL = re.compile(r"\s*[-–]\s*topic\s*$|\s*vevo\s*$", re.I)
_CAUDA_PIPE = re.compile(r"\s*[|｜]\s*[^|]*\b(?:official|lyric|video|audio|visuali[sz]er|oficial)\b.*$", re.I)
_NUMERO_INICIAL = re.compile(r"^\s*(?:\d{1,3}\s*[-._)]\s+|0\d\s+)")


def _tirar_grupos_lixo(texto: str) -> str:
    def troca(m):
        miolo = m.group(1)
        lixo = _LIXO.search(miolo) or (_extra_grupo is not None and _extra_grupo.search(miolo))
        return "" if lixo and not _VERSAO.search(miolo) else m.group(0)
    return GRUPO.sub(troca, texto)


def grupos_estranhos(texto: str) -> list[str]:
    """Trechos entre parênteses/colchetes que não parecem versão nem crédito: candidatos a "texto que não é do nome"."""
    return [m.group(1).strip() for m in GRUPO.finditer(texto or "") if m.group(1).strip() and not PROTEGE.search(m.group(1))]


def sem_grupos_estranhos(texto: str) -> str:
    """Usado só para PESQUISAR: tira os grupos estranhos para a busca na internet não falhar por causa deles."""
    t = GRUPO.sub(lambda m: m.group(0) if PROTEGE.search(m.group(1)) else "", texto or "")
    return re.sub(r"\s{2,}", " ", t).strip(" -–|_.\t")


_VAZIO = re.compile(r"^(?:unknown(?:\s+(?:album|artist|title|track))?|desconhecid[oa]|sem\s+t[ií]tulo|untitled|no\s+title|"
                    r"(?:track|faixa|audio)\s*\d+|n\s*/?\s*a|none|null|\?+|-+)$", re.I)


def limpar_texto(texto: str) -> str:
    if _VAZIO.match((texto or "").strip()):
        return ""  # "Unknown Album", "Track 01"...: é o mesmo que não ter a informação
    """Limpa um título, artista ou álbum. Devolve "" se só havia lixo."""
    t = texto or ""
    t = _tirar_grupos_lixo(t)
    t = _CAUDA_PIPE.sub("", t)
    if _extra_solto is not None:
        t = _extra_solto.sub("", t)
    t = _DOMINIO.sub("", t)
    t = _SUFIXO_CANAL.sub("", t)
    t = re.sub(r"\(\s*\)|\[\s*\]|\{\s*\}", "", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -–|_.\t")
    return t


_DO_YOUTUBE = re.compile(r"[\(\[]\s*youtube\s*[\)\]]", re.I)


def sem_canal(texto: str, original: str) -> str:
    """Arquivo baixado do YouTube: o título do vídeo costuma terminar com o nome do canal ("Artista - Música - Canal").
    Tira o que vem depois de "Artista - Música", a não ser que seja versão (Extended Mix, Radio Edit...)."""
    if not _DO_YOUTUBE.search(original or ""):
        return texto
    partes = re.split(r"\s+[-–]\s+", texto)
    if len(partes) < 3:
        return texto
    return " - ".join(partes[:2] + [p for p in partes[2:] if PROTEGE.search(p)])


def limpar_stem(stem: str) -> str:
    """Limpa o nome de um arquivo (sem extensão): números de faixa, underscores e lixo de site."""
    s = _NUMERO_INICIAL.sub("", (stem or "").replace("_", " "))
    s = sem_canal(limpar_texto(s), stem)
    return s or (stem or "").strip()


def nome_de_arquivo(titulo: str, artista: str, stem_original: str, maximo: int = 140) -> str:
    """"Artista - Título" quando as tags existem; senão o nome original, só que limpo."""
    t, a = limpar_texto(titulo), limpar_texto(artista)
    if t and a:
        a_arq = re.sub(r"(?<=\w{3})\s*/\s*(?=\w{3})", ", ", a)  # "Fulano/Ciclano" -> "Fulano, Ciclano" (AC/DC fica)
        nome = t if t.casefold().startswith(a_arq.casefold() + " - ") else f"{a_arq} - {t}"
    else:
        nome = limpar_stem(stem_original)
    return nome[:maximo].rstrip(" .-")
