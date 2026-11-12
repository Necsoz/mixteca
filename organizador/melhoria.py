"""Melhoria básica de áudio, conservadora, sempre em CÓPIA (o original nunca é alterado).

O que faz: corta subgrave inaudível (abaixo de 25 Hz), deixa o volume parecido entre as músicas
(normalização de loudness) e segura os picos com um limitador, para não estourar.
O que NÃO faz: não recupera o que um MP3 ruim já perdeu e não mexe em distorção ou timbre.
"""
import json
from functools import lru_cache
from pathlib import Path

from .ferramentas import achar, executar

ALVO_PADRAO = -10.0  # LUFS


@lru_cache(maxsize=None)
def _tem_encoder(nome: str) -> bool:
    r = executar([achar("ffmpeg"), "-hide_banner", "-encoders"])
    return nome in r.stdout.decode(errors="ignore")


def _medir(origem, alvo: float) -> dict:
    r = executar([
        achar("ffmpeg"), "-nostats", "-i", str(origem), "-vn",
        "-af", f"highpass=f=25,loudnorm=I={alvo}:TP=-1:LRA=11:print_format=json", "-f", "null", "-",
    ])
    texto = r.stderr.decode(errors="ignore")
    i, j = texto.rfind("{"), texto.rfind("}")
    if i < 0 or j < i:
        raise RuntimeError("não consegui medir o volume")
    return json.loads(texto[i:j + 1])


def _codec(extensao: str) -> tuple[str, list[str]]:
    ext = extensao.lower()
    if ext == ".mp3" and _tem_encoder("libmp3lame"):
        return ".mp3", ["-c:a", "libmp3lame", "-q:a", "0", "-id3v2_version", "3"]
    if ext in (".m4a", ".aac"):
        return ".m4a", ["-c:a", "aac", "-b:a", "256k"]
    if ext == ".wav":
        return ".wav", ["-c:a", "pcm_s16le"]
    return ".flac", ["-c:a", "flac"]


def melhorar(origem, destino, alvo: float = ALVO_PADRAO) -> dict:
    """Gera uma cópia melhorada em `destino` (a extensão pode mudar). Só processa se for preciso."""
    m = _medir(origem, alvo)
    entrada, pico = float(m["input_i"]), float(m["input_tp"])
    if abs(entrada - alvo) <= 1.5 and pico <= -0.3:
        return {"status": "ja_bom", "entrada_lufs": entrada, "pico_db": pico}
    ext, codec = _codec(Path(origem).suffix)
    destino = Path(destino).with_suffix(ext)
    destino.parent.mkdir(parents=True, exist_ok=True)
    cadeia = (
        f"highpass=f=25,loudnorm=I={alvo}:TP=-1:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
        "alimiter=limit=0.89:level=disabled"
    )
    base = [achar("ffmpeg"), "-y", "-v", "error", "-i", str(origem)]
    saida = ["-af", cadeia, "-ar", "44100", *codec, "-map_metadata", "0", str(destino)]
    r = executar(base + ["-map", "0:a:0", "-map", "0:v:0?", "-c:v", "copy"] + saida)  # com a capa
    if r.returncode != 0:
        r = executar(base + ["-map", "0:a:0"] + saida)  # sem a capa
    if r.returncode != 0 or not destino.exists():
        raise RuntimeError(r.stderr.decode(errors="ignore")[-300:] or "falha ao gerar a cópia melhorada")
    return {"status": "melhorado", "entrada_lufs": entrada, "pico_db": pico, "destino": str(destino)}
