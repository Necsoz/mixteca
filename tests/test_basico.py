"""Testes automáticos. Rodar: python tests/test_basico.py   (ou: python -m pytest tests)"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from organizador import planejador  # noqa: E402
from organizador.analise import analisar_arquivo  # noqa: E402
from organizador.camelot import camelot, compativeis  # noqa: E402
from organizador.generos import faixa_bpm, limpar_genero  # noqa: E402
from organizador.modelos import Faixa  # noqa: E402


def test_camelot_conhecidos():
    assert camelot(9, True) == "8A"    # A menor
    assert camelot(0, False) == "8B"   # C maior
    assert camelot(11, True) == "10A"  # B menor
    assert camelot(1, True) == "12A"   # C# menor
    assert camelot(11, False) == "1B"  # B maior
    assert camelot(8, True) == "1A"    # G# menor
    assert camelot(7, False) == "9B"   # G maior
    assert camelot(2, False) == "10B"  # D maior


def test_compatibilidade():
    assert set(compativeis("8A")) == {"8A", "7A", "9A", "8B"}
    assert set(compativeis("1A")) == {"1A", "12A", "2A", "1B"}  # dá a volta na roda
    assert set(compativeis("12B")) == {"12B", "11B", "1B", "12A"}


def test_generos():
    assert limpar_genero("big room; edm") == "Big Room"
    assert limpar_genero("EDM") == "EDM"
    assert limpar_genero("") == ""
    assert faixa_bpm("Melodic Dubstep") == (138, 150)
    assert faixa_bpm("Bass House") == (124, 132)


def _faixa(nome, genero="Big Room", bpm=128.0, cam="8A", conf=9.0, tom_conf=0.1):
    return Faixa(caminho=f"/x/{nome}", genero=genero, bpm=bpm, bpm_conf=conf, camelot=cam, tom_conf=tom_conf)


def test_camelot_em_ordem_harmonica_e_nomes_profissionais():
    from organizador import limpeza
    limpeza.definir_termos(["baixafacil"])  # nome de site vem das preferências locais, não do código
    ordem = sorted(planejador.rotulo_camelot(c) for c in ["10A", "1B", "2A", "1A", "12B", "9A", "10B", "2B"])
    assert ordem == ["01A", "01B", "02A", "02B", "09A", "10A", "10B", "12B"]  # número, depois A/B, em qualquer ordenação
    f = Faixa(caminho="/x/Kura - TORA (BAIXAFACIL).mp3", titulo="TORA", artista="Kura", album="TORA", genero="Big Room",
              bpm=128, bpm_conf=9, camelot="8A", tom_conf=.1, ano="2015")
    item = planejador.planejar([f], "A")[0]
    assert item.destino == "Big Room/128 BPM/08A/Kura - TORA.mp3", item.destino
    assert item.tags == {"titulo": "TORA", "artista": "Kura", "album": "TORA", "genero": "Big Room", "ano": "2015", "bpm": 128, "camelot": "8A"}
    sem_tag = Faixa(caminho="/x/01_Mike_Hawkins_-_Lovestruck_[baixafacil.com].mp3", genero="Big Room", bpm=128, bpm_conf=9, camelot="8A", tom_conf=.1)
    assert planejador.planejar([sem_tag], "D")[0].destino == "Big Room/128 BPM/Mike Hawkins - Lovestruck.mp3"


def test_agrupar_generos_proximos_na_pasta_sem_mudar_a_tag():
    from organizador.taxonomia import grupo
    casos = {"Riddim": "Dubstep", "Melodic Dubstep": "Dubstep", "Brostep": "Dubstep", "Tech House": "House", "Electro House": "House",
             "Progressive House": "House", "Big Room": "Big Room", "Psytrance": "Trance", "Melodic Techno": "Techno",
             "Liquid Drum & Bass": "Drum & Bass", "Hardstyle": "Hardstyle & Hardcore", "Future Bass": "Trap & Future Bass",
             "Indie Rock": "Rock", "Hardcore Punk": "Rock", "Heavy Metal": "Metal", "Synthpop": "Pop", "Sertanejo Universitário": "Sertanejo & Brasil",
             "Hip-Hop": "Hip-Hop & R&B", "Gênero Inventado": "Gênero Inventado"}
    for g, esperado in casos.items():
        assert grupo(g) == esperado, (g, grupo(g))
    f = Faixa(caminho="/x/a.mp3", titulo="A", artista="B", genero="Riddim", bpm=140, bpm_conf=9, camelot="6A", tom_conf=.1)
    assert planejador.planejar([f], "A")[0].destino.startswith("Riddim/")
    item = planejador.planejar([f], "A", agrupar_generos=True)[0]
    assert item.destino == "Dubstep/140 BPM/06A/B - A.mp3" and item.tags["genero"] == "Riddim"
    # grupos escolhidos pelo usuário valem antes dos padrões; Deathstep e Tearout não entram em Dubstep
    from organizador.taxonomia import ler_grupos
    meus = ler_grupos("Electro & Progressive: Electro House, Progressive House\nlinha sem dois pontos\nBass = Riddim; Trap")
    assert grupo("Electro House", meus) == "Electro & Progressive" and grupo("progressive house", meus) == "Electro & Progressive"
    assert grupo("Tech House", meus) == "House" and grupo("Riddim", meus) == "Bass" and grupo("Trap", meus) == "Bass"
    assert grupo("Deathstep") == "Deathstep" and grupo("Tearout") == "Tearout" and grupo("Brostep") == "Dubstep"
    assert planejador.planejar([f], "D", agrupar_generos=True, grupos_proprios=meus)[0].destino.startswith("Bass/")
    # mover pela tela: tira Electro House e Progressive House de House e junta com Big Room, ou cria pasta nova
    from organizador.taxonomia import mover_grupo
    txt = mover_grupo(mover_grupo("", "Electro House", "Big Room"), "Progressive House", "Big Room")
    m = ler_grupos(txt)
    assert grupo("Electro House", m) == "Big Room" and grupo("Progressive House", m) == "Big Room" and grupo("Tech House", m) == "House"
    txt = mover_grupo(mover_grupo(txt, "Electro House", "Electro & Prog"), "Progressive House", "electro & prog")
    m = ler_grupos(txt)
    assert grupo("Electro House", m) == grupo("Progressive House", m) == "Electro & Prog" and txt.count("\n") == 0, txt
    assert mover_grupo(mover_grupo(txt, "Electro House", ""), "Progressive House", "House") == ""   # voltar ao padrão limpa tudo
    # renomear pastas: uma criada pelo usuário e uma padrão; renomear de novo e voltar ao nome original
    from organizador.taxonomia import RENOMEAR, renomear_pasta
    m = ler_grupos(mover_grupo("", "Indie Rock", "Alternative/Indie"))
    ren = renomear_pasta({}, "Alternative/Indie", "Alternative/Indie/Pop")
    ren = renomear_pasta(ren, "House", "Casa")
    m[RENOMEAR] = ren
    assert grupo("Indie Rock", m) == "Alternative/Indie/Pop" and grupo("Tech House", m) == "Casa" and grupo("Riddim", m) == "Dubstep"
    m[RENOMEAR] = renomear_pasta(ren, "Casa", "House Music")
    assert grupo("Deep House", m) == "House Music"
    m[RENOMEAR] = renomear_pasta(m[RENOMEAR], "House Music", "House")
    assert grupo("Deep House", m) == "House" and "house" not in m[RENOMEAR]
    fr = Faixa(caminho="/x/i.mp3", titulo="T", artista="A", genero="Indie Rock", bpm=120, bpm_conf=9, camelot="8A", tom_conf=.1)
    assert planejador.planejar([fr], "D", agrupar_generos=True, grupos_proprios=m)[0].destino.startswith("Alternative - Indie - Pop/")


def test_melhoria_aguenta_medicao_fora_da_faixa():
    from organizador import melhoria
    bom = {"input_i": "-8.5", "input_tp": "0.4", "input_lra": "5.1", "input_thresh": "-18.6", "target_offset": "0.3"}
    assert melhoria._medidas_validas(bom)
    for chave, valor in [("input_i", "0.62"), ("input_i", "-inf"), ("input_thresh", "inf"), ("input_lra", "nan"), ("target_offset", None)]:
        assert not melhoria._medidas_validas({**bom, chave: valor}), (chave, valor)
    assert melhoria._numero({"input_i": "-inf"}, "input_i", -99.0) == -99.0
    # arquivo real altíssimo (onda quadrada no talo): a medição passa de 0 LUFS e a cópia sai mesmo assim
    import subprocess, tempfile
    tmp = Path(tempfile.mkdtemp())
    alto = tmp / "alto.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "aevalsrc=exprs='4*sgn(sin(2*PI*1000*t))':d=6:s=44100", "-c:a", "pcm_f32le", str(alto)], check=True)
    r = melhoria.melhorar(alto, tmp / "saida" / "alto.wav")
    assert r["status"] == "melhorado" and Path(r["destino"]).stat().st_size > 1000, r


def test_bpm_automatico_junta_vizinhos_com_poucas_musicas():
    g = planejador.agrupar_bpms({124: 1, 125: 1, 126: 2, 128: 40, 129: 1, 130: 2, 140: 1, 150: 9, 151: 1})
    assert g[124] == g[125] == g[126] == "124-126 BPM"      # poucas músicas e vizinhos: uma pasta só
    assert g[128] == "128 BPM"                                # já tem bastante: fica sozinho
    assert g[129] == g[130] == "129-130 BPM"
    assert g[140] == "140 BPM"                                # longe de todo mundo: não é forçado a juntar
    assert g[150] == g[151] == "150-151 BPM"                  # a música sozinha no 151 entra no vizinho
    assert planejador.agrupar_bpms({100: 3, 101: 3, 103: 1}) == {100: "100 BPM", 101: "101-103 BPM", 103: "101-103 BPM"}
    assert all(int(r.split()[0].split("-")[-1]) - int(r.split()[0].split("-")[0]) <= 5 for r in g.values())
    f = [_faixa(f"a{i}.mp3", bpm=b) for i, b in enumerate([126, 127, 128, 128])] + [_faixa("d.mp3", genero="Dubstep", bpm=127, cam="6A")]
    plano = {i.origem: i.destino for i in planejador.planejar(f, "A", bpm_modo="auto")}
    assert plano["/x/a0.mp3"].startswith("Big Room/126-128 BPM/08A/") and plano["/x/a3.mp3"].startswith("Big Room/126-128 BPM/")
    assert plano["/x/d.mp3"].startswith("Dubstep/127 BPM/06A/")   # cada gênero junta os seus, sem misturar
    assert {i.origem: i.destino for i in planejador.planejar(f, "A")}["/x/a0.mp3"].startswith("Big Room/126 BPM/")


def test_reaproveitar_pasta_de_melhoradas_antiga_sem_refazer():
    tmp = Path(tempfile.mkdtemp())
    origem, saida = tmp / "o", tmp / "Melhoradas"
    origem.mkdir()
    for n in ("a", "b", "c", "nova"):
        (origem / f"{n}.mp3").write_bytes(n.encode() * 50)
    # pasta feita por uma versão antiga: BPM exato, sem índice; "c" tinha dado erro e "nova" não existia
    for rel in ("Big Room/126 BPM/08A/Art - A.mp3", "Big Room/127 BPM/08A/Art - B.mp3"):
        (saida / rel).parent.mkdir(parents=True, exist_ok=True)
        (saida / rel).write_bytes(b"melhorada " + rel.encode())
    pedidos = [(str(origem / "a.mp3"), "Big Room/126-127 BPM/08A/Art - A.mp3"), (str(origem / "b.mp3"), "Big Room/126-127 BPM/08A/Art - B.mp3"),
               (str(origem / "c.mp3"), "Big Room/126-127 BPM/08A/Art - C.mp3"), (str(origem / "nova.mp3"), "Dubstep/140 BPM/06A/Art - Nova.mp3")]
    fazer, cont, indice = planejador.reaproveitar(saida, pedidos, -10.0)
    assert fazer == [2, 3] and cont["movidos"] == 2                      # só as duas que faltam precisam ser processadas
    assert (saida / "Big Room/126-127 BPM/08A/Art - A.mp3").read_bytes().startswith(b"melhorada")
    assert not (saida / "Big Room/126 BPM").exists()                     # pasta antiga vazia some
    planejador.salvar_indice(saida, indice)
    fazer2, cont2, _ = planejador.reaproveitar(saida, pedidos[:2], -10.0)
    assert fazer2 == [] and cont2["no_lugar"] == 2                       # rodar de novo: nada a fazer
    (origem / "a.mp3").write_bytes(b"arquivo baixado de novo, diferente")  # original trocado: essa é refeita
    assert planejador.reaproveitar(saida, pedidos[:2], -10.0)[0] == [0]
    assert planejador.reaproveitar(saida, pedidos[:2], -10.0, refazer=True)[0] == [0, 1]
    # pasta antiga + opção nova de tom no nome do arquivo: ainda acha pelo nome antigo, move e renomeia
    velha = tmp / "M2"
    (velha / "Rock/100 BPM/01A").mkdir(parents=True)
    (velha / "Rock/100 BPM/01A/Art - Z.mp3").write_bytes(b"melhorada z")
    fz, cz, _ = planejador.reaproveitar(velha, [(str(origem / "b.mp3"), "Rock/100 BPM/01A - Art - Z.mp3", ["Art - Z.mp3"])], -10.0)
    assert fz == [] and cz["movidos"] == 1 and (velha / "Rock/100 BPM/01A - Art - Z.mp3").read_bytes() == b"melhorada z"


def test_ordem_de_pastas_montada_pelo_usuario():
    f = Faixa(caminho="/x/a.mp3", titulo="T", artista="Kura/Outro", genero="Big Room", ano="2015-03-01", bpm=128, bpm_conf=9, camelot="8A", tom_conf=.1)
    d = lambda o: planejador.planejar([f], "A", ordem=o)[0].destino  # noqa: E731
    assert d(["camelot", "bpm", "genero"]) == "08A/128 BPM/Big Room/Kura, Outro - T.mp3"
    assert d(["bpm", "camelot", "genero"]) == "128 BPM/08A/Big Room/Kura, Outro - T.mp3"
    assert d(["genero"]) == "Big Room/Kura, Outro - T.mp3"
    assert d(["artista", "ano", "genero"]) == "Kura/2015/Big Room/Kura, Outro - T.mp3"
    assert d(["genero", "inventado"]) == d(None) == "Big Room/128 BPM/08A/Kura, Outro - T.mp3"     # ordem inválida: usa o modelo
    assert planejador.validar_ordem(["bpm", "bpm"]) is None and planejador.validar_ordem([]) is None
    # tom no nome do arquivo em vez de subpasta: ordena em sequência harmônica dentro da pasta
    assert planejador.planejar([f], "A", ordem=["genero", "bpm"], tom_no_nome=True)[0].destino == "Big Room/128 BPM/08A - Kura, Outro - T.mp3"
    nomes = sorted(planejador.planejar([Faixa(caminho=f"/x/{c}.mp3", titulo="T", artista=c, genero="G", bpm=128, bpm_conf=9, camelot=c, tom_conf=.1)
                                        for c in ("10B", "2A", "1B", "1A")], "A", ordem=["genero"], tom_no_nome=True), key=lambda i: i.destino)
    assert [Path(i.destino).name[:3] for i in nomes] == ["01A", "01B", "02A", "10B"]
    sem = Faixa(caminho="/x/b.mp3", titulo="T2", genero="Big Room", bpm=128, bpm_conf=9, camelot="8A", tom_conf=.1)
    assert planejador.planejar([sem], "A", ordem=["artista", "ano"])[0].destino == "Sem artista/Sem ano/b.mp3"
    # só o que está na ordem pode mandar para a Revisão: sem tom detectado não importa se o tom não é pasta
    sem.camelot = None
    assert not planejador.planejar([sem], "A", ordem=["genero", "bpm"])[0].revisao


def test_planejador_padroes():
    f = [_faixa("a.mp3"), _faixa("b.mp3", genero="Dubstep", bpm=140, cam="6A")]
    caminhos = {i.origem: i.destino for i in planejador.planejar(f, "A")}
    assert caminhos["/x/a.mp3"] == "Big Room/128 BPM/08A/a.mp3"
    assert {i.origem: i.destino for i in planejador.planejar(f, "B")}["/x/b.mp3"] == "140 BPM/Dubstep/06A/b.mp3"
    assert {i.origem: i.destino for i in planejador.planejar(f, "C")}["/x/a.mp3"] == "Big Room/08A/128 BPM/a.mp3"
    assert {i.origem: i.destino for i in planejador.planejar(f, "D")}["/x/a.mp3"] == "Big Room/128 BPM/a.mp3"


def test_planejador_faixas_de_bpm_e_revisao():
    f = [_faixa("a.mp3", bpm=127.0), _faixa("b.mp3", genero=""), _faixa("c.mp3", conf=1.0), _faixa("d.mp3", cam=None)]
    plano = {i.origem: i for i in planejador.planejar(f, "A", bpm_modo="faixas", bpm_tam=5)}
    assert plano["/x/a.mp3"].destino == "Big Room/125-129 BPM/08A/a.mp3"
    assert plano["/x/b.mp3"].destino.startswith("Revisão/Sem gênero/")
    assert plano["/x/c.mp3"].destino.startswith("Revisão/BPM incerto/")
    assert plano["/x/d.mp3"].destino.startswith("Revisão/Tom não detectado/")
    forcado = {i.origem: i for i in planejador.planejar(f, "A", incluir_incertas=True)}
    assert forcado["/x/c.mp3"].destino.startswith("Big Room/")


def test_nomes_repetidos_e_invalidos():
    f = [Faixa(caminho="/a/x.mp3", genero="Rock", bpm=100, bpm_conf=9, camelot="1A", tom_conf=.1),
         Faixa(caminho="/b/x.mp3", genero="Rock", bpm=100, bpm_conf=9, camelot="1A", tom_conf=.1),
         Faixa(caminho="/c/y.mp3", genero="R&B/Soul: x", bpm=90, bpm_conf=9, camelot="1A", tom_conf=.1)]
    destinos = [i.destino for i in planejador.planejar(f, "A")]
    assert "Rock/100 BPM/01A/x.mp3" in destinos and "Rock/100 BPM/01A/x (2).mp3" in destinos
    assert all(":" not in d and "?" not in d for d in destinos)


def test_copia_segura():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "o").mkdir()
    (tmp / "o" / "a.mp3").write_bytes(b"A" * 100)
    f = [_faixa(str(tmp / "o" / "a.mp3")).__class__(caminho=str(tmp / "o" / "a.mp3"), genero="Rock", bpm=100,
                                                      bpm_conf=9, camelot="1A", tom_conf=.1)]
    plano = planejador.planejar(f, "A")
    r1 = planejador.executar(plano, tmp / "d")
    assert r1["copiados"] == 1 and (tmp / "o" / "a.mp3").exists()
    r2 = planejador.executar(plano, tmp / "d")  # de novo: não duplica
    assert r2["copiados"] == 0 and r2["ignorados"] == 1
    alvo = tmp / "d" / plano[0].destino
    alvo.write_bytes(b"outro conteudo maior")  # arquivo diferente no destino: nunca sobrescreve
    r3 = planejador.executar(plano, tmp / "d")
    assert alvo.read_bytes() == b"outro conteudo maior" and r3["erros"] == 0
    # destino que o programa nunca viu (sem registros) e com um arquivo diferente no caminho: copia ao lado, sem sobrescrever
    outro = tmp / "d2" / plano[0].destino
    outro.parent.mkdir(parents=True)
    outro.write_bytes(b"arquivo de outra origem")
    r4 = planejador.executar(plano, tmp / "d2")
    assert r4["copiados"] == 1 and outro.read_bytes() == b"arquivo de outra origem" and len(list(outro.parent.iterdir())) == 2
    assert Path(r3["log"]).exists()


def _wav_sintetico(caminho, bpm=128, segundos=60, sr=44100):
    t = np.arange(int(sr * segundos)) / sr
    x = np.zeros_like(t)
    passo = 60.0 / bpm
    for k in range(int(segundos / passo)):  # bumbo em todo tempo + chimbal a cada contratempo
        i = int(k * passo * sr)
        n = int(0.18 * sr)
        tt = np.arange(n) / sr
        x[i:i + n] += (np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 18))[: len(x[i:i + n])]
        j = int((k + 0.5) * passo * sr)
        m = int(0.03 * sr)
        x[j:j + m] += 0.15 * np.random.default_rng(k).standard_normal(len(x[j:j + m]))[: len(x[j:j + m])] * np.exp(-np.arange(len(x[j:j + m])) / (0.008 * sr))
    for fr in (220.0, 261.63, 329.63):  # acorde de Lá menor (A C E)
        x += 0.12 * np.sin(2 * np.pi * fr * t)
    x = x / np.abs(x).max() * 0.8
    wavfile.write(str(caminho), sr, (x * 32767).astype(np.int16))


def test_analise_bpm_e_tom_sinteticos():
    tmp = Path(tempfile.mkdtemp())
    for bpm in (100, 128, 140):
        p = tmp / f"s{bpm}.wav"
        _wav_sintetico(p, bpm)
        f = analisar_arquivo(p)
        assert f.erro is None, f.erro
        assert abs(f.bpm - bpm) <= 1.0, (bpm, f.bpm)
        assert f.camelot in ("8A", "8B"), f.camelot  # Lá menor ou o relativo Dó maior
        assert f.bpm_conf > 3


def test_arquivo_invalido_nao_quebra():
    tmp = Path(tempfile.mkdtemp())
    p = tmp / "lixo.mp3"
    p.write_bytes(b"isto nao e um mp3")
    f = analisar_arquivo(p)
    assert f.erro


def test_artista_principal():
    from organizador.generos import artista_principal
    assert artista_principal("Tony Junior/Kura/Jimmy Clash") == "Tony Junior"
    assert artista_principal("AC/DC ") == "AC/DC"
    assert artista_principal("4B & Junkie Kid") == "4B"
    assert artista_principal("Bassjackers & Joe Ghost ft. MOTi") == "Bassjackers"
    assert artista_principal("") == ""


def test_cache_de_generos_por_artista():
    from organizador.store import Cache
    c = Cache(Path(tempfile.mkdtemp()) / "c.db")
    assert c.generos_artista() == {}
    c.definir_genero_artista("kura", "Big Room")
    assert c.generos_artista() == {"kura": "Big Room"}
    c.definir_genero_artista("kura", "")  # vazio remove
    assert c.generos_artista() == {}


def test_genero_escolhido_entra_na_analise_e_bpm_e_inteiro():
    p = Path(tempfile.mkdtemp()) / "sem_tag.wav"
    _wav_sintetico(p, 140)
    f = analisar_arquivo(p, {"": "Dubstep"})  # arquivo sem artista -> chave ""
    assert f.erro is None and f.genero == "Dubstep" and f.genero_manual is True
    assert isinstance(f.bpm, int) and f.bpm == 140



if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print("ok   ", nome)
            except Exception as e:  # noqa: BLE001
                falhas += 1
                print("FALHA", nome, "->", repr(e))
    sys.exit(1 if falhas else 0)
