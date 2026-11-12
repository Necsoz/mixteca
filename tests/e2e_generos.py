"""Teste no navegador: músicas SEM tag de gênero -> painel de gêneros -> gênero aplicado -> pastas.
Uso: python tests/e2e_generos.py PASTA_COM_MP3 PASTA_DOS_PRINTS"""
import subprocess
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
origem = tmp / "cartao"
origem.mkdir()
escolhidas = ["3ece0951", "6bcc03a6", "2c9880bf", "1d306db8"]  # 3LAU, 4B & Junkie Kid, Dr. Lobster, Alvaro & Carnage
for p in fonte.glob("*.mp3"):
    if p.name[:8] in escolhidas:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(p), "-map_metadata", "0", "-metadata", "genre=",
                        "-c", "copy", str(origem / p.name[9:])], check=True)

srv = servidor.criar_servidor(0, tmp / "cache.db")
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/"
erros = []
with sync_playwright() as pw:
    nav = pw.chromium.launch()
    pg = nav.new_page(viewport={"width": 1180, "height": 900})
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.on("dialog", lambda d: d.accept())
    pg.goto(url)
    pg.fill("#origem", str(origem))
    pg.fill("#destino", str(tmp / "organizado"))
    pg.click("#b-analisar")
    pg.wait_for_selector("#s2b:not(.off)", timeout=120000)
    print("artistas sem gênero:", pg.inner_text("#sg-n"))
    print("pastas ANTES:", pg.inner_text("#tree").replace("\n", " | ")[:200])
    pg.screenshot(path=str(prints / "g1-painel.png"), full_page=True)
    linhas = pg.query_selector_all("#sg-corpo tr")
    for tr in linhas:
        artista = tr.query_selector("td").inner_text()
        inp = tr.query_selector("input")
        inp.fill("Dubstep" if "Lobster" in artista else "Big Room" if artista in ("3LAU", "4B") else "Electro House")
    pg.click("#b-aplicar-gen")
    pg.wait_for_timeout(500)
    pg.wait_for_function("document.querySelector('#barra').style.display==='none'", timeout=120000)
    pg.wait_for_timeout(1500)
    print("painel depois (deve sumir):", "off" in pg.get_attribute("#s2b", "class"))
    print("pastas DEPOIS:", pg.inner_text("#tree").replace("\n", " | ")[:200])
    print("tabela:", [r.inner_text().replace("\t", " | ").replace("\n", " ") for r in pg.query_selector_all("#corpo tr.m")])
    pg.screenshot(path=str(prints / "g2-depois.png"), full_page=True)
    nav.close()
print("erros de console:", erros or "nenhum")
srv.shutdown()
