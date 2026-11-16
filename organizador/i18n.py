"""Idiomas da interface: Português (Brasil) e Inglês (EUA).

O programa é escrito em português. Para o inglês:
  - `tela(html, "en")` troca os textos da página por uma lista de pares (trecho em português -> trecho em inglês).
    Os testes conferem que TODO trecho em português da lista ainda existe na página, então um texto alterado na tela
    sem atualizar a tradução é pego na hora.
  - `tr(texto, "en")` traduz as mensagens que vêm do servidor (erros, motivos, fontes das sugestões).
"""
import os
import re

IDIOMAS = ("pt", "en")


def detectar() -> str:
    """Idioma inicial: o do Windows (português -> pt; qualquer outro -> en). Fora do Windows, português."""
    forcado = os.environ.get("MIXTECA_IDIOMA", "").lower()
    if forcado in IDIOMAS:
        return forcado
    if os.name != "nt":
        return "pt"
    try:
        import ctypes
        return "pt" if (ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF) == 0x16 else "en"
    except Exception:  # noqa: BLE001
        return "pt"


def escolher(valor: str) -> str:
    return valor if valor in IDIOMAS else detectar()


# ----------------------------------------------------------------------------- textos da página (pt -> en)
TELA_EN: list[tuple[str, str]] = [
    # barra lateral
    ('aria-label="Passo a passo"', 'aria-label="Step by step"'),
    ('<span>1</span>Pastas</button>', '<span>1</span>Folders</button>'),
    ('<span>2</span>Conferir</button>', '<span>2</span>Review</button>'),
    ('<span>3</span>Organizar</button>', '<span>3</span>Organize</button>'),
    ('<span>4</span>Copiar</button>', '<span>4</span>Copy</button>'),
    ('Nada é apagado nem movido: o Mixteca só cria cópias organizadas.', 'Nothing is deleted or moved: Mixteca only creates organized copies.'),
    # passo 1
    ('<h2>Onde estão suas músicas?</h2>', '<h2>Where is your music?</h2>'),
    ('Escolha a pasta das músicas e uma pasta para as cópias organizadas. As originais nunca são movidas, alteradas ou apagadas.',
     'Pick your music folder and a folder for the organized copies. The originals are never moved, changed or deleted.'),
    ('Pasta das músicas (ex.: o cartão de memória)', 'Music folder (e.g. a memory card)'),
    ('placeholder="Ex.: E:\\Music"', 'placeholder="E.g. E:\\Music"'),
    ('placeholder="Ex.: D:\\Músicas"', 'placeholder="E.g. D:\\Organized"'),
    ('Escolher…', 'Browse…'),
    ('Pasta para as cópias organizadas', 'Folder for the organized copies'),
    ('Chaves e opções da busca na internet (opcional: token do Discogs etc.)', 'Keys and internet search options (optional: Discogs token etc.)'),
    ('Chave AcoustID (reconhece pelo som)', 'AcoustID key (recognizes by sound)'),
    ('Chave Last.fm (mais gêneros)', 'Last.fm key (more genres)'),
    ('Token Discogs (mais estilos)', 'Discogs token (more styles)'),
    ('Seu e-mail (só se quiser; o programa já se identifica sozinho)', 'Your e-mail (only if you want; the program already identifies itself)'),
    ('deixe vazio se não tiver', 'leave empty if you have none'),
    ('placeholder="deixe vazio"', 'placeholder="leave empty"'),
    (' Procurar <b>capa melhor</b> (maior) para músicas que já têm capa pequena; só troca se a nova for bem maior',
     ' Look for <b>better cover art</b> (larger) for tracks that already have a small cover; only replaced if the new one is much larger'),
    (' Aplicar sozinho o que for de <b>alta e média confiança</b> e estava vazio',
     ' Automatically apply <b>high and medium confidence</b> results to fields that were empty'),
    ('<button id="b-cfg">Salvar</button>', '<button id="b-cfg">Save</button>'),
    ('Analisar músicas</button>', 'Analyze music</button>'),
    ('A análise lê o BPM e o tom direto do áudio, sem tocar as músicas. Fica guardada, então da próxima vez é instantâneo.',
     'The analysis reads BPM and key straight from the audio, without playing the tracks. It is saved, so next time it is instant.'),
    # passo 2: internet e sugestões
    ('O que encontrei na internet <small', 'What I found online <small'),
    ('(automático)</small>', '(automatic)</small>'),
    ('(opcional)</small>', '(optional)</small>'),
    ('O Mixteca já procurou sozinho o que faltava em cada música (<b>nome, artista, álbum, ano, gênero e capa</b>) e preencheu o que tinha certeza. '
     'Para corrigir um gênero, use o lápis na lista abaixo. As músicas originais não são alteradas.',
     'Mixteca has already looked up what was missing in each track (<b>title, artist, album, year, genre and cover</b>) and filled in what it was sure about. '
     'To fix a genre, use the pencil in the list below. The original files are not changed.'),
    ('>Buscar de novo</button>', '>Search again</button>'),
    ('Só precisa se a conexão caiu ou se você quiser tentar outra vez.', 'Only needed if the connection dropped or you want to try again.'),
    ('Sugestões que o programa não teve certeza <small', 'Suggestions the program was not sure about <small'),
    ('<option value="">Todas</option>', '<option value="">All</option>'),
    ('>Alta confiança<', '>High confidence<'),
    ('>Média confiança<', '>Medium confidence<'),
    ('>Baixa confiança<', '>Low confidence<'),
    ('>Aceitar as mostradas<', '>Accept the ones shown<'),
    ('>Recusar as mostradas<', '>Reject the ones shown<'),
    ('Os botões valem para o que está na lista (use o filtro para escolher o nível). Baixa confiança nunca é aceita em lote: só uma a uma, no ✓ de cada linha. '
     'As informações são gravadas nas <b>cópias</b> no passo de copiar.',
     'The buttons apply to what is in the list (use the filter to choose the level). Low confidence is never accepted in bulk: only one by one, with the ✓ on each row. '
     'The information is written to the <b>copies</b> in the copy step.'),
    # passo 2: lista de músicas
    ('<h2>Suas músicas</h2>', '<h2>Your music</h2>'),
    ('Clique numa música: as que combinam com ela (tom compatível e BPM parecido) ficam destacadas em azul.',
     'Click a track: the ones that match it (compatible key and similar BPM) are highlighted in blue.'),
    ('placeholder="Buscar por nome, artista ou gênero…"', 'placeholder="Search by title, artist or genre…"'),
    ('Desfazer o que o programa completou na música selecionada', 'Undo what the program filled in for the selected track'),
    ('</span> BPM incerto · <span class="u">?</span> tom incerto · <span class="u">⚠</span> qualidade baixa (MP3 com agudos cortados)',
     '</span> uncertain BPM · <span class="u">?</span> uncertain key · <span class="u">⚠</span> low quality (MP3 with the highs cut off)'),
    # passo 3
    ('<h2>Como você quer as pastas?</h2>', '<h2>How do you want the folders?</h2>'),
    ('Monte a ordem das pastas: <b>arraste</b> os blocos (ou clique neles) para colocar, tirar e trocar de lugar. A primeira é a pasta de fora.',
     'Build the folder order: <b>drag</b> the blocks (or click them) to add, remove and reorder. The first one is the outer folder.'),
    ('<div class="l2">Ordem das pastas</div>', '<div class="l2">Folder order</div>'),
    ('aria-label="Ordem das pastas escolhida"', 'aria-label="Chosen folder order"'),
    ('<div class="l2">Disponíveis</div>', '<div class="l2">Available</div>'),
    ('aria-label="Níveis disponíveis"', 'aria-label="Available levels"'),
    ('content:"Solte aqui"', 'content:"Drop here"'),
    ('Modelos prontos (com exemplos das suas músicas)', 'Ready-made templates (with examples from your music)'),
    ('<label>BPM nas pastas:', '<label>BPM in folders:'),
    ('title="Automático: junta BPMs vizinhos que têm poucas músicas (até 5 BPM de diferença), dentro de cada gênero"',
     'title="Automatic: merges neighbouring BPMs that have few tracks (up to 5 BPM apart), within each genre"'),
    ('Automático (junta BPMs vizinhos)', 'Automatic (merges neighbouring BPMs)'),
    ('Exato (128 BPM)', 'Exact (128 BPM)'),
    ('Em faixas fixas', 'Fixed ranges'),
    ('Tamanho da faixa:', 'Range size:'),
    ('title="Ex.: Riddim, Brostep e Melodic Dubstep vão para a pasta Dubstep; Tech House e Deep House para House. A tag da música continua com o gênero exato."',
     'title="E.g. Riddim, Brostep and Melodic Dubstep go to the Dubstep folder; Tech House and Deep House go to House. The tag of the track keeps the exact genre."'),
    (' Juntar gêneros próximos na mesma pasta</label>', ' Put similar genres in the same folder</label>'),
    ('title="Ex.: “08A - Kura - TORA.mp3”. Dentro de cada pasta os arquivos ficam em ordem harmônica (01A, 01B, 02A...), sem criar subpastas de tom. '
     'O bloco Tom sai da ordem das pastas."',
     'title="E.g. “08A - Artist - Title.mp3”. Inside each folder the files sort in harmonic order (01A, 01B, 02A...), with no key subfolders. '
     'The Key block leaves the folder order."'),
    (' Colocar o tom no começo do nome do arquivo</label>', ' Put the key at the start of the file name</label>'),
    ('title="Ex.: “128 - Kura - TORA.mp3”. Dentro de cada pasta os arquivos ficam do BPM mais baixo ao mais alto, sem criar subpastas de BPM. Junto com o tom no nome vira “128 - 08A - Kura - TORA.mp3”: ordem de BPM e, no mesmo BPM, ordem harmônica. O bloco BPM sai da ordem das pastas; se quiser, coloque de volta para ter pastas em faixas (“126-130 BPM”) com o BPM exato no nome."',
     'title="E.g. “128 - Artist - Title.mp3”. Inside each folder the files sort from the lowest BPM to the highest, with no BPM subfolders. Together with the key in the name it becomes “128 - 08A - Artist - Title.mp3”: BPM order and, within the same BPM, harmonic order. The BPM block leaves the folder order; put it back if you want range folders (“126-130 BPM”) with the exact BPM in the name."'),
    (' Colocar o BPM no começo do nome do arquivo</label>', ' Put the BPM at the start of the file name</label>'),
    (' Colocar também as incertas nas pastas (em vez de “Revisão”)</label>', ' Also put the uncertain ones in the folders (instead of “Review”)</label>'),
    ('Como os seus gêneros ficaram agrupados. Para mudar, use a setinha ao lado do gênero: mande para outra pasta ou crie uma <b>nova pasta</b>. '
     'O lápis ao lado do nome <b>renomeia</b> a pasta. A prévia abaixo atualiza na hora.',
     'How your genres were grouped. To change it, use the arrow next to a genre: send it to another folder or create a <b>new folder</b>. '
     'The pencil next to the name <b>renames</b> the folder. The preview below updates right away.'),
    ('As músicas que o programa não tem certeza (sem gênero, <b>BPM ou tom duvidoso</b>…) vão para a pasta <b class="warn">Revisão</b>, '
     'dentro de uma subpasta com o motivo, em vez de serem classificadas no chute. Marcando a opção acima, elas entram nas pastas normais. '
     'O tom é uma estimativa: em caso de dúvida, confira nas pastas que mais usa.',
     'Tracks the program is not sure about (no genre, <b>doubtful BPM or key</b>…) go to the <b class="warn">Review</b> folder, '
     'inside a subfolder named after the reason, instead of being sorted by guesswork. With the option above checked, they go into the regular folders. '
     'The key is an estimate: when in doubt, double-check the folders you use most.'),
    # passo 2: gêneros para conferir
    ('<h2>Gêneros para conferir <small', '<h2>Genres to review <small'),
    ('</b> músicas ficaram sem gênero confirmado. Onde deu, o Mixteca já colocou uma <b>sugestão</b> (cruzando outras músicas do mesmo artista, a sonoridade e a internet). '
     'Confira, troque se quiser e confirme. Sugestões não confirmadas são usadas mesmo assim; músicas sem nenhum gênero vão para a pasta <b class="warn">Revisão</b>.',
     '</b> tracks have no confirmed genre. Where possible, Mixteca already added a <b>suggestion</b> (cross-checking other tracks by the same artist, the sound and the internet). '
     'Check them, change them if you like, and confirm. Unconfirmed suggestions are used anyway; tracks with no genre at all go to the <b class="warn">Review</b> folder.'),
    ('>Confirmar todas as sugestões</button>', '>Confirm all suggestions</button>'),
    ('<th>Música</th><th style="min-width:200px">Gênero</th><th>De onde veio a sugestão</th>',
     '<th>Track</th><th style="min-width:200px">Genre</th><th>Where the suggestion came from</th>'),
    # passo 4
    ('<h2>Copiar para o destino</h2>', '<h2>Copy to the destination</h2>'),
    ('Cria as pastas e <b>copia</b> as músicas. Se você já organizou antes neste mesmo destino, as cópias que mudaram de pasta são <b>movidas</b> (não duplicadas) '
     'e as que já estão no lugar são puladas. Um registro do que foi feito fica salvo no destino.',
     'Creates the folders and <b>copies</b> the tracks. If you have organized into this same destination before, copies whose folder changed are <b>moved</b> (not duplicated) '
     'and the ones already in place are skipped. A log of what was done is saved in the destination.'),
    (' Gravar nome, artista, álbum, gênero e capa encontrados <b>nas cópias</b> (as tags antigas ficam guardadas para desfazer)',
     ' Write the title, artist, album, genre and cover found <b>to the copies</b> (the old tags are kept so you can undo)'),
    ('>Copiar músicas</button>', '>Copy music</button>'),
    ('<h2>Melhorar o áudio <small', '<h2>Improve the audio <small'),
    ('Deixa o volume parecido entre as músicas, corta subgrave inaudível e segura picos que estouram. Gera <b>cópias novas</b> na pasta <b>Melhoradas</b> dentro do destino; '
     'as outras ficam como estão. Não recupera o que um MP3 de baixa qualidade já perdeu, e a cópia é um MP3 novo (alta qualidade). Leva cerca de 20 segundos por música.',
     'Evens out the volume across tracks, cuts inaudible sub-bass and tames clipping peaks. Creates <b>new copies</b> in the <b>Improved</b> folder inside the destination; '
     'the others stay as they are. It does not recover what a low-quality MP3 already lost, and the copy is a new (high quality) MP3. Takes about 20 seconds per track.'),
    ('<label>Quais:', '<label>Which:'),
    ('>Só as de qualidade baixa<', '>Only the low-quality ones<'),
    ('>Só as que estouram (pico acima de 0 dB)<', '>Only the ones that clip (peak above 0 dB)<'),
    ('<option value="todas">Todas</option>', '<option value="todas">All</option>'),
    ('<label>Volume alvo:', '<label>Target volume:'),
    ('>Suave (-14 LUFS)<', '>Soft (-14 LUFS)<'),
    ('>Padrão (-10 LUFS)<', '>Standard (-10 LUFS)<'),
    ('>Forte (-8 LUFS)<', '>Loud (-8 LUFS)<'),
    (' Refazer também as que já foram melhoradas antes (por padrão elas são aproveitadas: ficam onde estão ou são movidas para a pasta nova)',
     ' Also redo the ones already improved before (by default they are reused: they stay where they are or are moved to the new folder)'),
    ('>Criar cópias melhoradas</button>', '>Create improved copies</button>'),
    ('← Voltar', '← Back'),
    ('Continuar →', 'Continue →'),
    ('title="Volta para a tela inicial. O programa continua aberto e a análise fica guardada."', 'title="Goes back to the start screen. The program stays open and the analysis is kept."'),
    ('title="Volta para a tela inicial"', 'title="Goes back to the start screen"'),
    ('>✔ Concluir<', '>✔ Finish<'),
    ('Músicas repetidas <small', 'Duplicate tracks <small'),
    ('Músicas que já foram organizadas antes neste destino (vindas de outra pasta) ou que aparecem mais de uma vez na própria pasta das músicas. Para cada uma o programa sugere ficar com a de <b>qualidade melhor</b>; mude o que quiser. Nada é apagado: quando a nova entra no lugar de uma que já estava no destino, a antiga vai para a pasta <b>Substituídas</b>. Repetidas na própria pasta só deixam de ser copiadas.', 'Tracks that were already organized into this destination before (from another folder) or that appear more than once in the music folder itself. For each one the program suggests keeping the one with <b>better quality</b>; change whatever you like. Nothing is deleted: when the new one takes the place of one already in the destination, the old one goes to the <b>Replaced</b> folder. Duplicates within the music folder are simply not copied.'),
    ('>Seguir as sugestões<', '>Follow the suggestions<'),
    ('>Manter todas as do destino<', '>Keep all the destination ones<'),
    ('>Trocar todas pelas novas<', '>Replace all with the new ones<'),
    ('<th>Música</th><th>A outra versão</th><th>Esta</th><th>Ficar com</th>', '<th>Track</th><th>The other version</th><th>This one</th><th>Keep</th>'),
    ('[["destino","Ficar com a outra"],["nova","Ficar com esta"],["ambas","Manter as duas"]]', '[["destino","Keep the other one"],["nova","Keep this one"],["ambas","Keep both"]]'),
    ('"na mesma pasta: "', '"in the same folder: "'),
    ('"no destino"', '"in the destination"'),
    ('{melhor:"esta tem qualidade melhor",pior:"a outra tem qualidade melhor",parecida:"qualidade parecida: fica a outra"}', '{melhor:"this one has better quality",pior:"the other one has better quality",parecida:"similar quality: the other one stays"}'),
    ('"repetidas na própria pasta (não copiadas)"', '"duplicates within the folder (not copied)"'),
    ('repetidas na própria pasta puladas, ', 'duplicates within the folder skipped, '),
    ('"sem perdas"', '"lossless"'),
    ('{melhor:"a nova tem qualidade melhor",pior:"a do destino tem qualidade melhor",parecida:"qualidade parecida: fica a do destino",desconhecida:"no destino só há a cópia melhorada: fica ela"}', '{melhor:"the new one has better quality",pior:"the destination one has better quality",parecida:"similar quality: the destination one stays",desconhecida:"the destination only has the improved copy: it stays"}'),
    ('`${n("destino")} ficam com a outra versão, ${n("nova")} com esta, ${n("ambas")} com as duas.`', '`${n("destino")} keep the other version, ${n("nova")} keep this one, ${n("ambas")} keep both.`'),
    ('aria-label="Com qual ficar: ${esc(r.nome)}"', 'aria-label="Which to keep: ${esc(r.nome)}"'),
    ('[["destino","Manter a do destino"],["nova","Trocar pela nova"],["ambas","Manter as duas"]]', '[["destino","Keep the destination one"],["nova","Replace with the new one"],["ambas","Keep both"]]'),
    (' <small>(melhorada)</small>', ' <small>(improved)</small>'),
    ('r.escolhida?"sua escolha":"sugestão: "', 'r.escolhida?"your choice":"suggestion: "'),
    ('`<tr><td colspan="4" class="hint">Mostrando 500 de ${reps.length}. Os botões acima valem para todas.</td></tr>`', '`<tr><td colspan="4" class="hint">Showing 500 of ${reps.length}. The buttons above apply to all of them.</td></tr>`'),
    ('"repetidas: ficou a do destino"', '"duplicates: destination one kept"'),
    ('"trocadas pelas novas (antigas em Substituídas)"', '"replaced with the new ones (old ones in Replaced)"'),
    ('repetidas puladas (ficou a do destino), ', 'duplicates skipped (destination one kept), '),
    ('trocadas pelas novas (antigas em Substituídas), ', 'replaced with the new ones (old ones in Replaced), '),
    ('<button id="b-pausar">Pausar</button><button id="b-cancelar">Cancelar</button>', '<button id="b-pausar">Pause</button><button id="b-cancelar">Cancel</button>'),
    # ---- textos montados pelo script
    ('nomesNiveis={genero:"Gênero",bpm:"BPM",camelot:"Tom (Camelot)",artista:"Artista",ano:"Ano"}',
     'nomesNiveis={genero:"Genre",bpm:"BPM",camelot:"Key (Camelot)",artista:"Artist",ano:"Year"}'),
    ('"Erro desconhecido"', '"Unknown error"'),
    ('"Neste computador, cole o caminho da pasta no campo."', '"On this computer, paste the folder path into the field."'),
    ('{analisar:"Analisando e buscando na internet",copiar:"Copiando",melhorar:"Melhorando",reanalisar:"Recalculando",identificar:"Identificando"}[job.tipo]||"Trabalhando"',
     '{analisar:"Analyzing and searching online",copiar:"Copying",melhorar:"Improving",reanalisar:"Recalculating",identificar:"Identifying"}[job.tipo]||"Working"'),
    ('"Em pausa · "', '"Paused · "'),
    ('job.pausado?"Continuar":"Pausar"', 'job.pausado?"Resume":"Pause"'),
    ('erro("Cancelado.")', 'erro("Cancelled.")'),
    ('✔ Pronto.', '✔ Done.'),
    (' copiadas, ', ' copied, '),
    (' movidas de pasta, ', ' moved to another folder, '),
    (' já estavam no lugar, ', ' already in place, '),
    (' com erro</span>', ' with errors</span>'),
    ('<small>Registro: ', '<small>Log: '),
    ('>Ver resumo<', '>View summary<'),
    (' cópias melhoradas agora, ', ' copies improved now, '),
    (' aproveitadas de antes', ' reused from before'),
    (' movidas para a pasta nova)`', ' moved to the new folder)`'),
    (' já estavam boas, ', ' were already fine, '),
    ('<small>Pasta: ', '<small>Folder: '),
    ('Cópia cancelada', 'Copy cancelled'),
    ('✔ Cópia concluída e conferida', '✔ Copy finished and verified'),
    ('Cópia concluída, com avisos', 'Copy finished, with warnings'),
    ('<div class="hint">Pasta: <b>', '<div class="hint">Folder: <b>'),
    ('"músicas copiadas"', '"tracks copied"'),
    ('"movidas para a pasta nova"', '"moved to the new folder"'),
    ('"já estavam no lugar"', '"already in place"'),
    ('"com nome e tags organizados"', '"with name and tags tidied"'),
    ('"capas colocadas/melhoradas"', '"covers added/improved"'),
    ('"na pasta Revisão"', '"in the Review folder"'),
    ('"com erro"', '"with errors"'),
    ('Conferência: ', 'Check: '),
    (' arquivo(s) não foram encontrados no destino.', ' file(s) were not found in the destination.'),
    ('todos os arquivos estão no destino.', 'all files are in the destination.'),
    (' original(is) mudaram durante a cópia!', ' original(s) changed during the copy!'),
    ('Os originais não foram alterados.', 'The originals were not changed.'),
    (' cópia(s) ficaram com as tags antigas (a música está inteira).', ' copy(ies) kept the old tags (the audio is intact).'),
    ('"Pastas criadas (primeiro nível):"', '"Folders created (top level):"'),
    ('`Músicas na Revisão e o motivo${', '`Tracks in Review and why${'),
    ('` (mostrando ${rev.length} de ${r.revisao_total})`', '` (showing ${rev.length} of ${r.revisao_total})`'),
    ('… e mais ${rev.length-30}', '… and ${rev.length-30} more'),
    ('lista("Erros:"', 'lista("Errors:"'),
    ('Registro do que foi feito (permite restaurar tags): ', 'Log of what was done (lets you restore tags): '),
    ('>Abrir a pasta<', '>Open the folder<'),
    ('>Fechar<', '>Close<'),
    ('Abra esta pasta no seu computador:', 'Open this folder on your computer:'),
    ('</b> músicas</span>', '</b> tracks</span>'),
    ('</b> gêneros</span>', '</b> genres</span>'),
    ('</b> com qualidade baixa</span>', '</b> with low quality</span>'),
    ('</b> com erro de leitura</span>', '</b> could not be read</span>'),
    ('</b> músicas com informação faltando</span>', '</b> tracks with missing information</span>'),
    ('Sem exemplos ainda', 'No examples yet'),
    ('${p.pastas} pastas</small>', '${p.pastas} folders</small>'),
    ('"Clique para tirar; arraste para mudar de lugar; setas do teclado também movem":"Clique ou arraste para usar"',
     '"Click to remove; drag to reorder; the arrow keys also move it":"Click or drag to use"'),
    ('"Este modelo usa como pasta algo que já está no nome do arquivo. Desmarque a opção do nome para usar."',
     '"This template uses as a folder something that is already in the file name. Untick the name option to use it."'),
    ('"Só vale quando o BPM é uma das pastas. Coloque o bloco BPM na ordem das pastas para usar."',
     '"Only applies when BPM is one of the folders. Put the BPM block in the folder order to use it."'),
    ('"Já está no nome do arquivo. Desmarque a opção do nome para usar como pasta."',
     '"Already in the file name. Untick the name option to use it as a folder."'),
    (':"Automático: junta BPMs vizinhos que têm poucas músicas (até 5 BPM de diferença), dentro de cada gênero";',
     ':"Automatic: merges neighbouring BPMs that have few tracks (up to 5 BPM apart), within each genre";'),
    ('"Deixe pelo menos um nível na ordem das pastas."', '"Keep at least one level in the folder order."'),
    ('"Revisão"', '"Review"'),
    ('Músicas/ — <b>${r.total}</b> arquivos', 'Music/ — <b>${r.total}</b> files'),
    (' música(s) vão para a pasta Revisão</b>, e o motivo de cada uma:', ' track(s) go to the Review folder</b>, and the reason for each:'),
    ('… e mais ${it.length-40}', '… and ${it.length-40} more'),
    ('Copiar ${total} músicas para:', 'Copy ${total} tracks to:'),
    ('Os arquivos originais não serão alterados.', 'The original files will not be changed.'),
    ('Criar cópias melhoradas na pasta “Melhoradas” do destino?', 'Create improved copies in the “Improved” folder of the destination?'),
    ('As músicas originais não serão alteradas.', 'The original files will not be changed.'),
    ('["arquivo","Música"],["album","Álbum"],["genero","Gênero"],["bpm","BPM"],["camelot","Camelot"],["baixa","Qualidade"]',
     '["arquivo","Track"],["album","Album"],["genero","Genre"],["bpm","BPM"],["camelot","Camelot"],["baixa","Quality"]'),
    ('"fonte: "+f.genero_fonte', '"source: "+f.genero_fonte'),
    (' (não confirmado)">sugestão</span>', ' (unconfirmed)">suggestion</span>'),
    ('title="Trocar o gênero desta música"', 'title="Change the genre of this track"'),
    ('title="completado pelo programa: ', 'title="filled in by the program: '),
    ('title="Agudos cortados em ', 'title="Highs cut off at '),
    ('⚠ baixa</span>', '⚠ low</span>'),
    ('">erro</span>', '">error</span>'),
    ('title="tom incerto"', 'title="uncertain key"'),
    ('Mostrando 600 de ${lista.length}. Use a busca para filtrar.', 'Showing 600 of ${lista.length}. Use the search to filter.'),
    ('placeholder="gênero"', 'placeholder="genre"'),
    ('placeholder="escreva o gênero" aria-label="Gênero de ${esc(g.nome)}"', 'placeholder="type the genre" aria-label="Genre of ${esc(g.nome)}"'),
    ('esc(g.motivo||"sugestão"):"sem pistas: não achei nada parecido"', 'esc(g.motivo||"suggestion"):"no clues: found nothing similar"'),
    ('>Confirmar</button>', '>Confirm</button>'),
    ('Mostrando 300 de ${semGenero.length} músicas.', 'Showing 300 of ${semGenero.length} tracks.'),
    ('"Escreva o gênero antes de confirmar."', '"Type the genre before confirming."'),
    ('ROT={titulo:"Nome",artista:"Artista",album:"Álbum/Single",ano:"Ano",genero:"Gênero",capa:"Capa"}',
     'ROT={titulo:"Title",artista:"Artist",album:"Album/Single",ano:"Year",genero:"Genre",capa:"Cover"}'),
    ('title="Renomear esta pasta" aria-label="Renomear a pasta ${esc(p)}"', 'title="Rename this folder" aria-label="Rename the folder ${esc(p)}"'),
    ('${total} música${total===1?"":"s"}</span>', '${total} track${total===1?"":"s"}</span>'),
    ('"você mudou este gênero de pasta"', '"you moved this genre to another folder"'),
    ('aria-label="Mover ${esc(g.genero)}"><option value="">mover ▾</option>', 'aria-label="Move ${esc(g.genero)}"><option value="">move ▾</option>'),
    ('➕ Nova pasta…', '➕ New folder…'),
    ('↩ Voltar ao padrão', '↩ Back to default'),
    ('Nenhuma música com gênero ainda.', 'No tracks with a genre yet.'),
    ('`Nome da nova pasta para "${g.genero}":`', '`Name of the new folder for "${g.genero}":`'),
    ('"Novo nome da pasta:"', '"New folder name:"'),
    ('"(token guardado)"', '"(token saved)"'),
    ('"(chave guardada)"', '"(key saved)"'),
    ('"As chaves ficam só neste computador ("+esc(c.pasta_dados)+") e nunca vão para o GitHub."',
     '"Keys are stored only on this computer ("+esc(c.pasta_dados)+") and are never uploaded anywhere."'),
    ('" A chave AcoustID só funciona com o programa fpcalc, que não está instalado."', '" The AcoustID key only works with the fpcalc program, which is not installed."'),
    ("<b class='ok'>Salvo.</b>", "<b class='ok'>Saved.</b>"),
    ('✔ Nada a buscar.</b> Todas as músicas já têm nome, artista, gênero e capa.', '✔ Nothing to search.</b> Every track already has a title, artist, genre and cover.'),
    ('Sonoridade: acertou ', 'Sound check: guessed '),
    ('% ao tentar adivinhar o gênero de ', '% correctly when predicting the genre of '),
    (' músicas suas que já tinham gênero.', ' of your tracks that already had a genre.'),
    (' Pesquisei ${r.pesquisadas} músicas${', ' Searched ${r.pesquisadas} tracks${'),
    (' já estavam guardadas)`', ' were already saved)`'),
    (' e preenchi sozinho <b>', ' and filled in <b>'),
    ('</b> informações. `', '</b> pieces of information automatically. `'),
    ('</b> músicas sem gênero receberam uma <b>sugestão</b> (não confirmada). ', '</b> tracks with no genre received a <b>suggestion</b> (unconfirmed). '),
    (' sugestões ficaram para você conferir (opcional). ', ' suggestions are left for you to review (optional). '),
    (' músicas sem resultado confiável.', ' tracks with no reliable result.'),
    (' consultas falharam por problema de conexão; clique em Buscar de novo para tentar só essas.',
     ' lookups failed because of connection problems; click Search again to retry only those.'),
    ('A fonte extra “${esc(r.extra_indisponivel)}” não respondeu e foi deixada de lado; usei as outras fontes.',
     'The extra source “${esc(r.extra_indisponivel)}” did not respond and was skipped; the other sources were used.'),
    ('<span class="badge b-${c.nivel}">${c.nivel}</span>', '<span class="badge b-${c.nivel}">${({alta:"high",media:"medium",baixa:"low"})[c.nivel]||c.nivel}</span>'),
    ('Encontrado: ', 'Found: '),
    (' · fontes: ', ' · sources: '),
    ('||"sonoridade")', '||"sound")'),
    ('Não identificada na internet${', 'Not identified online${'),
    ('" (procurei: "', '" (searched for: "'),
    ('Continua faltando: ', 'Still missing: '),
    ('Mostrando 200 de ${lista.length}. Resolva estas para ver as próximas.', 'Showing 200 of ${lista.length}. Resolve these to see the next ones.'),
    ('`${r.campos} sugest${r.campos===1?"ão":"ões"} ${corpo.acao==="aceitar"?"aceita":"recusada"}${r.campos===1?"":"s"}.`',
     '`${r.campos} suggestion${r.campos===1?"":"s"} ${corpo.acao==="aceitar"?"accepted":"rejected"}.`'),
    ('"Nada para aceitar em lote (as de baixa confiança são aceitas uma a uma)."', '"Nothing to accept in bulk (low-confidence ones are accepted one by one)."'),
    ('"Nenhuma sugestão para recusar."', '"No suggestions to reject."'),
    ('"Pasta com as músicas"', '"Music folder"'),
    ('"Pasta de destino"', '"Destination folder"'),
]


def tela(html: str, idioma: str) -> str:
    """Devolve a página no idioma pedido (o original é português)."""
    html = html.replace("__IDIOMA__", idioma)
    if idioma != "en":
        return html
    html = html.replace('<html lang="pt-BR">', '<html lang="en-US">')
    for pt, en in TELA_EN:
        html = html.replace(pt, en)
    return html


# ----------------------------------------------------------------------------- mensagens do servidor (pt -> en)
_EXATO = {
    "Já existe uma tarefa em andamento. Espere terminar ou cancele.": "Another task is already running. Wait for it to finish or cancel it.",
    "Informe a pasta das músicas.": "Choose the music folder.",
    "Informe a pasta de destino.": "Choose the destination folder.",
    "Padrão de pastas inválido.": "Invalid folder template.",
    "Analise uma pasta primeiro.": "Analyze a folder first.",
    "A pasta de destino precisa ser diferente da pasta das músicas (e não pode ficar dentro dela).":
        "The destination folder must be different from the music folder (and cannot be inside it).",
    "Escolha um gênero.": "Choose a genre.",
    "Escreva o novo nome da pasta.": "Type the new folder name.",
    "Ainda não há uma cópia feita.": "No copy has been made yet.",
    "Nenhuma música se encaixa nessa escolha.": "No tracks match that choice.",
    "Volume alvo fora do intervalo permitido.": "Target volume outside the allowed range.",
    "Nenhum gênero para aplicar.": "No genre to apply.",
    "Ação inválida.": "Invalid action.",
    "Sugestões de baixa confiança precisam ser conferidas e aceitas uma a uma.": "Low-confidence suggestions must be checked and accepted one by one.",
    "Nada selecionado.": "Nothing selected.",
    "Escreva o gênero antes de confirmar.": "Type the genre before confirming.",
    "Música não encontrada.": "Track not found.",
    "Acesso negado.": "Access denied.",
    "Não encontrado.": "Not found.",
    "Sem acesso às fontes da internet. O que já foi pesquisado ficou guardado: verifique a conexão e clique em Buscar de novo para continuar de onde parou.":
        "Cannot reach the internet sources. What was already looked up is saved: check your connection and click Search again to continue where it stopped.",
    "Não consegui falar com a internet agora, então usei só a sonoridade das suas músicas. Quando a conexão voltar, clique em Buscar de novo.":
        "The internet could not be reached right now, so only the sound of your tracks was used. When the connection is back, click Search again.",
    "Conferindo o tamanho das capas": "Checking cover art sizes",
    "sem treino": "not trained",
    "você": "you",
    "som": "sound",
    "manual": "manual",
    "texto que não faz parte do nome foi removido": "text that is not part of the name was removed",
    "difere da tag atual; confira": "differs from the current tag; please check",
    "o gênero gravado não fazia sentido": "the stored genre did not make sense",
    "ajustado pela preferência local": "adjusted by a local preference",
    "sonoridade e preferência local concordam": "sound and local preference agree",
    "palpite fraco pela sonoridade": "weak guess based on the sound",
    "só há informação ampla; mantido o gênero mais abrangente": "only broad information is available; kept the most general genre",
    "Nome": "Title", "Artista": "Artist", "Álbum/Single": "Album/Single", "Ano": "Year", "Gênero": "Genre", "Capa": "Cover",
}
_PADROES = [(re.compile(p), r) for p, r in [
    (r"^A (pasta das músicas|pasta de destino) não existe: (.*)$", r"The folder does not exist: \2"),
    (r"^Erro inesperado: (.*)$", r"Unexpected error: \1"),
    (r"^Internet · (.*)$", r"Internet · \1"),
    (r"^Sonoridade · (.*)$", r"Sound · \1"),
    (r"^Ajustando BPM: (.*)$", r"Adjusting BPM: \1"),
    (r"^poucas músicas com gênero para aprender \(precisa de (\d+)\+ em pelo menos 2 gêneros\)$",
     r"too few tracks with a genre to learn from (needs \1+ in at least 2 genres)"),
    (r"^a sonoridade lembra (.*); confira$", r"the sound resembles \1; please check"),
    (r"^palpite pela sonoridade \(parecida com músicas suas de (.*)\)$", r"guess based on the sound (similar to your \1 tracks)"),
    (r"^a tag diz (.*), mas a internet indica (.*); confira$", r"the tag says \1, but the internet points to \2; please check"),
]]
_TRECHOS = [  # pedaços que aparecem dentro de fontes compostas, ex.: "sugestão: outras músicas do mesmo artista + sonoridade parecida"
    ("sugestão: ", "suggestion: "), ("outras músicas do mesmo artista", "other tracks by the same artist"),
    ("sonoridade parecida", "similar sound"), ("palpite da internet", "internet guess"),
    ("som + preferência local", "sound + local preference"), (" + som", " + sound"),
]


def tr(texto, idioma: str):
    """Traduz uma mensagem do servidor. Texto desconhecido volta como veio."""
    if idioma != "en" or not isinstance(texto, str) or not texto:
        return texto
    if texto in _EXATO:
        return _EXATO[texto]
    for padrao, troca in _PADROES:
        if padrao.match(texto):
            return padrao.sub(troca, texto)
    if "; " in texto:  # nota composta: traduz cada parte
        return "; ".join(tr(parte, idioma) for parte in texto.split("; "))
    for pt, en in _TRECHOS:
        texto = texto.replace(pt, en)
    return texto
