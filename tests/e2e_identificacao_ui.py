"""Navegador + internet SIMULADA: analisar -> identificar -> conferir -> aceitar -> copiar com tags. Uso: python tests/e2e_identificacao_ui.py PASTA_PRINTS"""
import sys
import threading
from pathlib import Path

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
    pg.goto(url); pg.fill("#origem", str(origem)); pg.fill("#destino", str(destino)); pg.click("#b-analisar")
    # só analisar: a busca na internet acontece sozinha, sem pedir e-mail, chave nem clique
    pg.wait_for_selector("#res-id", state="visible", timeout=180000); pg.wait_for_timeout(1500)
    print("e-mail pedido?", "obrigatório" in pg.inner_text("#si"))
    print("resultado:", pg.inner_text("#res-id").replace("\n", " "))
    pg.locator("#si").screenshot(path=str(prints / "id-1-revisao.png"))
    print("propostas restantes:", pg.locator(".prop").count())
    pg.click("#b-copiar"); pg.wait_for_selector("#res-copiar", state="visible", timeout=120000)
    print("copiar:", pg.inner_text("#res-copiar").replace("\n", " "))
    pg.wait_for_selector("#fim", state="visible", timeout=10000)
    print("tela final:", pg.inner_text("#fim-card").replace("\n", " | ")[:700])
    pg.locator("#fim-card").screenshot(path=str(prints / "id-3-tela-final.png"))
    pg.click("#fim-fechar"); pg.screenshot(path=str(prints / "id-2-final.png"), full_page=True); nav.close()
print("erros de console:", erros or "nenhum")
srv.shutdown()
