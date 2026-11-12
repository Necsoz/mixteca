"""Roda a análise numa pasta de músicas e mostra uma tabela. Uso: python tests/rodar_amostra.py PASTA"""
import glob
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from organizador.analise import analisar_arquivo  # noqa: E402
from organizador.camelot import nome_tom  # noqa: E402

pasta = sys.argv[1]
print(f"{'arquivo':34} {'gênero':12} {'BPM':>6} {'conf':>5} {'tom':13} {'cam':>4} {'conf':>6} {'corte':>6} {'pico':>5} {'rms':>6} {'t(s)':>5}")
for p in sorted(glob.glob(str(Path(pasta) / "*.mp3"))):
    t0 = time.time()
    f = analisar_arquivo(p)
    nome = Path(p).name.split("-", 1)[-1][:33]
    if f.erro:
        print(f"{nome:34} ERRO {f.erro}")
        continue
    tom = nome_tom(f.tom_pc, f.tom_menor)
    corte = f"{f.corte_hz / 1000:.1f}k" if f.corte_hz else "-"
    print(f"{nome:34} {f.genero[:12]:12} {f.bpm:6} {f.bpm_conf:5} {tom:13} {f.camelot:>4} {f.tom_conf:6} {corte:>6} {f.pico_db:5} {f.rms_db:6} {time.time() - t0:5.1f}")
