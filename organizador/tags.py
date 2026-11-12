"""Leitura de tags e informações do arquivo via FFprobe (sem bibliotecas de tags de terceiros)."""
import json

from .ferramentas import achar, executar
from .generos import limpar_genero


def ler_info(caminho) -> dict:
    r = executar([
        achar("ffprobe"), "-v", "error",
        "-show_entries", "format=duration,bit_rate:format_tags:stream=codec_name,codec_type",
        "-of", "json", str(caminho),
    ])
    if r.returncode != 0:
        raise ValueError("não consegui ler o arquivo (formato não suportado ou corrompido)")
    dados = json.loads(r.stdout or b"{}")
    formato = dados.get("format", {})
    tags = {str(k).lower(): str(v) for k, v in (formato.get("tags") or {}).items()}
    codec = next((s.get("codec_name", "") for s in dados.get("streams", []) if s.get("codec_type") == "audio"), "")
    try:
        duracao = float(formato.get("duration") or 0)
    except ValueError:
        duracao = 0.0
    try:
        bitrate = int(formato.get("bit_rate") or 0) // 1000 or None
    except ValueError:
        bitrate = None
    tem_capa = any(s.get("codec_type") == "video" for s in dados.get("streams", []))
    data = tags.get("date") or tags.get("year") or tags.get("tyer") or ""
    return {
        "ano": data.strip()[:4] if data.strip()[:4].isdigit() else "",
        "tem_capa": tem_capa,
        "titulo": tags.get("title", ""),
        "artista": tags.get("artist") or tags.get("album_artist", ""),
        "album": tags.get("album", ""),
        "genero": limpar_genero(tags.get("genre", "")),
        "duracao": duracao,
        "bitrate_kbps": bitrate,
        "codec": codec,
    }
