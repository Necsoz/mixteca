"""Navegador + internet SIMULADA: analisar -> identificar -> conferir -> aceitar -> copiar com tags. Uso: python tests/e2e_identificacao_ui.py PASTA_PRINTS"""
import os
import sys
import threading
from pathlib import Path

os.environ.setdefault("MIXTECA_IDIOMA", "pt")  # os testes conferem os textos em português
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from playwright.sync_api import sync_playwright  # noqa: E402

import test_identificacao as T  # noqa: E402
from organizador import config, servidor  # noqa: E402
from organizador.rede import Cliente  # noqa: E402

prints = Path(sys.argv[1]); prints.mkdir(parents=True, exist_ok=True)
tmp = T._tmp(); origem, cfg, destino = tmp / "cartao", tmp / "cfg", tmp / "out"
origem.mkdir(); cfg.mkdir()
for i in range(6):
    T._faixa_som(origem / f"a{i}.mp3", "a", i, {"title": f"A{i}", "artist": f"Art A{i}", "album": "X", "genre": "Alfa"})
    T._faixa_som(origem / f"b{i}.mp3", "b", i, {"title": f"B{i}", "artist": f"Art B{i}", "album": "X", "genre": "Sub Z"})
T._faixa_som(origem / "mesmo_artista_1.mp3", "a", 20, {"title": "U1", "artist": "Art A0", "album": "X"})
T._faixa_som(origem / "Kaskade - Atmosphere.mp3", "a", 22, {})
capa = T._jpeg(tmp / "capa.jpg")
servidor.Cliente = lambda contato, cache: Cliente(contato, cache, T._internet_falsa(capa, []), dormir=lambda s: None)
srv = servidor.criar_servidor(0, tmp / "c.db", cfg)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/"
erros = []
with sync_playwright() as pw:
    nav = pw.chromium.launch(); pg = nav.new_page(viewport={"width": 1180, "height": 900})
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: erros.append(str(e))); pg.on("dialog", lambda d: d.accept())
    pg.goto(url); pg.screenshot(path=str(prints / "passo-1.png")); pg.fill("#origem", str(origem)); pg.fill("#destino", str(destino)); pg.click("#b-analisar")
    # só analisar: a busca na internet acontece sozinha, sem pedir e-mail, chave nem clique
    pg.wait_for_selector("#res-id", state="visible", timeout=180000); pg.wait_for_timeout(1500)
    print("e-mail pedido?", "obrigatório" in pg.inner_text("#si"))
    print("resultado:", pg.inner_text("#res-id").replace("\n", " "))
    pg.locator("#si").screenshot(path=str(prints / "id-1-revisao.png"))
    print("propostas restantes:", pg.locator(".prop").count())
    pg.locator("#corpo button.ed").first.click(); pg.locator("#corpo td.tg input").fill("Tech House"); pg.keyboard.press("Enter"); pg.wait_for_timeout(1500)
    print("gênero trocado na mão:", pg.locator("#corpo tr.m").first.inner_text().replace("\n", " ").replace("\t", " | ")[:120])
    pg.screenshot(path=str(prints / "passo-2.png"))
    pg.click('#passos button[data-p="3"]'); pg.wait_for_selector("#niveis-on .nivel")
    ordem = lambda: [b.get_attribute("data-k") for b in pg.locator("#niveis-on .nivel").all()]  # noqa: E731
    print("ordem inicial:", ordem())
    pg.locator('#niveis-on .nivel[data-k="camelot"]').drag_to(pg.locator('#niveis-on .nivel[data-k="genero"]'), target_position={"x": 3, "y": 10}); pg.wait_for_timeout(1200)
    print("depois de arrastar o tom para o começo:", ordem())
    pg.locator('#niveis-off .nivel[data-k="artista"]').click(); pg.wait_for_timeout(1000)
    print("depois de clicar em Artista:", ordem(), "| prévia:", pg.inner_text("#tree").replace("\n", " | ")[:90])
    pg.locator("#s2").screenshot(path=str(prints / "ordem-pastas.png"))
    pg.locator('#niveis-on .nivel[data-k="artista"]').click(); pg.wait_for_timeout(800)
    pg.locator('#niveis-on .nivel[data-k="camelot"]').drag_to(pg.locator("#niveis-off")); pg.wait_for_timeout(1000)
    print("depois de tirar artista e tom:", ordem())
    # BPM no nome: o bloco BPM sai da ordem; de volta, só em faixas (a pasta "Exato" repetiria o nome)
    pg.select_option("#bpm_modo", "exato"); pg.wait_for_timeout(800)
    pg.check("#bpm_nome"); pg.wait_for_timeout(1200)
    exato_travado = lambda: pg.evaluate("document.querySelector('#bpm_modo option[value=exato]').disabled")  # noqa: E731
    assert ordem() == ["genero"] and pg.locator("#bpm_modo").is_disabled() and exato_travado() and pg.input_value("#bpm_modo") == "auto"
    pg.locator('#niveis-off .nivel[data-k="bpm"]').click(); pg.wait_for_timeout(1000)
    assert ordem() == ["genero", "bpm"] and not pg.locator("#bpm_modo").is_disabled() and exato_travado()
    print("BPM no nome + pasta de BPM em faixas:", pg.inner_text("#tree").replace("\n", " | ")[:80])
    # tom no nome: o bloco Tom e os modelos que o usam ficam bloqueados
    pg.check("#tom_nome"); pg.wait_for_timeout(1200)
    assert pg.locator('#niveis-off .nivel[data-k="camelot"]').is_disabled() and pg.locator(".pad:disabled").count() == 3
    pg.locator("#s2").screenshot(path=str(prints / "bloqueios.png"))
    pg.uncheck("#tom_nome"); pg.uncheck("#bpm_nome"); pg.wait_for_timeout(1200)
    assert not exato_travado() and pg.locator(".pad:disabled").count() == 0 and ordem() == ["genero", "bpm"]
    pg.check("#agrupar"); pg.wait_for_timeout(800)
    print("grupos antes:", pg.inner_text("#grupos-lista").replace("\n", " ")[:160])
    pg.locator("#grupos-lista select").first.select_option(index=1); pg.wait_for_timeout(1500)
    print("grupos depois:", pg.inner_text("#grupos-lista").replace("\n", " ")[:160])
    print("prévia com grupos:", pg.inner_text("#tree").replace("\n", " | ")[:200])
    pg.locator("#s2").screenshot(path=str(prints / "id-4-grupos.png"))
    pg.screenshot(path=str(prints / "passo-3.png"))
    pg.click("#b-avancar"); assert pg.locator("#b-concluir").is_visible() and not pg.locator("#b-avancar").is_visible()
    pg.click("#b-copiar"); pg.wait_for_selector("#res-copiar", state="visible", timeout=120000)
    print("copiar:", pg.inner_text("#res-copiar").replace("\n", " "))
    pg.wait_for_selector("#fim", state="visible", timeout=10000)
    print("tela final:", pg.inner_text("#fim-card").replace("\n", " | ")[:700])
    pg.locator("#fim-card").screenshot(path=str(prints / "id-3-tela-final.png"))
    pg.click("#fim-fechar"); pg.screenshot(path=str(prints / "id-2-final.png"), full_page=True)
    pg.click("#b-concluir"); pg.wait_for_timeout(300)   # concluir: volta para a tela inicial, sem fechar o programa
    assert pg.locator('section[data-p="1"]').is_visible() and not pg.locator("#b-concluir").is_visible()
    # outra pasta com duas músicas que já estão no destino e uma inédita: aparecem como repetidas
    import shutil
    origem2 = tmp / "outra"; origem2.mkdir()
    shutil.copy2(origem / "a0.mp3", origem2 / "copia de a0.mp3"); shutil.copy2(origem / "b1.mp3", origem2 / "b1 (1).mp3")
    T._faixa_som(origem2 / "inedita.mp3", "b", 30, {"title": "Inedita", "artist": "Art Nova", "album": "X", "genre": "Sub Z"})
    shutil.copy2(origem2 / "inedita.mp3", origem2 / "inedita - copia.mp3")   # repetida dentro da própria pasta
    pg.fill("#origem", str(origem2)); pg.click("#b-analisar")
    pg.wait_for_selector("#srep:not(.off)", timeout=180000); pg.wait_for_timeout(800)
    print("repetidas:", pg.inner_text("#srep").replace("\n", " | ")[:400])
    assert pg.locator("#rep-corpo tr").count() == 3 and "na mesma pasta" in pg.inner_text("#rep-corpo")
    pg.click("#b-rep-nova"); pg.wait_for_timeout(600)
    assert pg.locator('#rep-corpo select').first.input_value() == "nova"
    pg.locator("#srep").screenshot(path=str(prints / "repetidas.png"))
    pg.click('#passos button[data-p="4"]'); pg.click("#b-copiar"); pg.wait_for_selector("#fim", state="visible", timeout=120000)
    fim = pg.inner_text("#fim-card"); print("tela final 2:", fim.replace("\n", " | ")[:300])
    assert "trocadas pelas novas" in fim and len(list((destino / "Substituídas").rglob("*.mp3"))) == 2
    assert len([p for p in destino.rglob("*.mp3") if "Inedita" in p.name]) == 1    # só uma das duas cópias da inédita
    nav.close()
print("erros de console:", erros or "nenhum")
srv.shutdown()
