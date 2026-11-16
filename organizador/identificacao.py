"""Identifica cada música na internet (fase de REDE, guardada em cache) e transforma o resultado em propostas
de metadados com nível de confiança (fase de DECISÃO, só cálculo local, repetível a qualquer momento)."""
from . import casamento, decisao, limpeza
from . import extras
from .provedores import acoustid, capas, discogs, lastfm, musicbrainz
from .rede import ErroRede  # noqa: F401  (reexportado para quem chama)
from .taxonomia import Taxonomia

VERSAO_ONLINE = 5  # sobe quando a lógica de busca muda: resultados antigos são pesquisados de novo
CAMPOS_ROTULO = {"titulo": "Nome", "artista": "Artista", "album": "Álbum/Single", "ano": "Ano", "genero": "Gênero", "capa": "Capa"}


def pesquisar_online(faixa, cli, cred: dict, pasta_capas, so_capa: bool = False) -> dict:
    """Consulta as fontes para UMA música. Levanta ErroRede se a internet falhar (aí nada é guardado).
    `so_capa`: a música já está completa; só interessa saber se existe uma capa bem melhor que a embutida."""
    art, tit, origem = casamento.consulta_do_arquivo(faixa.titulo, faixa.artista, faixa.caminho)
    melhor = None
    # título só para PESQUISAR: sem trechos estranhos entre parênteses (ex.: nome de site), que fariam a busca falhar
    tit_busca = limpeza.sem_grupos_estranhos(tit) or tit
    for t in ([tit] + ([tit_busca] if tit_busca != tit else [])) if tit else []:
        if melhor is not None and melhor["_nota"]["nivel"] != "baixa":
            break
        for c in musicbrainz.buscar(cli, art, t, faixa.album):
            c["_nota"] = casamento.pontuar(art, tit, faixa.duracao, c, origem)
            if melhor is None or c["_nota"]["score"] > melhor["_nota"]["score"]:
                melhor = c
    fontes = ["MusicBrainz"] if melhor else []
    if cred.get("acoustid") and acoustid.disponivel() and (melhor is None or melhor["_nota"]["nivel"] != "alta"):
        imp = acoustid.impressao(faixa.caminho)
        res = acoustid.consultar(cli, cred["acoustid"], *imp) if imp else []
        if res and res[0]["score"] >= 0.9:
            c = musicbrainz.por_id(cli, res[0]["mbid"], faixa.album)
            if c:
                dd = abs(faixa.duracao - c["duracao"]) if faixa.duracao and c["duracao"] else None
                nota = casamento.pontuar(art, tit, faixa.duracao, c, "tags") if art and tit else {"score": 0, "nivel": "baixa"}
                # a impressão digital também erra (cadastros trocados no AcoustID): se o arquivo diz claramente outro
                # artista E outro título, a identificação pelo som é descartada (ex.: "Ibranovski - Vicious" não vira
                # uma música pop turca só porque o AcoustID disse)
                contradiz = bool(art and tit) and (nota.get("titulo") or 0) < 0.5 and (nota.get("artista") or 0) < 0.5
                if not contradiz:
                    if dd is None or dd <= 8:
                        nota = {**nota, "score": max(nota["score"], round(res[0]["score"] * 0.95, 3)), "nivel": "alta", "fingerprint": res[0]["score"]}
                    c["_nota"] = nota
                    if melhor is None or nota["score"] >= melhor["_nota"]["score"]:
                        melhor, fontes = c, ["AcoustID", "MusicBrainz"]
    generos_extras = {}  # fontes extras locais e opcionais (arquivos na pasta "extras"; ver extras.py)
    if tit and not so_capa:
        for mod in extras.carregar_todos(pasta_capas.parent):
            x = None
            for c in mod.buscar(cli, art, tit_busca, pasta_capas.parent):
                c["_nota"] = casamento.pontuar(art, tit, faixa.duracao, c, origem)
                if x is None or c["_nota"]["score"] > x["_nota"]["score"]:
                    x = c
            if x and x["_nota"]["nivel"] != "baixa":
                generos_extras[mod.FONTE] = x.pop("generos_extra", {})
                if melhor is None or x["_nota"]["score"] > melhor["_nota"]["score"]:
                    melhor, fontes = x, [mod.FONTE]
                else:
                    fontes.append(mod.FONTE)
    estilos_discogs = None
    if melhor is None and cred.get("discogs") and art and tit and not so_capa:
        # nenhuma outra fonte achou: o Discogs confirma que existe um lançamento desse artista com essa faixa
        d = discogs.lancamento(cli, cred["discogs"], art, tit_busca)
        if d:
            estilos_discogs = d["estilos"]
            melhor = {"fonte": "Discogs", "mbid": "", "titulo": tit_busca, "artista": art, "artista_mbid": "", "album": d["album"],
                      "tipo": "", "ano": d["ano"], "duracao": 0.0, "release_id": "", "release_group_id": "", "generos": {},
                      "_nota": {"score": 0.78, "nivel": "media", "titulo": 1.0, "artista": 1.0, "duracao_dif": None}}
            fontes = ["Discogs"]
    if melhor is None:
        return {"cand": None, "consulta": {"artista": art, "titulo": tit, "origem": origem}}

    if melhor.get("sem_lancamento") and melhor.get("mbid") and melhor["_nota"]["nivel"] in ("alta", "media"):
        # a busca só trouxe coletâneas: a gravação completa lista todos os lançamentos (single, EP, álbum do artista)
        completo = musicbrainz.por_id(cli, melhor["mbid"], faixa.album)
        if completo and not completo.get("sem_lancamento"):
            for k in ("album", "tipo", "ano", "release_id", "release_group_id"):
                melhor[k] = completo[k]
    melhor.pop("sem_lancamento", None)
    nota = melhor.pop("_nota")
    brutos = {"MusicBrainz": melhor.pop("tags_gravacao", {})}
    capa = None
    brutos.update({nome: g for nome, g in generos_extras.items() if g})
    capa_melhor = 0
    if nota["nivel"] in ("alta", "media"):
        if not so_capa:
            brutos["MusicBrainz (artista)"] = musicbrainz.generos_do_artista(cli, melhor.get("artista_mbid", ""))
        if cred.get("lastfm") and not so_capa:
            brutos["Last.fm"] = lastfm.tags(cli, cred["lastfm"], melhor["artista"], melhor["titulo"])
            fontes.append("Last.fm")
        if estilos_discogs is not None:
            brutos["Discogs"] = estilos_discogs
        elif cred.get("discogs") and not so_capa:
            brutos["Discogs"] = discogs.estilos(cli, cred["discogs"], melhor["artista"], melhor["titulo"])
            fontes.append("Discogs")
        ids = (melhor.get("release_id", ""), melhor.get("release_group_id", ""))
        if not faixa.tem_capa and any(ids):
            capa = capas.baixar(cli, pasta_capas, *ids)
            if capa:
                fontes.append("Cover Art Archive")
        elif faixa.tem_capa and nota["nivel"] == "alta" and any(ids) and cred.get("procurar_capa_melhor", True):
            lado = capas.lado_embutido(faixa.caminho)  # só troca se a da internet for bem maior que a que já está na música
            if 0 < lado < capas.LADO_BOM:
                capa = capas.baixar(cli, pasta_capas, *ids, tamanho="1200", minimo=max(800, int(lado * 1.3)))
                if capa:
                    capa_melhor = lado
                    fontes.append("Cover Art Archive")
    return {"cand": melhor, "nota": nota, "brutos": brutos, "capa": capa, "fontes": fontes, "so_capa": so_capa, "capa_melhor": capa_melhor,
            "consulta": {"artista": art, "titulo": tit, "origem": origem}}


def montar_proposta(faixa, online: dict | None, som, tax: Taxonomia) -> dict | None:
    """Une identificação online + sonoridade e propõe o que falta (ou o que parece errado)."""
    cand = (online or {}).get("cand")
    nota = (online or {}).get("nota") or {}
    nivel_id = nota.get("nivel", "baixa") if cand else "baixa"
    fontes = (online or {}).get("fontes", [])
    fonte_id = "AcoustID" if "AcoustID" in fontes else (fontes[0] if fontes else "MusicBrainz")
    rotulo = " + ".join(f for f in fontes if f not in ("AcoustID", "Cover Art Archive")) or "MusicBrainz"
    campos: dict[str, dict] = {}
    so_capa = bool((online or {}).get("so_capa"))

    def add(campo, atual, novo, fonte, conf, nivel, alteracao=False, nota_txt=""):
        campos[campo] = {"atual": atual, "novo": novo, "fonte": fonte, "conf": conf, "nivel": nivel,
                         "alteracao": alteracao, "nota": nota_txt}

    if cand and not so_capa:
        for campo in ("titulo", "artista", "album", "ano"):
            novo, atual = cand.get(campo) or "", getattr(faixa, campo, "") or ""
            if not novo:
                continue
            if not atual:
                add(campo, "", novo, fonte_id, nota["score"], nivel_id)
                continue
            limpo = casamento.sem_sobras(atual, novo) if campo in ("titulo", "album") else atual
            if limpo != atual and (nivel_id == "alta" or (nivel_id == "media" and (nota.get("artista") or 0) >= 0.8)):
                # a internet mostra que parte do texto não é do nome (ex.: site de onde o arquivo veio): tira sozinho
                add(campo, atual, limpo, fonte_id, nota["score"], nivel_id, False, "texto que não faz parte do nome foi removido")
            elif campo in ("titulo", "artista") and nivel_id == "alta":
                dif = casamento.sim(atual, novo) if campo == "titulo" else casamento.sim_artistas(atual, novo)
                if dif < 0.85:
                    add(campo, atual, novo, fonte_id, nota["score"], "media", True, "difere da tag atual; confira")
    if cand and online.get("capa") and nivel_id in ("alta", "media"):
        if not faixa.tem_capa:
            add("capa", "", online["capa"], "Cover Art Archive", nota["score"], nivel_id)
        elif online.get("capa_melhor") and nivel_id == "alta":
            add("capa", "", online["capa"], "Cover Art Archive", nota["score"], "alta", False,
                f"capa maior que a atual ({online['capa_melhor']} px)")

    atual = "" if (faixa.genero_fonte or "").startswith("sugestão") else faixa.genero  # sugestão não confirmada não trava a busca
    suspeito = tax.suspeito(atual)  # "Spotify", "2015"...: trata como se estivesse vazio
    artista_ref, ano_ref = faixa.artista or (cand or {}).get("artista", ""), faixa.ano or (cand or {}).get("ano", "")
    if so_capa:
        pass  # música completa: só a capa interessa, o gênero que já está gravado não é tocado
    elif not atual or tax.generico(atual) or suspeito:
        votos = decisao.votos_online(online["brutos"], tax) if cand else {}
        d = decisao.decidir_genero("" if suspeito else atual, votos, nivel_id, som, artista_ref, ano_ref, tax, rotulo)
        if d and d[0] != atual:
            add("genero", atual, d[0], d[1], d[3], d[2], False, d[4] + ("; o gênero gravado não fazia sentido" if suspeito and d[4] else
                                                                       "o gênero gravado não fazia sentido" if suspeito else ""))
    elif cand and nivel_id == "alta":
        # gênero gravado é plausível: ele manda. Só vira sugestão (nunca automática) se a internet, com certeza
        # na identificação, aponta para outra família de música (ex.: tag "Rock" numa faixa de Big Room).
        d = decisao.decidir_genero("", decisao.votos_online(online["brutos"], tax), "alta", None, artista_ref, ano_ref, tax, rotulo)
        fa, fn = tax.familia(atual), (tax.familia(d[0]) if d else None)
        if d and d[2] == "alta" and fa and fn and fa != fn:
            add("genero", atual, d[0], d[1], d[3], "media", True, f"a tag diz {atual}, mas a internet indica {d[0]}; confira")
    if not campos:
        return None
    tem = lambda c: bool(getattr(faixa, c, "")) or c in campos  # noqa: E731
    faltando = [CAMPOS_ROTULO[c] for c in ("titulo", "artista", "album", "genero") if not tem(c)]
    if not faixa.tem_capa and "capa" not in campos:
        faltando.append("Capa")
    return {"caminho": faixa.caminho, "status": "pendente", "campos": campos, "faltando": faltando,
            "identificacao": {"nivel": nivel_id, "score": nota.get("score"), "fontes": (online or {}).get("fontes", []),
                              "encontrado": (f"{cand['artista']} - {cand['titulo']}" if cand else ""),
                              "tipo": (cand or {}).get("tipo", ""), "consulta": (online or {}).get("consulta")}}
