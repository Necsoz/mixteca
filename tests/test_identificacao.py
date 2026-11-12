"""Testes da identificação online (com internet SIMULADA), gêneros, capas, preferências locais e gravação nas cópias.
Rodar: python tests/test_identificacao.py"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from organizador import casamento, config, decisao, escrita, identificacao, servidor  # noqa: E402
from organizador.classificador import ClassificadorSom  # noqa: E402
from organizador.modelos import Faixa  # noqa: E402
from organizador import extras, limpeza  # noqa: E402
from organizador.provedores import capas  # noqa: E402
from organizador.rede import Cliente, ErroRede  # noqa: E402
from organizador.store import Cache  # noqa: E402
from organizador.taxonomia import Taxonomia  # noqa: E402

# Preferências FICTÍCIAS só para testar o mecanismo (as regras reais de cada pessoa ficam fora do repositório).
PREFS_TESTE = {
    "mapa_generos": {"sub x": "Alfa", "sub y": "Alfa", "beta house": "Beta"},
    "manter_generos": ["Sub Z"],
    "artistas_dica": [{"artistas": ["Artista Dica"], "genero": "Alfa", "anos": [2011, 2016], "converter": ["house", "dance"]}],
}


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


def _jpeg(caminho: Path, lado=500) -> bytes:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0x2060c0:s={lado}x{lado}", "-frames:v", "1", str(caminho)], check=True)
    return caminho.read_bytes()


# ---------------------------------------------------------------- preferências e taxonomia
def test_sem_arquivo_de_preferencias_usa_padrao_e_cria_modelo_neutro():
    pasta = _tmp()
    assert config.carregar_preferencias(pasta) == {}
    modelo = json.loads((pasta / "user_preferences.json").read_text(encoding="utf-8"))
    assert modelo["mapa_generos"] == {} and modelo["artistas_dica"] == []  # nada pessoal
    t = Taxonomia(config.carregar_preferencias(pasta))
    assert not t.personalizada
    assert t.normalizar("drum and bass") == "Drum & Bass" and t.normalizar("BIG ROOM") == "Big Room"
    assert t.normalizar("Brostep") == "Brostep"  # versão pública não agrupa subgêneros
    assert t.generico("Electronic") and t.generico("EDM") and not t.generico("Big Room")
    assert t.dica("Qualquer", 2014) is None


def test_preferencias_com_defeito_nao_derrubam():
    pasta = _tmp()
    (pasta / "user_preferences.json").write_text("{ isto nao é json", encoding="utf-8")
    assert config.carregar_preferencias(pasta) == {}


def test_preferencias_locais_agrupam_e_dicas():
    t = Taxonomia(PREFS_TESTE)
    assert t.personalizada
    assert t.normalizar("Sub X") == "Alfa" and t.normalizar("sub y") == "Alfa"
    assert t.normalizar("sub z") == "Sub Z"  # exceção mantida
    d = t.dica("Artista Dica & Outro", "2013")
    assert d and d[0] == "Alfa" and "house" in d[1]
    assert t.dica("Artista Dica", "2020") is None  # fora da época
    assert t.dica("Artista Dica", "") is not None  # sem ano: dica vale (só ajuda, não decide sozinha)


def test_credenciais_ficam_locais_e_validam_chaves():
    pasta = _tmp()
    c = config.salvar_credenciais({"contato": " a@b.c ", "lastfm": "k", "naoexiste": "x"}, pasta)
    assert c["contato"] == "a@b.c" and "naoexiste" not in c
    assert config.carregar_credenciais(pasta)["lastfm"] == "k"


# ---------------------------------------------------------------- classificação por som
def _nuvens(n=30, seed=1):
    rng = np.random.default_rng(seed)
    a = rng.normal(0, 1, (n, 10)) + 4
    b = rng.normal(0, 1, (n, 10)) - 4
    c = rng.normal(0, 1, (4, 10))  # classe com poucos exemplos: ignorada
    return [list(v) for v in np.vstack([a, b, c])], ["Alfa"] * n + ["Beta"] * n + ["Rara"] * 4


def test_classificador_aprende_e_se_autoavalia():
    X, y = _nuvens()
    clf = ClassificadorSom()
    teste = clf.treinar(X, y)
    assert clf.pronto and teste["acuracia"] >= 0.95 and "Rara" not in teste["por_genero"]
    assert clf.prever([4.0] * 10)[0] == "Alfa" and clf.prever([-4.0] * 10)[0] == "Beta"
    assert clf.prever([1.0] * 3) is None  # vetor de tamanho diferente


def test_classificador_sem_base_nao_inventa():
    clf = ClassificadorSom()
    clf.treinar([[1.0, 2.0]] * 3, ["Alfa"] * 3)
    assert not clf.pronto and clf.prever([1.0, 2.0]) is None and clf.motivo


def test_classificador_desconfia_de_genero_que_confunde():
    rng = np.random.default_rng(3)
    X = [list(v) for v in rng.normal(0, 1, (60, 6))]  # mesma nuvem para os dois gêneros: impossível distinguir
    clf = ClassificadorSom()
    clf.treinar(X, ["Alfa"] * 30 + ["Beta"] * 30)
    assert clf.autoteste["acuracia"] < 0.8
    assert clf.prever([0.0] * 6) is None or clf.autoteste["por_genero"][clf.prever([0.0] * 6)[0]]["confiavel"]


# ---------------------------------------------------------------- casamento
def test_casamento_niveis_de_confianca():
    cand = {"titulo": "Atmosphere (Original Mix)", "artista": "Kaskade", "duracao": 200}
    assert casamento.pontuar("Kaskade", "Atmosphere", 201, cand)["nivel"] == "alta"
    assert casamento.pontuar("Kaskade", "Atmosphere", 330, cand)["nivel"] != "alta"       # duração muito diferente
    assert casamento.pontuar("Outra Pessoa", "Atmosphere", 200, cand)["nivel"] != "alta"   # artista diferente
    assert casamento.pontuar("Kaskade", "Outra Música Totalmente", 200, cand)["nivel"] == "baixa"
    assert casamento.pontuar("", "Atmosphere", 200, cand)["nivel"] != "alta"               # sem artista não é alta
    assert casamento.pontuar("Kaskade", "Atmosphere", None, cand, "arquivo")["nivel"] != "alta"  # só nome do arquivo e sem duração
    assert casamento.consulta_do_arquivo("", "", "/m/07 - Kaskade - Atmosphere.mp3") == ("Kaskade", "Atmosphere", "arquivo")
    assert casamento.sim_artistas("Tony Junior/Kura", "Tony Junior & Kura") >= 0.95


# ---------------------------------------------------------------- rede
def test_cliente_limita_ritmo_repete_e_guarda_cache():
    esperas, chamadas = [], []
    respostas = [(503, b"", {}), (200, b'{"ok":1}', {})]

    def transp(url, cab, t):
        chamadas.append(url)
        assert "OrganizadorMusical" in cab["User-Agent"] and "eu@x.com" in cab["User-Agent"]
        return respostas.pop(0) if respostas else (200, b'{"ok":1}', {})

    relogio = [0.0]
    cache = Cache(_tmp() / "c.db")
    cli = Cliente("eu@x.com", cache, transp, dormir=lambda s: (esperas.append(s), relogio.__setitem__(0, relogio[0] + s)), relogio=lambda: relogio[0])
    assert cli.get("https://musicbrainz.org/ws/2/a") == (200, b'{"ok":1}')  # tentou de novo depois do 503
    assert len(chamadas) == 2 and max(esperas) >= 2
    cli.get("https://musicbrainz.org/ws/2/a")  # vem do cache
    assert len(chamadas) == 2
    antes = len(esperas)
    cli.get("https://musicbrainz.org/ws/2/b")
    assert len(esperas) > antes and esperas[-1] >= 1.0 - 1e-6  # no máximo ~1 pedido por segundo no MusicBrainz


def test_cliente_desiste_com_erro_claro():
    cli = Cliente("a@b.c", None, lambda u, c, t: (503, b"", {}), dormir=lambda s: None)
    try:
        cli.get("https://musicbrainz.org/x")
        assert False
    except ErroRede:
        pass


# ---------------------------------------------------------------- capas
def test_capas_so_aceita_imagem_frontal_boa():
    tmp = _tmp()
    boa = _jpeg(tmp / "boa.jpg", 500)
    pequena = _jpeg(tmp / "p.jpg", 150)
    assert capas.dimensoes(boa)[:2] == (500, 500) and capas.dimensoes(b"nada") is None

    def cli_com(corpo, status=200):
        return Cliente("a@b.c", None, lambda u, c, t: (status, corpo, {}), dormir=lambda s: None)

    assert capas.baixar(cli_com(boa), tmp / "capas", "rel1") and (tmp / "capas").exists()
    assert capas.baixar(cli_com(pequena), tmp / "capas", "rel1") is None
    assert capas.baixar(cli_com(b"<html>", 200), tmp / "capas", "rel1") is None
    assert capas.baixar(cli_com(b"", 404), tmp / "capas", "rel1", "grp1") is None


# ---------------------------------------------------------------- decisão de gênero
def test_decisao_de_genero_por_evidencias():
    t = Taxonomia({})
    # online confiável + som concordando = alta
    g = decisao.decidir_genero("", {"Big Room": 0.8}, "alta", ("Big Room", 0.8), "X", "", t)
    assert g[0] == "Big Room" and g[2] == "alta"
    # só som: nunca alta
    assert decisao.decidir_genero("", {}, "baixa", ("Dubstep", 0.9), "X", "", t)[2] == "media"
    assert decisao.decidir_genero("", {}, "baixa", ("Dubstep", 0.55), "X", "", t)[2] == "baixa"
    assert decisao.decidir_genero("", {}, "baixa", ("Dubstep", 0.3), "X", "", t) is None
    # identificação fraca: não usa tags da internet
    assert decisao.decidir_genero("", {"Techno": 0.9}, "baixa", None, "X", "", t) is None
    # divergência entre fontes: pede conferência
    g = decisao.decidir_genero("", {"Techno": 0.9}, "alta", ("Trance", 0.85), "X", "", t)
    assert g[0] == "Techno" and g[2] == "media" and "lembra" in g[4]
    # só informação ampla: mantém o gênero mais abrangente, sem inventar subgênero
    g = decisao.decidir_genero("", {"Electronic": 0.9}, "alta", None, "X", "", t)
    assert g[0] == "Electronic" and g[2] == "media"


def test_votos_ignoram_tags_que_nao_sao_genero():
    t = Taxonomia({})
    v = decisao.votos_online({"MusicBrainz": {"seen live": 9, "american": 5, "house": 3, "electro house": 7}}, t)
    assert set(v) == {"House", "Electro House"} and v["Electro House"] > v["House"]


def test_dica_local_converte_so_se_o_som_nao_contradiz():
    t = Taxonomia(PREFS_TESTE)
    g = decisao.decidir_genero("", {"House": 0.8}, "alta", None, "Artista Dica", "2013", t)
    assert g[0] == "Alfa"
    g = decisao.decidir_genero("", {"House": 0.8}, "alta", ("Gama", 0.8), "Artista Dica", "2013", t)
    assert g[0] == "House"  # o som diz outra coisa: a dica não manda
    g = decisao.decidir_genero("", {"House": 0.8}, "alta", None, "Artista Dica", "2021", t)
    assert g[0] == "House"  # fora da época
    g = decisao.decidir_genero("", {"Techno": 0.8}, "alta", None, "Artista Dica", "2013", t)
    assert g[0] == "Techno"  # dica só converte os gêneros listados


# ---------------------------------------------------------------- gravação nas cópias
def _mp3(caminho: Path, tags: dict | None = None, segundos=6):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={segundos}", "-c:a", "libmp3lame"]
    for k, v in (tags or {}).items():
        cmd += ["-metadata", f"{k}={v}"]
    subprocess.run(cmd + [str(caminho)], check=True)


def test_gravar_tags_e_capa_so_na_copia_e_guarda_o_anterior():
    tmp = _tmp()
    orig = tmp / "o.mp3"
    _mp3(orig, {"title": "Velho"})
    antes = orig.read_bytes()
    copia = tmp / "c.mp3"
    copia.write_bytes(antes)
    capa = tmp / "capa.jpg"
    _jpeg(capa)
    r = escrita.gravar(copia, {"titulo": "Novo", "artista": "Fulano", "genero": "Big Room", "ano": "2014"}, str(capa))
    assert r["tags_anteriores"].get("title") == "Velho" and r["capa_gravada"]
    tags, tem_capa = escrita._ler(copia)
    assert tags["title"] == "Novo" and tags["artist"] == "Fulano" and tags["genre"] == "Big Room" and tem_capa
    assert orig.read_bytes() == antes  # original intacto
    assert not list(tmp.glob(".tmp-*"))
    r2 = escrita.gravar(copia, {"album": "Single X"})  # sem capa nova: a que já existe continua
    assert not r2["capa_gravada"] and escrita._ler(copia)[0]["album"] == "Single X" and escrita._ler(copia)[1]
    r3 = escrita.gravar(copia, {}, str(_jpeg(tmp / "capa2.jpg", 900) and tmp / "capa2.jpg"))  # capa melhor: troca, sem duplicar
    assert r3["capa_gravada"] and escrita._ler(copia)[1]
    # limpeza profissional: comentário/"encoded by" somem; BPM e tom (Camelot) entram; o que é útil fica
    sujo = tmp / "sujo.mp3"
    _mp3(sujo, {"title": "TORA", "artist": "Kura", "album": "TORA", "comment": "baixado em baixafacil.net", "encoded_by": "BaixaFacil", "track": "1"})
    escrita.gravar(sujo, {"titulo": "TORA", "artista": "Kura", "genero": "Big Room", "bpm": 128, "camelot": "8A"}, limpar=True)
    t = escrita._ler(sujo)[0]
    assert "comment" not in t and "encoded_by" not in t and t["title"] == "TORA" and t["track"] == "1", t
    assert t.get("tbpm") == "128" and t.get("tkey") == "8A" and t["genre"] == "Big Room", t
    erro = tmp / "falso.mp3"
    erro.write_bytes(b"lixo")
    try:
        escrita.gravar(erro, {"titulo": "x"})
        assert False
    except RuntimeError:
        assert erro.read_bytes() == b"lixo" and not list(tmp.glob(".tmp-*"))  # falhou sem estragar a cópia


# ---------------------------------------------------------------- integração completa (internet simulada)
def _faixa_som(caminho: Path, tipo: str, seed: int, tags: dict, segundos=24, sr=44100):
    rng = np.random.default_rng(seed)
    t = np.arange(int(sr * segundos)) / sr
    bpm = 128 if tipo == "a" else 140
    passo = 60 / bpm
    x = np.zeros_like(t)
    for k in range(int(segundos / passo)):
        i, n = int(k * passo * sr), int(0.18 * sr)
        tt = np.arange(n) / sr
        x[i:i + n] += (np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18))[: len(x[i:i + n])]
    if tipo == "a":   # brilhante: chimbais e sintetizador agudo
        x += 0.25 * rng.standard_normal(len(t)) * (np.sin(2 * np.pi * 8 * t) > 0.6) + 0.15 * np.sin(2 * np.pi * (1800 + 40 * seed) * t)
    else:             # grave pesado
        x += 0.5 * np.sin(2 * np.pi * (45 + seed) * t) * (1 + np.sin(2 * np.pi * 2 * t))
    x = x / np.abs(x).max() * 0.8
    wav = caminho.with_suffix(".wav")
    wavfile.write(str(wav), sr, (x * 32767).astype(np.int16))
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-c:a", "libmp3lame", "-q:a", "2"]
    for k, v in tags.items():
        cmd += ["-metadata", f"{k}={v}"]
    subprocess.run(cmd + [str(caminho)], check=True)
    wav.unlink()


def _internet_falsa(capa_bytes: bytes, chamadas: list):
    def transp(url, cab, t):
        chamadas.append(url)
        p = urllib.parse.urlsplit(url)
        if p.hostname == "musicbrainz.org" and p.path.endswith("/recording"):
            q = urllib.parse.parse_qs(p.query)["query"][0]
            if "Atmosphere" in q:
                rec = {"id": "rec-1", "title": "Atmosphere", "length": 24500,
                       "artist-credit": [{"name": "Kaskade", "artist": {"id": "art-1", "name": "Kaskade"}}],
                       "releases": [{"id": "rel-1", "title": "Atmosphere", "status": "Official", "date": "2013-05-01",
                                     "release-group": {"id": "rg-1", "primary-type": "Single"}}],
                       "tags": [{"name": "electro house", "count": 6}, {"name": "seen live", "count": 9}]}
                return 200, json.dumps({"recordings": [rec]}).encode(), {}
            return 200, b'{"recordings": []}', {}
        if p.hostname == "musicbrainz.org" and "/artist/" in p.path:
            return 200, json.dumps({"genres": [{"name": "electro house", "count": 4}]}).encode(), {}
        if p.hostname == "coverartarchive.org":
            return 200, capa_bytes, {}
        return 404, b"", {}
    return transp


# ---------------------------------------------------------------- fontes extras locais (opcionais)
def _instalar_extra(pasta: Path, candidatos: list, peso=1.0, so_genero=True) -> None:
    """Cria um extra falso na pasta de dados de teste, como um usuário faria com um arquivo .py."""
    (pasta / "extras").mkdir(parents=True, exist_ok=True)
    (pasta / "extras" / "fonte_teste.py").write_text(
        f"FONTE = 'FonteTeste'\nPESO = {peso}\nSO_GENERO = {so_genero}\nCANDS = {candidatos!r}\n"
        "def buscar(cli, artista, titulo, pasta=None):\n    import copy\n    return copy.deepcopy(CANDS)\n", encoding="utf-8")


def _cand_extra(titulo, artista, generos: dict, duracao=200.0, ano="2015", album=""):
    return {"fonte": "FonteTeste", "mbid": "", "titulo": titulo, "artista": artista, "artista_mbid": "", "album": album, "tipo": "",
            "ano": ano, "duracao": duracao, "release_id": "", "release_group_id": "", "generos": {}, "generos_extra": generos}


def _sem_internet():
    return Cliente("", None, lambda u, c, t: (404, b"", {}), dormir=lambda s: None)


def test_extras_locais_sao_opcionais_e_um_extra_com_defeito_nao_derruba():
    pasta = _tmp()
    assert extras.carregar_todos(pasta) == []  # sem pasta "extras": só as fontes padrão
    (pasta / "extras").mkdir()
    (pasta / "extras" / "quebrado.py").write_text("isto nao e python (", encoding="utf-8")
    (pasta / "extras" / "sem_contrato.py").write_text("X = 1\n", encoding="utf-8")
    assert extras.carregar_todos(pasta) == []
    _instalar_extra(pasta, [])
    assert [m.FONTE for m in extras.carregar_todos(pasta)] == ["FonteTeste"]
    assert servidor._versao_online({}) != 0


def test_extra_decide_genero_sozinho_mesmo_sem_musicbrainz():
    t = Taxonomia({})
    pasta = _tmp()
    _instalar_extra(pasta, [_cand_extra("Lovestruck", "Mike Hawkins", {"Big Room": 10, "Mainstage": 2}, ano="2015", album="Lovestruck EP")])
    f = Faixa(caminho="/x/Mike Hawkins - Lovestruck.mp3", duracao=200.0)
    online = identificacao.pesquisar_online(f, _sem_internet(), {}, pasta / "capas")
    assert online["cand"]["artista"] == "Mike Hawkins" and "FonteTeste" in online["fontes"], online
    g = identificacao.montar_proposta(f, online, None, t)["campos"]["genero"]
    assert g["novo"] == "Big Room" and g["fonte"] == "FonteTeste" and g["nivel"] == "alta", g  # "Mainstage" vira Big Room
    # sem extra instalado: nada é consultado nem inventado
    online2 = identificacao.pesquisar_online(f, _sem_internet(), {}, _tmp() / "capas")
    assert online2["cand"] is None
    # nomes de gênero de fontes "só gênero" são aceitos mesmo sem parecerem gênero pelas palavras
    assert decisao.votos_online({"FonteTeste": {"Funky Nome Novo": 10}}, t) == {"Funky Nome Novo": 1.0}
    # ajustes antigos recebem o nome padronizado
    from organizador import pipeline
    antigo = Faixa(caminho="/x.mp3", genero="")
    pipeline.finalizar(antigo, t, {"campos": {"genero": {"valor": "Mainstage", "fonte": "FonteTeste"}}})
    assert antigo.genero == "Big Room" and antigo.ajustes["genero"] == "Big Room"


def test_genero_amplo_perde_para_estilo_do_discogs():
    """"Dance / Pop" (amplo) perde para o estilo específico do Discogs (Electro House)."""
    t = Taxonomia({})
    assert t.generico("Dance / Pop")
    v = decisao.votos_online({"FonteTeste": {"Dance / Pop": 10}, "Discogs": {"Electro House": 6, "Electronic": 3}}, t)
    assert v == {"Electro House": 1.0}, v
    assert decisao.votos_online({"FonteTeste": {"Dance / Pop": 10}}, t) == {"Dance / Pop": 1.0}  # sem nada melhor, o amplo vale
    pasta = _tmp()
    _instalar_extra(pasta, [_cand_extra("World On Fire", "Mike Hawkins, 7 Skies", {"Dance / Pop": 10}, duracao=300.0)])
    urls = []

    def transp(url, cab, tmo):
        urls.append(url)
        if "api.discogs.com" in url:
            if "artist=Mike" in url:
                return 200, json.dumps({"results": [{"style": ["Electro House"], "genre": ["Electronic"]}]}).encode(), {}
            return 200, b'{"results": []}', {}
        return 404, b"", {}

    cli = Cliente("", None, transp, dormir=lambda s: None)
    f = Faixa(caminho="/x/Mike Hawkins - World On Fire (Extended Mix).mp3", duracao=300.0)
    online = identificacao.pesquisar_online(f, cli, {"discogs": "TOKEN"}, pasta / "capas")
    assert "Discogs" in online["fontes"], online["fontes"]
    g = identificacao.montar_proposta(f, online, None, t)["campos"]["genero"]
    assert g["novo"] == "Electro House" and g["nivel"] in ("alta", "media"), g
    assert any("artist=Mike" in u and "track=World+On+Fire" in u for u in urls)
    assert servidor._versao_online({"discogs": "x"}) != servidor._versao_online({})  # ligar o Discogs refaz a busca


def test_genero_gravado_plausivel_manda_e_so_lixo_ou_conflito_e_corrigido():
    t = Taxonomia({})
    assert t.suspeito("Spotify") and t.suspeito("2015") and t.suspeito("Youtube Music") and t.suspeito("Unknown")
    assert not t.suspeito("Eurodance") and not t.suspeito("Forró") and not t.suspeito("Electro House") and not t.suspeito("")
    assert t.familia("Big Room") == "eletronica" and t.familia("Rock") == "outra" and t.familia("Vaporwave") is None
    pasta = _tmp()
    _instalar_extra(pasta, [_cand_extra("Lovestruck", "Mike Hawkins", {"Big Room": 10}, ano="")])

    def online_de(f):
        return identificacao.pesquisar_online(f, _sem_internet(), {}, pasta / "capas")

    base = dict(titulo="Lovestruck", artista="Mike Hawkins", album="X", duracao=200.0, tem_capa=True)
    # 1) gênero da tag faz sentido (outro subgênero eletrônico): NÃO muda, nem vira sugestão
    f1 = Faixa(caminho="/a.mp3", genero="Electro House", **base)
    assert identificacao.montar_proposta(f1, online_de(f1), None, t) is None
    # 2) lixo na tag: corrigido sozinho (proposta normal, não é "alteração a conferir")
    f2 = Faixa(caminho="/b.mp3", genero="Spotify", **base)
    g2 = identificacao.montar_proposta(f2, online_de(f2), None, t)["campos"]["genero"]
    assert g2["novo"] == "Big Room" and not g2["alteracao"] and g2["nivel"] == "alta", g2
    # 3) família diferente (Rock numa faixa de Big Room): só sugestão para conferir, nunca automática
    f3 = Faixa(caminho="/c.mp3", genero="Rock", **base)
    g3 = identificacao.montar_proposta(f3, online_de(f3), None, t)["campos"]["genero"]
    assert g3["novo"] == "Big Room" and g3["alteracao"] and g3["nivel"] == "media", g3


def test_capa_so_e_trocada_se_a_da_internet_for_bem_maior():
    tmp = _tmp()
    grande = _jpeg(tmp / "g.jpg", 1200)
    t = Taxonomia({})

    def musica(nome, lado):
        mp3 = tmp / nome
        _mp3(mp3, {"title": "Atmosphere", "artist": "Kaskade", "album": "Atmosphere", "genre": "Electro House"})
        c = tmp / f"c{lado}.jpg"
        _jpeg(c, lado)
        escrita.gravar(mp3, {}, str(c))
        return Faixa(caminho=str(mp3), titulo="Atmosphere", artista="Kaskade", album="Atmosphere", genero="Electro House",
                     ano="2013", duracao=24.5, tem_capa=True)

    chamadas: list = []
    cli = Cliente("", None, _internet_falsa(grande, chamadas), dormir=lambda s: None)
    # capa embutida pequena (300 px) e música completa: só a capa é proposta, o gênero da tag não é tocado
    f = musica("pequena.mp3", 300)
    assert capas.lado_embutido(f.caminho) == 300
    online = identificacao.pesquisar_online(f, cli, {}, tmp / "capas", so_capa=True)
    p = identificacao.montar_proposta(f, online, None, t)
    assert list(p["campos"]) == ["capa"] and p["campos"]["capa"]["nivel"] == "alta" and "300 px" in p["campos"]["capa"]["nota"], p
    # capa embutida já grande (1100 px): não baixa nada de novo
    chamadas.clear()
    f2 = musica("grande.mp3", 1100)
    online2 = identificacao.pesquisar_online(f2, cli, {}, tmp / "capas", so_capa=True)
    assert not online2["capa"] and identificacao.montar_proposta(f2, online2, None, t) is None
    assert not any("coverartarchive" in u for u in chamadas)
    # desligado nas configurações: não procura capa melhor
    chamadas.clear()
    online3 = identificacao.pesquisar_online(f, cli, {"procurar_capa_melhor": False}, tmp / "capas", so_capa=True)
    assert not online3["capa"]


def test_texto_que_nao_e_do_nome_some_comparando_com_a_internet():
    """Sem lista de palavras: o programa percebe, pelo nome encontrado na internet, o que sobra no título."""
    S = casamento.sem_sobras
    assert S("TORA (SITEQUALQUER)", "TORA") == "TORA"
    assert S("TORA [baixado de algumlugar]", "Tora") == "TORA"
    assert S("TORA (Extended Mix) (SITEQUALQUER)", "TORA") == "TORA (Extended Mix)"   # versão fica
    assert S("TORA - SiteQualquer", "TORA") == "TORA" and S("TORA SITEQUALQUER", "TORA") == "TORA"
    assert S("Lose Control (feat. Fulano)", "Lose Control") == "Lose Control (feat. Fulano)"
    assert S("Song (Part 2)", "Song") == "Song (Part 2)" and S("Song (Love)", "Song (Love)") == "Song (Love)"
    assert S("Outra Coisa (SITEQUALQUER)", "TORA") == "Outra Coisa (SITEQUALQUER)"      # não bate: não mexe
    t = Taxonomia({})
    pedidos = []

    def transp(url, cab, tmo):
        pedidos.append(urllib.parse.unquote_plus(url))
        if "musicbrainz.org" in url and "/recording" in url:
            if "SITEQUALQUER" in pedidos[-1]:
                return 200, b'{"recordings": []}', {}   # com o texto extra a busca não acha nada
            rec = {"id": "r1", "title": "TORA", "length": 200000, "artist-credit": [{"name": "Kura", "artist": {"id": "a1", "name": "Kura"}}],
                   "releases": [{"id": "l1", "title": "TORA", "status": "Official", "date": "2015-01-01", "release-group": {"id": "g1", "primary-type": "Single"}}]}
            return 200, json.dumps({"recordings": [rec]}).encode(), {}
        return 404, b"", {}

    f = Faixa(caminho="/x/qualquer.mp3", titulo="TORA (SITEQUALQUER)", artista="Kura", album="TORA (SITEQUALQUER)", genero="Big Room",
              duracao=200.0, tem_capa=True)
    online = identificacao.pesquisar_online(f, Cliente("", None, transp, dormir=lambda s: None), {}, _tmp() / "capas")
    assert online["nota"]["nivel"] == "alta", online["nota"]
    campos = identificacao.montar_proposta(f, online, None, t)["campos"]
    assert campos["titulo"]["novo"] == "TORA" and not campos["titulo"]["alteracao"] and campos["titulo"]["nivel"] == "alta"
    assert campos["album"]["novo"] == "TORA" and "genero" not in campos
    # gênero antigo guardado com outro nome é padronizado sempre que os ajustes são reaplicados
    from organizador import ajustes
    ajustes.normalizar_genero = t.normalizar
    g = Faixa(caminho="/y.mp3")
    ajustes.aplicar_em_faixa(g, {"campos": {"genero": {"valor": "Mainstage"}}})
    assert g.genero == "Big Room" and g.ajustes["genero"] == "Big Room"


def test_discogs_identifica_quando_o_musicbrainz_nao_acha():
    t = Taxonomia({})

    def transp(url, cab, tmo):
        if "api.discogs.com" in url and "artist=Kura" in url and "track=TORA" in url:
            return 200, json.dumps({"results": [{"title": "Kura - TORA", "year": "2015", "style": ["Big Room"], "genre": ["Electronic"]}]}).encode(), {}
        if "musicbrainz.org" in url:
            return 200, b'{"recordings": []}', {}
        return 404, b"", {}

    f = Faixa(caminho="/x/Kura - TORA (SITEQUALQUER).mp3", duracao=200.0)
    online = identificacao.pesquisar_online(f, Cliente("", None, transp, dormir=lambda s: None), {"discogs": "TOKEN"}, _tmp() / "capas")
    assert online["fontes"] == ["Discogs"] and online["nota"]["nivel"] == "media", online
    campos = identificacao.montar_proposta(f, online, None, t)["campos"]
    assert campos["genero"]["novo"] == "Big Room" and campos["genero"]["fonte"] == "Discogs" and campos["genero"]["nivel"] == "media", campos["genero"]
    assert campos["titulo"]["novo"] == "TORA" and campos["artista"]["novo"] == "Kura" and campos["ano"]["novo"] == "2015"
    # sem token, nada disso acontece
    assert identificacao.pesquisar_online(f, Cliente("", None, transp, dormir=lambda s: None), {}, _tmp() / "capas")["cand"] is None


def _esperar(E, limite=120):
    ini = time.time()
    while time.time() - ini < limite:
        with E.lock:
            if E.job["fase"] != "rodando":
                return dict(E.job)
        time.sleep(0.1)
    raise TimeoutError("tarefa não terminou")


def test_integracao_identificar_revisar_gravar_e_originais_intactos():
    tmp = _tmp()
    origem, cfg = tmp / "cartao", tmp / "cfg"
    origem.mkdir()
    cfg.mkdir()
    (cfg / "user_preferences.json").write_text(json.dumps(PREFS_TESTE), encoding="utf-8")
    # biblioteca: 6 músicas de cada estilo com gênero na tag (para a sonoridade aprender) + 3 sem gênero
    for i in range(6):
        _faixa_som(origem / f"a{i}.mp3", "a", i, {"title": f"A{i}", "artist": f"Art A{i}", "album": "X", "genre": "Alfa"})
        _faixa_som(origem / f"b{i}.mp3", "b", i, {"title": f"B{i}", "artist": f"Art B{i}", "album": "X", "genre": "Sub Z"})
    _faixa_som(origem / "mesmo_artista_1.mp3", "a", 20, {"title": "U1", "artist": "Art A0", "album": "X"})
    _faixa_som(origem / "mesmo_artista_2.mp3", "b", 21, {"title": "U2", "artist": "Art A0", "album": "X"})
    _faixa_som(origem / "Kaskade - Atmosphere.mp3", "a", 22, {})  # sem NENHUMA tag: só o nome do arquivo
    antes = {p.name: p.read_bytes() for p in origem.glob("*.mp3")}
    capa = _jpeg(tmp / "capa.jpg")

    config.salvar_credenciais({"contato": "teste@exemplo.com"}, cfg)
    srv = servidor.criar_servidor(0, tmp / "c.db", cfg)
    E = servidor.E
    chamadas: list = []
    servidor.Cliente = lambda contato, cache: Cliente(contato, cache, _internet_falsa(capa, chamadas), dormir=lambda s: None)

    # só analisar: a busca na internet roda sozinha em seguida, sem e-mail, chave nem clique extra
    servidor.r_analisar({"origem": str(origem)})
    job = _esperar(E)
    assert job["fase"] == "concluido", job
    assert "ident_aviso" not in job["resultado"], job["resultado"]
    res = job["resultado"]["ident"]
    assert res["autoteste"]["acuracia"] >= 0.9, res
    por = {Path(f.caminho).name: f for f in E.faixas}
    assert len(por) == 15 and all(f.vetor for f in E.faixas)
    assert por["a0.mp3"].genero == "Alfa" and por["b0.mp3"].genero == "Sub Z"

    # 1) música só com nome de arquivo: nome, artista, álbum, ano, gênero e capa vieram da internet (alta confiança, auto)
    k = por["Kaskade - Atmosphere.mp3"]
    assert (k.titulo, k.artista, k.album, k.ano) == ("Atmosphere", "Kaskade", "Atmosphere", "2013"), k
    assert "capa_arquivo" in k.ajustes
    # 2) gênero por música, não por artista: mesmo artista, sons diferentes -> gêneros diferentes, já aplicados (média confiança)
    assert (por["mesmo_artista_1.mp3"].genero, por["mesmo_artista_2.mp3"].genero) == ("Alfa", "Sub Z")
    assert por["mesmo_artista_1.mp3"].ajustes and por["mesmo_artista_2.mp3"].ajustes
    # 3) músicas já completas não foram tocadas
    assert por["a0.mp3"].ajustes == {} and por["a0.mp3"].genero == "Alfa"
    # 4) nada de baixa confiança foi aplicado sozinho
    props = servidor.r_propostas({})["propostas"]
    assert all(v["nivel"] == "baixa" for p in props for v in p["campos"].values())
    antes_req = len(chamadas)
    try:
        servidor.r_decidir({"acao": "aceitar", "nivel": "baixa"})
        assert False
    except servidor.Erro:
        pass
    _esperar(E)

    # identificar de novo não repete pesquisas já feitas (cache) e não repropõe o que já foi aceito
    try:
        servidor.r_identificar({})
        _esperar(E)
    except servidor.Erro:
        pass
    assert len(chamadas) == antes_req

    # copiar: organiza e grava os metadados só nas cópias
    destino = tmp / "saida"
    servidor.r_copiar({"destino": str(destino), "padrao": "D", "incluir_incertas": True})
    assert _esperar(E)["fase"] == "concluido"
    copia = next(destino.rglob("Kaskade - Atmosphere.mp3"))
    tags, tem_capa = escrita._ler(copia)
    assert tags["title"] == "Atmosphere" and tags["artist"] == "Kaskade" and tags["album"] == "Atmosphere" and tem_capa
    assert (copia.parent.parent.name) in {"Electro House", "Beta"} or "Electro" in str(copia)
    log = json.loads(next((destino / ".organizador").glob("log-*.json")).read_text(encoding="utf-8"))
    assert any("tags_anteriores" in r for r in log)
    # originais intactos, byte a byte
    assert {p.name: p.read_bytes() for p in origem.glob("*.mp3")} == antes

    # desfazer volta ao que era
    servidor.r_desfazer({"caminhos": [k.caminho]})
    assert not [f for f in E.faixas if f.caminho == k.caminho][0].ajustes
    srv.server_close()


def test_sem_internet_pausa_clara_e_nada_se_perde():
    tmp = _tmp()
    origem, cfg = tmp / "m", tmp / "cfg"
    origem.mkdir()
    cfg.mkdir()
    for i in range(7):
        _faixa_som(origem / f"Artista {i} - Musica {i}.mp3", "a", i, {}, segundos=14)
    config.salvar_credenciais({"contato": "t@e.com"}, cfg)
    srv = servidor.criar_servidor(0, tmp / "c.db", cfg)
    E = servidor.E
    servidor.Cliente = lambda contato, cache: Cliente(contato, cache, lambda u, c, t: (_ for _ in ()).throw(OSError("sem rede")), dormir=lambda s: None)
    servidor.r_analisar({"origem": str(origem)})
    job0 = _esperar(E)
    # sem internet na análise: não quebra, avisa e segue só com a sonoridade
    assert job0["fase"] == "concluido" and "ident_aviso" in job0["resultado"], job0
    servidor.r_identificar({})
    job = _esperar(E)
    assert job["fase"] == "erro" and "conexão" in job["erro"]
    assert len(E.faixas) == 7
    srv.server_close()


def test_identificar_nao_pede_email():
    """O usuário não precisa informar e-mail nem chave: o app se identifica sozinho no MusicBrainz."""
    from organizador.rede import CONTATO_PADRAO
    tmp = _tmp()
    srv = servidor.criar_servidor(0, tmp / "c.db", tmp)
    assert CONTATO_PADRAO in Cliente("", None).agente and "sem-contato" not in Cliente("", None).agente
    servidor.E.faixas = [Faixa(caminho="/x.mp3")]
    servidor.Cliente = lambda contato, cache: Cliente(contato, cache, lambda u, c, t: (200, b"{}", {}), dormir=lambda s: None)
    try:
        servidor.r_identificar({})
    except servidor.Erro as e:
        assert "e-mail" not in str(e)
    _esperar(servidor.E)
    srv.server_close()


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok   ", nome)
            except Exception as e:  # noqa: BLE001
                import traceback
                falhas += 1
                print("FALHA", nome, "->", repr(e))
                traceback.print_exc()
    sys.exit(1 if falhas else 0)
