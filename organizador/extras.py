"""Fontes extras LOCAIS e opcionais: arquivos .py colocados na pasta `extras`, dentro da pasta de dados do usuário
(no Windows: %APPDATA%\\Mixteca\\extras). Nada disso faz parte do programa distribuído: quem não colocar
nenhum arquivo ali usa apenas as fontes padrão. Cada extra define:

    FONTE = "Nome"                      # como aparece na tela
    PESO = 0.5                          # (opcional) peso do gênero dessa fonte na decisão, de 0 a 1
    SO_GENERO = False                   # (opcional) True se os nomes que ela devolve já são sempre gêneros
    def buscar(cli, artista, titulo, pasta=None) -> list[dict]:
        # candidatos no mesmo formato do MusicBrainz, mais "generos_extra": {"Gênero": peso}
"""
import importlib.util
from pathlib import Path

from . import decisao
from .ferramentas import pasta_dados

_cache: dict[str, object] = {}


def carregar_todos(pasta=None) -> list:
    base = (Path(pasta) if pasta else pasta_dados()) / "extras"
    if not base.is_dir():
        return []
    modulos = []
    for arq in sorted(base.glob("*.py")):
        chave = f"{arq}|{arq.stat().st_mtime_ns}"
        if chave not in _cache:
            try:
                spec = importlib.util.spec_from_file_location(f"organizador_extra_{arq.stem}", arq)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                ok = callable(getattr(mod, "buscar", None)) and isinstance(getattr(mod, "FONTE", None), str)
                if ok:
                    decisao.PESO_FONTES[mod.FONTE] = float(getattr(mod, "PESO", 0.5))
                    if getattr(mod, "SO_GENERO", False):
                        decisao.FONTES_SO_GENERO.add(mod.FONTE)
                _cache[chave] = mod if ok else None
            except Exception:  # noqa: BLE001 - um extra com defeito não pode derrubar o programa
                _cache[chave] = None
        if _cache[chave] is not None:
            modulos.append(_cache[chave])
    return modulos
