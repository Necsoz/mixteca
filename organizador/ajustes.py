"""Metadados aceitos pelo usuário. Ficam guardados à parte (o original e a análise não mudam) e só são
gravados nas CÓPIAS na hora de organizar. Cada ajuste guarda o valor anterior, para poder desfazer."""
CAMPOS_TAG = ("titulo", "artista", "album", "ano", "genero")
normalizar_genero = None  # definido pelo programa: padroniza gêneros guardados em versões antigas (ex.: nome antigo -> atual)


def aplicar_em_faixa(faixa, ov: dict | None) -> None:
    aj = {}
    for campo, c in ((ov or {}).get("campos") or {}).items():
        if campo == "capa":
            aj["capa_arquivo"] = c["valor"]
        elif campo in CAMPOS_TAG:
            valor = normalizar_genero(c["valor"]) if campo == "genero" and normalizar_genero else c["valor"]
            setattr(faixa, campo, valor)
            aj[campo] = valor
            if campo == "genero":
                faixa.genero_fonte, faixa.genero_manual = c.get("fonte", ""), False
    faixa.ajustes = aj


def registrar(cache, todas: dict, faixa, campos: dict) -> None:
    """campos: {campo: {"novo", "fonte", "nivel"}}"""
    ov = todas.setdefault(faixa.caminho, {"campos": {}})
    for campo, c in campos.items():
        ja = ov["campos"].get(campo)
        anterior = ja["anterior"] if ja else ("" if campo == "capa" else getattr(faixa, campo, ""))
        ov["campos"][campo] = {"valor": c["novo"], "fonte": c.get("fonte", ""), "nivel": c.get("nivel", ""), "anterior": anterior}
    cache.sobrescrita_salvar(faixa.caminho, ov)
    aplicar_em_faixa(faixa, ov)


def desfazer(cache, todas: dict, faixa) -> None:
    ov = todas.pop(faixa.caminho, None)
    if ov:
        for campo, c in ov["campos"].items():
            if campo in CAMPOS_TAG:
                setattr(faixa, campo, c.get("anterior", ""))
                if campo == "genero":
                    faixa.genero_fonte = "tag" if faixa.genero else ""
    faixa.ajustes = {}
    cache.sobrescrita_salvar(faixa.caminho, None)
