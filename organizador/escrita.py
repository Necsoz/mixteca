"""Grava tags e capa em uma CÓPIA (nunca no original), sem recodificar o áudio (FFmpeg -c copy).

O arquivo é refeito em um temporário e só então substitui a cópia; os metadados anteriores são devolvidos
para ficarem no log (permite restaurar). A capa é inserida/trocada só quando quem chama pede (música sem capa, ou capa da internet bem melhor).
Com `limpar=True` (mp3, flac, m4a) a cópia ganha um conjunto enxuto e profissional de tags: sem comentários,
"encoded by", links e outros restos de sites de download.
"""
import json
import os
from pathlib import Path

from .ferramentas import achar, executar

FORMATOS_COM_CAPA = {".mp3", ".m4a", ".flac"}
TAGS_FFMPEG = {"titulo": "title", "artista": "artist", "album": "album", "genero": "genre", "ano": "date"}
FORMATOS_LIMPEZA = {".mp3", ".flac", ".m4a"}
# tags úteis que sobrevivem à limpeza (o resto, como comentário e "encoded by", é descartado)
MANTER = ("album_artist", "track", "disc", "composer", "publisher", "tsrc")
# BPM e tom (Camelot) gravados para programas de DJ: nomes de tag por formato
TAGS_DJ = {".mp3": {"bpm": "TBPM", "camelot": "TKEY"}, ".flac": {"bpm": "BPM", "camelot": "INITIALKEY"}}


def _ler(arquivo) -> tuple[dict, bool]:
    r = executar([achar("ffprobe"), "-v", "error", "-show_entries", "format_tags:stream=codec_type", "-of", "json", str(arquivo)])
    d = json.loads(r.stdout or b"{}")
    tags = {str(k).lower(): str(v) for k, v in (d.get("format", {}).get("tags") or {}).items()}
    return tags, any(s.get("codec_type") == "video" for s in d.get("streams", []))


def gravar(arquivo, tags: dict, capa: str | None = None, limpar: bool = False) -> dict:
    """Devolve {"tags_anteriores": {...}, "capa_gravada": bool}. Levanta RuntimeError se falhar (a cópia fica intacta)."""
    arquivo = Path(arquivo)
    anteriores, tem_capa = _ler(arquivo)
    ext = arquivo.suffix.lower()
    limpar = limpar and ext in FORMATOS_LIMPEZA
    colocar_capa = bool(capa) and ext in FORMATOS_COM_CAPA and Path(capa).is_file()
    tmp = arquivo.with_name(f".tmp-{arquivo.name}")
    cmd = [achar("ffmpeg"), "-y", "-v", "error", "-i", str(arquivo)]
    if colocar_capa:
        cmd += ["-i", str(capa)]
    cmd += ["-map", "0:a"] + ([] if colocar_capa else ["-map", "0:v?"])  # capa nova substitui a antiga
    if colocar_capa:
        cmd += ["-map", "1:v", "-disposition:v:0", "attached_pic"]
    cmd += ["-c", "copy", "-map_metadata", "-1" if limpar else "0"]
    if limpar:
        for k in MANTER:
            if anteriores.get(k):
                cmd += ["-metadata", f"{k}={anteriores[k]}"]
    for campo, valor in tags.items():
        if campo in TAGS_FFMPEG and valor:
            cmd += ["-metadata", f"{TAGS_FFMPEG[campo]}={valor}"]
        elif campo in TAGS_DJ.get(ext, {}) and valor and limpar:
            cmd += ["-metadata", f"{TAGS_DJ[ext][campo]}={valor}"]
    if colocar_capa:
        cmd += ["-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)"]
    if ext == ".mp3":
        cmd += ["-id3v2_version", "3"]
    cmd.append(str(tmp))
    r = executar(cmd)
    if r.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(r.stderr.decode(errors="ignore")[-300:] or "falha ao gravar as tags")
    os.replace(tmp, arquivo)
    return {"tags_anteriores": anteriores, "capa_gravada": colocar_capa}
