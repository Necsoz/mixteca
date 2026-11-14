"""Configurações LOCAIS: preferências pessoais e credenciais de serviços.

Tudo fica na pasta de dados do usuário (no Windows: %APPDATA%\\Mixteca), fora do programa e fora do
repositório. Sem o arquivo de preferências, o app usa a classificação padrão.
"""
import json
import os
from pathlib import Path

from .ferramentas import pasta_dados

MODELO_PREFERENCIAS = {
    "versao": 1,
    "_ajuda": "Preferências locais deste computador. Este arquivo nunca deve ser enviado ao GitHub.",
    "mapa_generos": {},      # {"nome de origem": "Gênero final"}  (agrupa subgêneros)
    "manter_generos": [],    # nomes que NÃO são agrupados pelo mapa
    "artistas_dica": [],     # [{"artistas": [...], "genero": "...", "anos": [2011, 2016], "converter": [...]}]
    "limpar_termos": [],     # nomes de sites/programas que aparecem nos títulos e devem ser tirados (ex.: "nomedosite")
}
CREDENCIAIS_PADRAO = {"contato": "", "acoustid": "", "lastfm": "", "discogs": "", "grupos_pastas": "", "ordem_pastas": "", "pastas_renomeadas": "", "agrupar_generos": False, "aplicar_alta_automatico": True, "procurar_capa_melhor": True}
_CHAVES_CRED = set(CREDENCIAIS_PADRAO)


def _pasta(pasta) -> Path:
    return Path(pasta) if pasta else pasta_dados()


def arquivo_preferencias(pasta=None) -> Path:
    return _pasta(pasta) / "user_preferences.json"


def carregar_preferencias(pasta=None) -> dict:
    """Lê user_preferences.json; se não existir, cria um modelo neutro (comportamento padrão)."""
    arq = arquivo_preferencias(pasta)
    if not arq.exists():
        try:
            arq.write_text(json.dumps(MODELO_PREFERENCIAS, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
        return {}
    try:
        dados = json.loads(arq.read_text(encoding="utf-8-sig"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}  # arquivo com defeito: ignora e usa o padrão


def carregar_credenciais(pasta=None) -> dict:
    arq = _pasta(pasta) / "credenciais.json"
    cred = dict(CREDENCIAIS_PADRAO)
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        cred.update({k: v for k, v in dados.items() if k in _CHAVES_CRED})
    except (OSError, ValueError):
        pass
    return cred


def salvar_credenciais(novas: dict, pasta=None) -> dict:
    cred = carregar_credenciais(pasta)
    for k, v in novas.items():
        if k in _CHAVES_CRED:
            cred[k] = bool(v) if k in ("aplicar_alta_automatico", "procurar_capa_melhor", "agrupar_generos") else str(v).strip()
    arq = _pasta(pasta) / "credenciais.json"
    arq.write_text(json.dumps(cred, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(arq, 0o600)
    except OSError:
        pass
    return cred
