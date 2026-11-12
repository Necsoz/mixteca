"""Decide o gênero de CADA música juntando as evidências (e monta as propostas de metadados).

Evidências, da mais para a menos forte:
  1. gênero já gravado na tag (se específico) — nunca é trocado;
  2. tags de gênero de fontes externas, só se a música foi identificada com confiança;
  3. sonoridade (parecida com músicas da sua biblioteca que já têm gênero) — complemento, nunca "alta" sozinha;
  4. dica local por artista/época (preferências opcionais) — só ajuda a desempatar, não decide sozinha.
Nunca copia o gênero do artista para todas as músicas dele: cada música é avaliada pela própria evidência.
"""
from .taxonomia import Taxonomia

PESO_FONTES = {"MusicBrainz": 0.6, "MusicBrainz (artista)": 0.4, "Last.fm": 0.7, "Discogs": 0.5}
FONTES_SO_GENERO: set[str] = set()  # fontes extras cujos nomes já são sempre gêneros (não passam pelo filtro de tags)
MIN_SOM_MEDIA = 0.7
MIN_SOM_PALPITE = 0.5


def votos_online(brutos: dict[str, dict], tax: Taxonomia) -> dict[str, float]:
    """brutos: {fonte: {tag: contagem}} -> {gênero normalizado: peso entre 0 e 1}, só com tags que são gêneros.

    Se alguma fonte trouxe um gênero específico, os rótulos amplos (ex.: "Dance / Pop", "Electronic") são ignorados:
    não adianta uma fonte genérica "empatar" com outra que sabe o estilo exato."""
    por_fonte: dict[str, dict[str, float]] = {}
    for fonte, tags in brutos.items():
        validas: dict[str, float] = {}
        for tag, n in tags.items():
            if fonte in FONTES_SO_GENERO or tax.parece_genero(tag):
                g = tax.normalizar(tag)
                validas[g] = validas.get(g, 0) + max(1, n)
        if validas:
            por_fonte[fonte] = validas
    if any(not tax.generico(g) for v in por_fonte.values() for g in v):
        por_fonte = {f: {g: n for g, n in v.items() if not tax.generico(g)} for f, v in por_fonte.items()}
        por_fonte = {f: v for f, v in por_fonte.items() if v}
    total: dict[str, float] = {}
    for fonte, validas in por_fonte.items():
        soma = sum(validas.values())
        for g, n in validas.items():
            total[g] = total.get(g, 0) + PESO_FONTES.get(fonte, 0.4) * n / soma
    norma = sum(PESO_FONTES.get(f, 0.4) for f in por_fonte)
    return {g: v / norma for g, v in total.items()} if norma else {}


def decidir_genero(genero_atual: str, votos: dict[str, float], nivel_id: str, som, artista: str, ano, tax: Taxonomia, rotulo: str = "MusicBrainz"):
    """Devolve (genero, fonte, nivel, confianca, nota) ou None quando não há evidência suficiente.

    `som` é (gênero, parcela) do classificador por sonoridade ou None.
    """
    especificos = {g: v for g, v in votos.items() if not tax.generico(g)}
    genericos = {g: v for g, v in votos.items() if tax.generico(g)}
    online = max(especificos.items(), key=lambda kv: kv[1]) if especificos and nivel_id in ("alta", "media") else None
    dica = tax.dica(artista, ano)

    # dica local: pode converter um gênero amplo vindo da internet (ex.: o mesmo estilo com outro nome) se o som não contradiz
    if online and dica and (tax_chave(online[0]) in dica[1]) and not (som and som[0] != dica[0] and som[1] >= 0.6):
        online = (dica[0], online[1])
        nota_dica = "ajustado pela preferência local"
    else:
        nota_dica = ""

    if online and som and som[0] == online[0]:
        return online[0], rotulo + " + som", "alta" if nivel_id == "alta" else "media", round(min(0.98, 0.6 + online[1] / 2 + som[1] / 4), 2), nota_dica
    if online:
        conf = round(min(0.95, 0.35 + online[1] * 0.6), 2)
        nivel = "alta" if nivel_id == "alta" and online[1] >= 0.5 else "media"
        nota = nota_dica
        if som and som[0] != online[0] and som[1] >= MIN_SOM_MEDIA:
            nivel, nota = "media", f"a sonoridade lembra {som[0]}; confira"
        return online[0], rotulo, nivel, conf, nota
    if som:
        g, p = som
        if dica and dica[0] == g:
            return g, "som + preferência local", "media" if p >= MIN_SOM_PALPITE else "baixa", round(p, 2), "sonoridade e preferência local concordam"
        if p >= MIN_SOM_MEDIA:
            return g, "som", "media", round(p, 2), "palpite pela sonoridade (parecida com músicas suas de " + g + ")"
        if p >= MIN_SOM_PALPITE:
            return g, "som", "baixa", round(p, 2), "palpite fraco pela sonoridade"
    if genericos and not genero_atual and nivel_id in ("alta", "media"):
        g = max(genericos.items(), key=lambda kv: kv[1])[0]
        return g, rotulo, "media", round(0.3 + genericos[g] * 0.4, 2), "só há informação ampla; mantido o gênero mais abrangente"
    return None


def tax_chave(g: str) -> str:
    from .taxonomia import chave
    return chave(g)
