"""Melhoria básica de áudio, conservadora, sempre em CÓPIA (o original nunca é alterado).

O que faz: corta subgrave inaudível (abaixo de 25 Hz) e deixa o volume parecido entre as músicas com UM ajuste fixo
de volume por música (o mesmo do começo ao fim). Se chegar ao volume alvo fizesse os picos estourarem, a música fica
um pouco abaixo do alvo em vez de ser comprimida.
O que NÃO faz: não usa compressor nem limitador (eles fazem o volume "subir e descer", o efeito gangorra), não
recupera o que um MP3 ruim já perdeu e não mexe em distorção ou timbre.
"""
import json
import math
import os
from functools import lru_cache
from pathlib import Path

from .ferramentas import achar, executar

ALVO_PADRAO = -10.0  # LUFS
TETO_PICO = -1.0     # dBTP: o ajuste nunca passa disso
METODO = "ganho-fixo-v2"   # muda quando o jeito de melhorar muda: o que foi feito pelo método antigo é refeito


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


_FORMATO = {".mp3": "mp3", ".m4a": "ipod", ".wav": "wav", ".flac": "flac"}   # o temporário não tem a extensão certa


def _codec(extensao: str) -> tuple[str, list[str]]:
    ext = extensao.lower()
    if ext == ".mp3" and _tem_encoder("libmp3lame"):
        return ".mp3", ["-c:a", "libmp3lame", "-q:a", "0", "-id3v2_version", "3"]
    if ext in (".m4a", ".aac"):
        return ".m4a", ["-c:a", "aac", "-b:a", "256k"]
    if ext == ".wav":
        return ".wav", ["-c:a", "pcm_s16le"]
    return ".flac", ["-c:a", "flac"]


# faixas de valores que o filtro loudnorm do FFmpeg aceita na segunda passada
_LIMITES = {"input_i": (-99, 0), "input_tp": (-99, 99), "input_lra": (0, 99), "input_thresh": (-99, 0), "target_offset": (-99, 99)}


def _medidas_validas(m: dict) -> bool:
    """A medição às vezes devolve "inf"/"-inf" ou valores fora da faixa (música altíssima ou quase muda)."""
    try:
        return all(math.isfinite(float(m[k])) and lo <= float(m[k]) <= hi for k, (lo, hi) in _LIMITES.items())
    except (KeyError, TypeError, ValueError):
        return False


def _numero(m: dict, chave: str, padrao: float) -> float:
    try:
        v = float(m.get(chave))
        return v if math.isfinite(v) else padrao
    except (TypeError, ValueError):
        return padrao


def ganho(entrada_lufs: float, pico_dbtp: float, alvo: float) -> float:
    """Ajuste fixo (dB) para chegar perto do alvo sem o pico passar do teto."""
    return round(min(alvo - entrada_lufs, TETO_PICO - pico_dbtp), 2)


def melhorar(origem, destino, alvo: float = ALVO_PADRAO) -> dict:
    """Gera uma cópia melhorada em `destino` (a extensão pode mudar). Só processa se for preciso.

    Só mede (o loudnorm aqui serve apenas para medir loudness e pico) e aplica um volume fixo: nada de compressão
    dinâmica, que era o que fazia o volume oscilar."""
    m = _medir(origem, alvo)
    entrada, pico = _numero(m, "input_i", -99.0), _numero(m, "input_tp", 0.0)
    medido = math.isfinite(_numero(m, "input_i", math.nan)) and math.isfinite(_numero(m, "input_tp", math.nan))
    if entrada <= -70 or not medido:  # quase mudo ou medição impossível: melhor não mexer
        return {"status": "ja_bom", "entrada_lufs": entrada, "pico_db": pico}
    g = ganho(entrada, pico, alvo)
    if abs(g) < 0.5:  # diferença inaudível: não vale gerar outra cópia
        return {"status": "ja_bom", "entrada_lufs": entrada, "pico_db": pico}
    ext, codec = _codec(Path(origem).suffix)
    destino = Path(destino).with_suffix(ext)
    destino.parent.mkdir(parents=True, exist_ok=True)
    base = [achar("ffmpeg"), "-y", "-v", "error", "-i", str(origem)]
    # jeitos de gravar, do melhor para o mais simples: o codificador de MP3 (LAME) da versão do FFmpeg para Windows
    # falha em algumas músicas no modo VBR ("Cannot allocate memory"); aí vai em taxa fixa (320 kbps), com áudio de 16 bits
    jeitos = [(f"highpass=f=25,volume={g}dB", codec)]
    if ext == ".mp3":
        jeitos.append((f"highpass=f=25,volume={g}dB,aformat=sample_fmts=s16p", ["-c:a", "libmp3lame", "-b:a", "320k", "-id3v2_version", "3"]))
    # grava num temporário e só no fim troca pelo definitivo: uma falha no meio nunca deixa um arquivo pela metade
    tmp = destino.with_name(f".tmp-{destino.name}")
    r = None
    try:
        for cadeia, cod in jeitos:
            saida = ["-af", cadeia, "-ar", "44100", *cod, "-map_metadata", "0", "-f", _FORMATO.get(ext, ext[1:]), str(tmp)]
            r = executar(base + ["-map", "0:a:0", "-map", "0:v:0?", "-c:v", "copy"] + saida)  # com a capa
            if r.returncode != 0:
                r = executar(base + ["-map", "0:a:0"] + saida)  # sem a capa
            if r.returncode == 0 and tmp.exists() and tmp.stat().st_size > 0:
                break
        if r.returncode != 0 or not tmp.exists():
            raise RuntimeError(r.stderr.decode(errors="ignore")[-300:] or "falha ao gerar a cópia melhorada")
        os.replace(tmp, destino)
    finally:
        tmp.unlink(missing_ok=True)
    return {"status": "melhorado", "entrada_lufs": entrada, "pico_db": pico, "ganho_db": g, "destino": str(destino)}
