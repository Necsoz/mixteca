"""Cache das análises (SQLite): cada música é analisada uma vez e só de novo se o arquivo mudar."""
import json
import sqlite3
import threading
import time

from .modelos import Faixa

VERSAO = 3  # aumente quando o algoritmo de análise mudar, para refazer as análises antigas


class Cache:
    def __init__(self, arquivo):
        self._con = sqlite3.connect(str(arquivo), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._con.execute(
                "CREATE TABLE IF NOT EXISTS analises ("
                "caminho TEXT PRIMARY KEY, tamanho INTEGER, mtime REAL, versao INTEGER, dados TEXT)"
            )
            self._con.execute("CREATE TABLE IF NOT EXISTS generos_artista (chave TEXT PRIMARY KEY, genero TEXT)")
            self._con.execute("CREATE TABLE IF NOT EXISTS http (url TEXT PRIMARY KEY, status INTEGER, corpo BLOB, ts REAL)")
            self._con.execute("CREATE TABLE IF NOT EXISTS online (caminho TEXT PRIMARY KEY, tamanho INTEGER, mtime REAL, versao INTEGER, dados TEXT)")
            self._con.execute("CREATE TABLE IF NOT EXISTS propostas (caminho TEXT PRIMARY KEY, status TEXT, dados TEXT)")
            self._con.execute("CREATE TABLE IF NOT EXISTS sobrescritas (caminho TEXT PRIMARY KEY, dados TEXT)")
            self._con.execute("CREATE TABLE IF NOT EXISTS repetidas (caminho TEXT PRIMARY KEY, escolha TEXT)")
            self._con.commit()

    # ---- músicas repetidas: o que o usuário escolheu manter (sem escolha, vale a sugestão do programa)
    def repetidas_escolhas(self) -> dict:
        with self._lock:
            return dict(self._con.execute("SELECT caminho, escolha FROM repetidas").fetchall())

    def repetida_escolher(self, caminho: str, escolha: str | None) -> None:
        with self._lock:
            if escolha:
                self._con.execute("INSERT OR REPLACE INTO repetidas VALUES (?,?)", (caminho, escolha))
            else:
                self._con.execute("DELETE FROM repetidas WHERE caminho=?", (caminho,))
            self._con.commit()

    # ---- respostas da internet (evita repetir pesquisas)
    def http_obter(self, url: str, validade_dias: int = 90):
        with self._lock:
            r = self._con.execute("SELECT status, corpo, ts FROM http WHERE url=?", (url,)).fetchone()
        if r and time.time() - r[2] < validade_dias * 86400:
            return r[0], bytes(r[1])
        return None

    def http_guardar(self, url: str, status: int, corpo: bytes) -> None:
        with self._lock:
            self._con.execute("INSERT OR REPLACE INTO http VALUES (?,?,?,?)", (url, status, corpo, time.time()))
            self._con.commit()

    # ---- resultado da pesquisa online por música (permite pausar/continuar e recuperar após interrupção)
    def online_obter(self, caminho: str, tamanho: int, mtime: float, versao: int):
        with self._lock:
            r = self._con.execute("SELECT dados FROM online WHERE caminho=? AND tamanho=? AND mtime=? AND versao=?",
                                  (caminho, tamanho, mtime, versao)).fetchone()
        return json.loads(r[0]) if r else None

    def online_salvar(self, caminho: str, tamanho: int, mtime: float, versao: int, dados: dict) -> None:
        with self._lock:
            self._con.execute("INSERT OR REPLACE INTO online VALUES (?,?,?,?,?)",
                              (caminho, tamanho, mtime, versao, json.dumps(dados, ensure_ascii=False)))
            self._con.commit()

    # ---- propostas de metadados e alterações aceitas
    def propostas_salvar(self, lista: list[dict]) -> None:
        with self._lock:
            self._con.executemany("INSERT OR REPLACE INTO propostas VALUES (?,?,?)",
                                  [(p["caminho"], p["status"], json.dumps(p, ensure_ascii=False)) for p in lista])
            self._con.commit()

    def propostas_todas(self) -> list[dict]:
        with self._lock:
            return [json.loads(d) for (d,) in self._con.execute("SELECT dados FROM propostas")]

    def propostas_apagar(self, caminhos=None) -> None:
        with self._lock:
            if caminhos is None:
                self._con.execute("DELETE FROM propostas WHERE status='pendente'")
            else:
                self._con.executemany("DELETE FROM propostas WHERE caminho=?", [(c,) for c in caminhos])
            self._con.commit()

    def sobrescritas(self) -> dict:
        with self._lock:
            return {c: json.loads(d) for c, d in self._con.execute("SELECT caminho, dados FROM sobrescritas")}

    def sobrescrita_salvar(self, caminho: str, dados: dict | None) -> None:
        with self._lock:
            if dados:
                self._con.execute("INSERT OR REPLACE INTO sobrescritas VALUES (?,?)", (caminho, json.dumps(dados, ensure_ascii=False)))
            else:
                self._con.execute("DELETE FROM sobrescritas WHERE caminho=?", (caminho,))
            self._con.commit()

    def generos_artista(self) -> dict:
        with self._lock:
            return dict(self._con.execute("SELECT chave, genero FROM generos_artista").fetchall())

    def definir_genero_artista(self, chave: str, genero: str) -> None:
        with self._lock:
            if genero:
                self._con.execute("INSERT OR REPLACE INTO generos_artista VALUES (?,?)", (chave, genero))
            else:
                self._con.execute("DELETE FROM generos_artista WHERE chave=?", (chave,))
            self._con.commit()

    def obter(self, caminho: str, tamanho: int, mtime: float) -> Faixa | None:
        with self._lock:
            linha = self._con.execute(
                "SELECT dados FROM analises WHERE caminho=? AND tamanho=? AND mtime=? AND versao=?",
                (caminho, tamanho, mtime, VERSAO),
            ).fetchone()
        return Faixa.de_dict(json.loads(linha[0])) if linha else None

    def salvar(self, faixa: Faixa, tamanho: int, mtime: float) -> None:
        with self._lock:
            self._con.execute(
                "INSERT OR REPLACE INTO analises VALUES (?,?,?,?,?)",
                (faixa.caminho, tamanho, mtime, VERSAO, json.dumps(faixa.para_dict(), ensure_ascii=False)),
            )
            self._con.commit()
