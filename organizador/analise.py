"""Análise de áudio: BPM, tom (Camelot) e qualidade. Usa só numpy, scipy e FFmpeg.

Não toca a música: o FFmpeg decodifica um trecho de ~90 s direto para a memória.
"""
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d

from .camelot import camelot
from .ferramentas import achar, executar
from .generos import PADRAO, chave_artista, faixa_bpm
from .modelos import Faixa
from .tags import ler_info

SR = 44100
JANELA_S = 90

# Perfis de tonalidade de Krumhansl-Kessler (índice 0 = tônica)
PERFIL_MAIOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
PERFIL_MENOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def decodificar(caminho, inicio: float, duracao: float) -> np.ndarray:
    r = executar([
        achar("ffmpeg"), "-v", "error", "-ss", f"{inicio:.2f}", "-t", f"{duracao:.2f}",
        "-i", str(caminho), "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-",
    ])
    if r.returncode != 0 or not r.stdout:
        raise ValueError("falha ao decodificar o áudio")
    return np.frombuffer(r.stdout, dtype=np.float32)


def _stft_mag(x: np.ndarray, n_fft: int, hop: int) -> np.ndarray:
    if len(x) < n_fft + hop:
        raise ValueError("áudio curto demais")
    janela = np.hanning(n_fft).astype(np.float32)
    quadros = np.lib.stride_tricks.sliding_window_view(x, n_fft)[::hop]
    return np.abs(np.fft.rfft(quadros * janela, axis=1))


# ---------------------------------------------------------------- BPM
def _bpm(f: Faixa, x: np.ndarray, sr: int, genero_dica: str = "") -> None:
    hop, n_fft = 256, 1024
    mag = _stft_mag(x, n_fft, hop)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    bordas = np.searchsorted(freqs, np.geomspace(40, 10000, 25))
    energia = np.stack(
        [(mag[:, a:b] ** 2).sum(1) for a, b in zip(bordas[:-1], bordas[1:]) if b > a], axis=1
    )
    energia = energia / (np.percentile(energia, 95) + 1e-9)
    lg = np.log1p(100 * energia)
    onset = np.maximum(np.diff(lg, axis=0), 0).sum(1)
    fr = sr / hop  # quadros por segundo
    onset = onset - uniform_filter1d(onset, int(fr))  # tira a tendência lenta
    onset = onset * np.hanning(len(onset))

    t = np.arange(len(onset)) / fr
    grade = np.arange(30.0, 400.0, 0.1)
    X = np.empty(len(grade))
    for i in range(0, len(grade), 200):
        fase = np.exp(-2j * np.pi * np.outer(grade[i:i + 200] / 60.0, t))
        X[i:i + 200] = np.abs(fase @ onset)

    cand = np.arange(70.0, 185.01, 0.1)
    idx = lambda b: np.rint((b - 30.0) / 0.1).astype(int)  # noqa: E731
    score = X[idx(cand)] + 0.5 * X[idx(cand / 2)] + 0.5 * X[idx(cand * 2)]

    lo, hi = faixa_bpm(f.genero if (f.genero and faixa_bpm(f.genero) != PADRAO) else (genero_dica or f.genero))
    peso = np.where((cand >= lo - 3) & (cand <= hi + 3), 1.0, 0.6)  # gênero só desempata, não manda
    melhor = int(np.argmax(score * peso))
    b = float(cand[melhor])
    f.bpm = int(round(b))  # BPM sempre inteiro
    f.bpm_conf = round(float(score[melhor] / (np.median(score) + 1e-9)), 2)
    f.bpm_fora_da_faixa = (lo, hi) != PADRAO and (b < lo - 3 or b > hi + 3)


# ---------------------------------------------------------------- Tom
def _tom(f: Faixa, x: np.ndarray, sr: int) -> None:
    n_fft, hop = 8192, 4096
    mag = _stft_mag(x, n_fft, hop)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    sel = (freqs >= 100) & (freqs <= 2000)  # abaixo de 100 Hz é sub-bass, que atrapalha o tom
    m = mag[:, sel]
    midi = 69 + 12 * np.log2(freqs[sel] / 440)

    forte = freqs[sel] >= 200  # afinação da faixa (algumas estão alguns centésimos fora de 440 Hz)
    w = (m[:, forte] ** 2).sum(0)
    desvio = np.angle((w * np.exp(2j * np.pi * midi[forte])).sum()) / (2 * np.pi)
    ajustado = midi - desvio
    nota = np.rint(ajustado)
    peso = np.cos(np.pi * (ajustado - nota)) ** 2
    pcs = nota.astype(int) % 12

    comp = np.sqrt(m) * peso
    chroma = np.stack([comp[:, pcs == pc].sum(1) for pc in range(12)], axis=1)
    total = chroma.sum(1, keepdims=True)
    ok = total[:, 0] > np.percentile(total, 20)
    c = (chroma[ok] / total[ok]).mean(0)

    notas = []
    for t in range(12):
        notas.append((np.corrcoef(c, np.roll(PERFIL_MAIOR, t))[0, 1], t, False))
        notas.append((np.corrcoef(c, np.roll(PERFIL_MENOR, t))[0, 1], t, True))
    notas.sort(reverse=True)
    (c1, pc, menor), (c2, _, _) = notas[0], notas[1]
    f.tom_pc, f.tom_menor = int(pc), bool(menor)
    f.tom_conf = round(float(c1 - c2), 3)
    f.camelot = camelot(pc, menor)


# ---------------------------------------------------------------- Sonoridade (para classificar gênero)
NBANDAS = 20


def _vetor(f: Faixa, x: np.ndarray, sr: int) -> None:
    """Impressão compacta da sonoridade: formato do espectro (média e variação), brilho, graves, ritmo e dinâmica."""
    n_fft, hop = 4096, 2048
    pot = _stft_mag(x, n_fft, hop) ** 2
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    bordas = np.searchsorted(freqs, np.geomspace(35, 10000, NBANDAS + 1))
    bandas = np.stack([pot[:, a:max(b, a + 1)].sum(1) for a, b in zip(bordas[:-1], bordas[1:])], axis=1) + 1e-9
    total = bandas.sum(1, keepdims=True)
    rel = np.log10(bandas / total)
    centro = (pot * freqs).sum(1) / (pot.sum(1) + 1e-9)
    fluxo = np.maximum(np.diff(np.log(bandas), axis=0), 0).mean()
    graves = (bandas[:, :3].sum(1) / total[:, 0]).mean()
    crest = (f.pico_db or 0) - (f.rms_db or 0)
    v = [*rel.mean(0), *rel.std(0), centro.mean() / 1000, centro.std() / 1000, fluxo, graves, crest, float(f.bpm or 0)]
    f.vetor = [round(float(a), 4) for a in v]


# ---------------------------------------------------------------- Qualidade
def _qualidade(f: Faixa, x: np.ndarray) -> None:
    pico = float(np.abs(x).max())
    f.pico_db = round(20 * np.log10(max(pico, 1e-6)), 1)
    f.rms_db = round(20 * np.log10(float(np.sqrt(np.mean(x ** 2))) + 1e-9), 1)
    f.clip_pct = round(100 * float(np.mean(np.abs(x) >= 0.98)), 3)

    n_fft = 4096
    mag = _stft_mag(x[: SR * 45], n_fft, n_fft)
    pot = (mag ** 2).mean(0)
    pot = np.convolve(pot, np.ones(9) / 9, mode="same")
    nivel = 10 * np.log10(pot + 1e-12)
    hz_bin = SR / n_fft
    larg = int(600 / hz_bin)
    melhor_queda, melhor_fc = 0.0, None
    for fc in np.arange(10000, 21000, 100):
        i = int(fc / hz_bin)
        queda = nivel[i - larg:i].mean() - nivel[i:i + larg].mean()
        if queda > melhor_queda:
            melhor_queda, melhor_fc = queda, float(fc)
    f.corte_hz = melhor_fc if melhor_queda >= 12 else None
    f.qualidade_baixa = f.corte_hz is not None and f.corte_hz < 16500


def analisar_arquivo(caminho, generos_artista: dict | None = None, genero_dica: str = "") -> Faixa:
    f = Faixa(caminho=str(caminho))
    try:
        for k, v in ler_info(caminho).items():
            setattr(f, k, v)
        if not f.genero and generos_artista:  # gênero escolhido pelo usuário para o artista
            g = generos_artista.get(chave_artista(f.artista))
            if g:
                f.genero, f.genero_manual = g, True
        d = f.duracao
        janela = min(JANELA_S, d) if d > 0 else JANELA_S
        inicio = 0.0 if d <= JANELA_S + 20 else d * 0.2  # pula a intro das faixas longas
        if d > 0 and inicio + janela > d:
            inicio = max(0.0, d - janela)
        x44 = decodificar(caminho, inicio, janela)
        if len(x44) < SR * 10:
            raise ValueError("áudio curto demais para analisar")
        _qualidade(f, x44)
        x = signal.resample_poly(x44, 1, 2).astype(np.float32)
        _bpm(f, x, SR // 2, genero_dica)
        _tom(f, x, SR // 2)
        _vetor(f, x, SR // 2)
    except Exception as e:  # noqa: BLE001
        f.erro = str(e)
    return f
