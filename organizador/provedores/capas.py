"""Cover Art Archive: capas de lançamentos do MusicBrainz. Só aceita a capa FRONTAL do lançamento identificado."""
import hashlib
import json
import struct
from pathlib import Path

from ..ferramentas import achar, executar

BASE = "https://coverartarchive.org"
MIN_LADO = 300
LADO_BOM = 1000  # capa embutida com este lado (px) ou mais já é boa: não vale procurar outra


def lado_embutido(caminho) -> int:
    """Menor lado (px) da capa que já está dentro do arquivo; 0 se não tem ou não deu para ler."""
    try:
        r = executar([achar("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                      "-of", "json", str(caminho)])
        s = (json.loads(r.stdout or b"{}").get("streams") or [{}])[0]
        return min(int(s.get("width") or 0), int(s.get("height") or 0))
    except Exception:  # noqa: BLE001
        return 0


def dimensoes(dados: bytes) -> tuple[int, int, str] | None:
    """(largura, altura, extensão) de um JPEG ou PNG, sem bibliotecas de imagem."""
    if dados[:8] == b"\x89PNG\r\n\x1a\n" and len(dados) > 24:
        l, a = struct.unpack(">II", dados[16:24])
        return l, a, ".png"
    if dados[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(dados):
            if dados[i] != 0xFF:
                i += 1
                continue
            m = dados[i + 1]
            if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
                i += 2
                continue
            tam = struct.unpack(">H", dados[i + 2:i + 4])[0]
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                a, l = struct.unpack(">HH", dados[i + 5:i + 9])
                return l, a, ".jpg"
            i += 2 + tam
    return None


def baixar(cli, pasta_capas, release_id: str = "", release_group_id: str = "", tamanho: str = "500", minimo: int = MIN_LADO) -> str | None:
    """Baixa a capa frontal do lançamento (500 ou 1200 px); devolve o caminho do arquivo salvo ou None."""
    pasta_capas = Path(pasta_capas)
    for url in ([f"{BASE}/release/{release_id}/front-{tamanho}"] if release_id else []) + \
               ([f"{BASE}/release-group/{release_group_id}/front-{tamanho}"] if release_group_id else []):
        status, corpo = cli.get(url, guardar=False)
        if status != 200:
            continue
        info = dimensoes(corpo)
        if not info or min(info[0], info[1]) < minimo or abs(info[0] - info[1]) > 0.15 * max(info[0], info[1]):
            continue  # não é imagem, é pequena demais ou não é quadrada (capa de álbum é quadrada)
        pasta_capas.mkdir(parents=True, exist_ok=True)
        arq = pasta_capas / (hashlib.sha1(corpo).hexdigest()[:20] + info[2])
        if not arq.exists():
            arq.write_bytes(corpo)
        return str(arq)
    return None
