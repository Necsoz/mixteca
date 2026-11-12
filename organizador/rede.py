"""Cliente HTTP educado: identifica o app, limita requisições por serviço, tenta de novo e guarda respostas em cache."""
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

LIMITES = {  # segundos mínimos entre pedidos ao mesmo serviço
    "musicbrainz.org": 1.1, "api.acoustid.org": 0.4, "ws.audioscrobbler.com": 0.3, "coverartarchive.org": 0.3,
    "api.discogs.com": 1.1,
}
PADRAO_LIMITE = 0.3
# O MusicBrainz só exige que o programa se identifique: usamos a página do projeto, o usuário não informa nada.
CONTATO_PADRAO = "https://github.com/Necsoz/mixteca"
TENTAR = (429, 500, 502, 503, 504)


class ErroRede(Exception):
    pass


def _urllib(url: str, cabecalhos: dict, timeout: float):
    req = urllib.request.Request(url, headers=cabecalhos)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read(), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read() or b"", dict(e.headers or {})


class Cliente:
    def __init__(self, contato: str = "", cache=None, transporte=None, dormir=time.sleep, relogio=time.monotonic):
        self.agente = f"OrganizadorMusical/{__version__} ( {(contato or '').strip() or CONTATO_PADRAO} )"
        self.cache, self._transp = cache, transporte or _urllib
        self._dormir, self._relogio = dormir, relogio
        self._ultimo: dict[str, float] = {}
        self._lock = threading.Lock()
        self.extra_off = ""  # nome de uma fonte extra que desistiu de responder (preenchido por ela)

    def _esperar_vez(self, host: str) -> None:
        with self._lock:
            intervalo = LIMITES.get(host, PADRAO_LIMITE)
            falta = self._ultimo.get(host, -1e9) + intervalo - self._relogio()
            if falta > 0:
                self._dormir(falta)
            self._ultimo[host] = self._relogio()

    def get(self, url: str, usar_cache: bool = True, guardar: bool = True, timeout: float = 25.0, aceitar: str | None = None):
        """(status, corpo_em_bytes). Respostas 200/404 ficam em cache; erros temporários são repetidos 3 vezes."""
        if usar_cache and self.cache is not None:
            achado = self.cache.http_obter(url)
            if achado is not None:
                return achado
        host = urllib.parse.urlparse(url).hostname or ""
        ultimo_erro = None
        for tentativa in range(4):
            self._esperar_vez(host)
            try:
                status, corpo, cab = self._transp(url, {"User-Agent": self.agente, "Accept": aceitar or "application/json, image/*"}, timeout)
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                ultimo_erro, status, corpo, cab = str(e), None, b"", {}
            if status is not None and status not in TENTAR:
                if guardar and self.cache is not None and status in (200, 404):
                    self.cache.http_guardar(url, status, corpo)
                return status, corpo
            ultimo_erro = ultimo_erro or f"HTTP {status}"
            espera = 2 ** (tentativa + 1)
            try:
                espera = max(espera, min(60, float(cab.get("Retry-After", 0))))
            except (TypeError, ValueError):
                pass
            if tentativa < 3:
                self._dormir(espera)
        raise ErroRede(f"Sem resposta de {host}: {ultimo_erro}")
