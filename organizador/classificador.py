"""Classificação de gênero pela SONORIDADE, aprendendo com as músicas da própria biblioteca.

Usa as músicas que já têm um gênero específico como exemplos: uma música sem gênero recebe o gênero das
parecidas (k vizinhos mais próximos). Como é treinado com a sua biblioteca, "sonoridade de Big Room" significa
o que as suas músicas de Big Room soam. O autoteste (deixa uma música de fora e tenta adivinhá-la) mostra
a precisão real de cada gênero; gêneros pouco confiáveis não são usados.
"""
import numpy as np


class ClassificadorSom:
    def __init__(self, k: int = 7, min_exemplos: int = 5, min_precisao: float = 0.6):
        self.k, self.min_exemplos, self.min_precisao = k, min_exemplos, min_precisao
        self.pronto = False
        self.autoteste: dict = {}
        self.motivo = "sem treino"

    def treinar(self, vetores: list, rotulos: list[str]) -> dict:
        self.pronto = False
        pares = [(v, r) for v, r in zip(vetores, rotulos) if v and r]
        if pares:
            tam = len(pares[0][0])
            pares = [(v, r) for v, r in pares if len(v) == tam]
        cont: dict[str, int] = {}
        for _, r in pares:
            cont[r] = cont.get(r, 0) + 1
        pares = [(v, r) for v, r in pares if cont[r] >= self.min_exemplos]
        classes = sorted({r for _, r in pares})
        if len(classes) < 2:
            self.motivo = f"poucas músicas com gênero para aprender (precisa de {self.min_exemplos}+ em pelo menos 2 gêneros)"
            self.autoteste = {"n": len(pares), "acuracia": None, "por_genero": {}}
            return self.autoteste
        X = np.array([v for v, _ in pares], dtype=np.float32)
        self.mu = X.mean(0)
        self.sigma = np.maximum(X.std(0), 1e-6)
        self.X = (X - self.mu) / self.sigma
        self.classes = classes
        self.y = np.array([classes.index(r) for _, r in pares])
        self._loo()
        self.pronto = True
        self.motivo = ""
        return self.autoteste

    def _votos(self, d: np.ndarray, y_vizinhos_idx: np.ndarray) -> np.ndarray:
        votos = np.zeros(len(self.classes))
        w = 1.0 / (d + 1e-3)
        np.add.at(votos, self.y[y_vizinhos_idx], w)
        return votos / votos.sum()

    def _loo(self) -> None:
        n = len(self.y)
        k = min(self.k, n - 1)
        certos = np.zeros(len(self.classes))
        previstos = np.zeros(len(self.classes))
        totais = np.bincount(self.y, minlength=len(self.classes)).astype(float)
        for ini in range(0, n, 400):
            bloco = self.X[ini:ini + 400]
            d = np.sqrt(np.maximum(
                (bloco ** 2).sum(1)[:, None] + (self.X ** 2).sum(1)[None, :] - 2 * bloco @ self.X.T, 0))
            for i in range(len(bloco)):
                d[i, ini + i] = np.inf
                viz = np.argpartition(d[i], k)[:k]
                p = self._votos(d[i, viz], viz)
                c = int(np.argmax(p))
                previstos[c] += 1
                certos[c] += c == self.y[ini + i]
        por = {}
        for i, nome in enumerate(self.classes):
            prec = certos[i] / previstos[i] if previstos[i] else 0.0
            rec = certos[i] / totais[i] if totais[i] else 0.0
            por[nome] = {"n": int(totais[i]), "precisao": round(float(prec), 2), "recall": round(float(rec), 2),
                         "confiavel": bool(prec >= self.min_precisao)}
        self.autoteste = {"n": n, "acuracia": round(float(certos.sum() / n), 3), "por_genero": por}

    def prever(self, vetor: list) -> tuple[str, float] | None:
        """(gênero, parcela dos votos) ou None se não houver base ou o gênero previsto não for confiável."""
        if not self.pronto or not vetor or len(vetor) != self.X.shape[1]:
            return None
        v = (np.array(vetor, dtype=np.float32) - self.mu) / self.sigma
        d = np.sqrt(((self.X - v) ** 2).sum(1))
        k = min(self.k, len(d))
        viz = np.argpartition(d, k - 1)[:k]
        p = self._votos(d[viz], viz)
        c = int(np.argmax(p))
        nome = self.classes[c]
        if not self.autoteste["por_genero"][nome]["confiavel"]:
            return None
        return nome, float(p[c])
