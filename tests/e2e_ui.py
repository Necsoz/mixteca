"""Teste de ponta a ponta com navegador. Uso: python tests/e2e_ui.py PASTA_COM_MP3 PASTA_DE_SAIDA_DOS_PRINTS"""
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from playwright.sync_api import sync_playwright  # noqa: E402

from organizador import servidor  # noqa: E402

fonte, prints = Path(sys.argv[1]), Path(sys.argv[2])
prints.mkdir(parents=True, exist_ok=True)
tmp = Path(tempfile.mkdtemp())
origem, destino = tmp / "cartao", tmp / "organizado"
origem.mkdir()
for p in fonte.glob("*.mp3"):
    shutil.copy2(p, origem / p.name.split("-", 1)[-1] if p.name[8:9] == "-" else origem / p.name)

srv = servidor.criar_servidor(0, tmp / "cache.db")
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/"
erros_console = []

with sync_playwright() as pw:
    nav = pw.chromium.launch()
    pg = nav.new_page(viewport={"width": 1180, "height": 900}, device_scale_factor=1)
    pg.on("console", lambda m: erros_console.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: erros_console.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.goto(url)
    pg.screenshot(path=str(prints / "1-inicio.png"))
    pg.fill("#origem", str(origem))
    pg.fill("#destino", str(destino))
    pg.click("#b-analisar")
    pg.wait_for_selector("#s2:not(.off)", timeout=120000)
    pg.wait_for_selector(".pad", timeout=30000)
    pg.wait_for_timeout(800)
    pg.screenshot(path=str(prints / "2-padrao-A.png"), full_page=True)
    print("chips:", pg.inner_text("#chips").replace("\n", " "))

    pg.click(".pad[data-id=B]")
    pg.wait_for_timeout(700)
    pg.select_option("#bpm_modo", "faixas")
    pg.wait_for_timeout(700)
    pg.click(".pad[data-id=A]")
    pg.wait_for_timeout(500)
    pg.select_option("#bpm_modo", "exato")
    pg.wait_for_timeout(600)

    pg.click("#b-copiar")
    pg.wait_for_selector("#res-copiar", state="visible", timeout=60000)
    print("copiar:", pg.inner_text("#res-copiar").replace("\n", " "))

    pg.click("#tree details > summary")
    pg.click("#corpo tr.m >> nth=2")
    pg.wait_for_timeout(400)
    pg.screenshot(path=str(prints / "3-tabela.png"), full_page=True)

    pg.select_option("#escopo", "todas")
    pg.click("#b-melhorar")
    pg.wait_for_selector("#res-melhorar", state="visible", timeout=400000)
    print("melhorar:", pg.inner_text("#res-melhorar").replace("\n", " "))
    pg.screenshot(path=str(prints / "4-final.png"), full_page=True)
    nav.close()

print("\n--- ESTRUTURA CRIADA ---")
for raiz, _, arqs in sorted(os.walk(destino)):
    for a in sorted(arqs):
        if not a.startswith("log-"):
            print(os.path.relpath(os.path.join(raiz, a), destino))
print("\nerros de console:", erros_console or "nenhum")
print("originais intactos:", sorted(p.name for p in origem.glob("*.mp3")) == sorted(p.name for p in origem.iterdir()))
srv.shutdown()
