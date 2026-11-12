"""Varre uma pasta, lê as tags e analisa cada música (3 por vez, para não pesar na memória)."""
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .ajustes import aplicar_em_faixa
from .limpeza import limpar_texto
from .analise import analisar_arquivo
from .modelos import Faixa
from .store import Cache
from .taxonomia import Taxonomia

EXTENSOES = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus", ".aac", ".wma", ".aiff", ".aif"}


def listar_audios(origem) -> list[Path]:
    achados = []
    for raiz, pastas, arquivos in os.walk(origem):
        pastas[:] = [p for p in pastas if not p.startswith(".")]
        for nome in arquivos:
            if not nome.startswith(".") and Path(nome).suffix.lower() in EXTENSOES:
                achados.append(Path(raiz) / nome)
    return sorted(achados)


def esperar(pausa, cancelar) -> None:
    """Segura o trabalho enquanto o usuário mantém em pausa (continua ao retomar ou cancelar)."""
    while pausa is not None and pausa.is_set() and not (cancelar is not None and cancelar.is_set()):
        time.sleep(0.2)


def finalizar(f: Faixa, tax: Taxonomia | None, ov: dict | None) -> Faixa:
    """Aplica nomes padronizados de gênero e os ajustes aceitos. Não mexe no cache da análise."""
    f.titulo, f.artista, f.album = limpar_texto(f.titulo), limpar_texto(f.artista), limpar_texto(f.album)  # tira lixo de sites de download
    if f.genero:
        f.genero = tax.normalizar(f.genero) if tax else f.genero
        f.genero_fonte = "manual" if f.genero_manual else "tag"
    aplicar_em_faixa(f, ov)
    if f.ajustes.get("genero") and tax:  # ajustes antigos também recebem o nome padronizado (ex.: Mainstage -> Big Room)
        f.genero = f.ajustes["genero"] = tax.normalizar(f.genero)
    return f


def _processar(caminho: Path, cache: Cache, generos: dict, tax=None, ov=None) -> Faixa:
    st = os.stat(caminho)
    faixa = cache.obter(str(caminho), st.st_size, st.st_mtime)
    if faixa is None:
        dica = ((ov or {}).get("campos", {}).get("genero") or {}).get("valor", "")
        faixa = analisar_arquivo(caminho, generos, dica)
        if faixa.erro is None:
            if faixa.bitrate_kbps is not None and faixa.bitrate_kbps < 160 and faixa.codec in ("mp3", "aac"):
                faixa.qualidade_baixa = True
            cache.salvar(faixa, st.st_size, st.st_mtime)
    return finalizar(faixa, tax, ov)


def analisar_pasta(origem, cache: Cache, ao_progresso=None, cancelar=None, trabalhadores: int = 3,
                   pausa=None, tax: Taxonomia | None = None) -> list[Faixa]:
    arquivos = listar_audios(origem)
    generos = cache.generos_artista()
    sobrescritas = cache.sobrescritas()

    def tarefa(c):
        esperar(pausa, cancelar)
        if cancelar is not None and cancelar.is_set():
            return None
        return _processar(c, cache, generos, tax, sobrescritas.get(str(c)))

    resultados, feitos = [], 0
    with ThreadPoolExecutor(max_workers=trabalhadores) as pool:
        for fut in as_completed([pool.submit(tarefa, c) for c in arquivos]):
            faixa = fut.result()
            feitos += 1
            if faixa:
                resultados.append(faixa)
            if ao_progresso:
                ao_progresso(feitos, len(arquivos), faixa)
    return sorted(resultados, key=lambda f: f.caminho.lower())
