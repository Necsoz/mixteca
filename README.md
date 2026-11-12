# Mixteca (Organizador Musical)

Programa pessoal para organizar músicas em pastas por **gênero → BPM → tom (Camelot)** e achar o que combina na hora de tocar.

- Lê o **BPM e o tom direto do áudio** (sem tocar as músicas) e o gênero das tags que já existem.
- Músicas **sem gênero nas tags** aparecem num painel agrupadas por artista: você escolhe o gênero (vale para todas as músicas dele), e o BPM é recalculado já com o gênero. O gênero fica guardado só no programa; os arquivos não são alterados.
- Mostra **4 padrões de pastas** aplicados às suas próprias músicas, com prévia, para escolher antes de copiar.
- **Só copia.** Os originais nunca são movidos, alterados ou apagados; nada é sobrescrito; fica um registro (log) no destino.
- Músicas em que não tem certeza (sem gênero, BPM duvidoso…) vão para a pasta **Revisão**.
- Melhoria de áudio **opcional e leve** (volume parecido, corte de subgrave inaudível, limitador de picos), sempre em **cópias** na pasta `Melhoradas`.
- **Identificação na internet (automática):** depois de analisar, o programa já busca sozinho (sem e-mail, sem chave, sem clique) e completa **nome, artista, álbum/single, ano, gênero e capa** das músicas incompletas. Detalhes na seção abaixo.
- Tela da biblioteca: clique numa música e veja as que combinam (tom compatível + BPM parecido).

## Identificação e metadados (v0.3)
**Como decide.** Para cada música incompleta: (1) usa as tags e o nome do arquivo (`Artista - Título`) e a duração; (2) busca no **MusicBrainz** e, se você tiver chave gratuita do **AcoustID** e o `fpcalc` na pasta `ferramentas/`, também reconhece pelo som; (3) pega capa oficial no **Cover Art Archive** (só imagem frontal de boa resolução; sem capa confiável, não aplica nada); (4) opcionalmente cruza gêneros com o **Last.fm** (chave gratuita). Nada é pesquisado de novo (cache em `%APPDATA%\OrganizadorMusical`), o ritmo respeita os limites de cada serviço e dá para pausar, cancelar e continuar de onde parou.

**Confiança.** *Alta* (título, artista e duração batem): aplicada sozinha apenas em campos que estavam vazios (dá para desligar). *Média*: aparece para você conferir e aceitar (individual ou em lote). *Baixa*: só aceita uma a uma. Trocas de informação que já existia sempre pedem conferência. Cada sugestão mostra valor atual, valor novo, fonte e nível.

**Gênero por música.** Vem das tags de gênero da internet quando a música foi identificada com segurança; senão, de um classificador que compara a **sonoridade** com as músicas da *sua* biblioteca que já têm gênero (com autoteste de acerto mostrado na tela). Nunca copia o gênero do artista para todas as músicas dele. Sem evidência suficiente, usa o gênero mais abrangente sustentado ou deixa em branco.

**Segurança.** Os originais nunca são alterados. Os dados novos só são gravados nas **cópias** (tags e capa via FFmpeg), e as tags anteriores ficam registradas no log do destino. Tudo pode ser desfeito na tela da biblioteca.

**Preferências pessoais (opcional, locais).** Regras como "agrupar subgêneros" ou "artistas X de 2011–2016 = Big Room" ficam em `user_preferences.json` dentro de `%APPDATA%\OrganizadorMusical`, **fora do programa e do repositório** (está no `.gitignore`). Sem esse arquivo o programa usa a classificação padrão; não há opção na tela para alternar. As chaves de API ficam em `credenciais.json`, também local.

**Fontes extras locais (opcional).** Quem quiser pode somar outras fontes de gênero colocando arquivos `.py` na pasta `extras` dentro de `%APPDATA%\OrganizadorMusical`. Elas não fazem parte deste repositório, e cada pessoa é responsável por respeitar os termos de uso de qualquer serviço que usar. Sem nenhum arquivo ali, o programa usa só MusicBrainz, Cover Art Archive e, se você informar chave, AcoustID, Last.fm e Discogs.

**Nomes e tags profissionais (nas cópias).** O arquivo copiado vira `Artista - Título.mp3`, sem endereços de sites e restos de vídeo ("Official Video", "www...", "320kbps"...); nomes de sites sem endereço você pode listar em `limpar_termos` nas suas preferências locais; versões como "Original Mix" e créditos de remix ficam. Em mp3, flac e m4a as tags são refeitas só com o que é útil (título, artista, álbum, gênero, ano, faixa...), sem comentários nem "encoded by", e BPM e tom (Camelot) são gravados para programas de DJ (mp3 e flac). As pastas de tom usam zero à esquerda (`01A`, `01B`, `02A`...), então qualquer visualizador as deixa na ordem da roda harmônica, com os tons que combinam por perto.

**Prioridade para o que já vem na música.** Gênero, título, artista e álbum já gravados e plausíveis não são mexidos. Só é corrigido sozinho o gênero que é lixo (nome de site, número, "unknown"...). Se a tag diz algo de outra família (ex.: Rock numa faixa de Big Room), vira sugestão para você conferir. A capa só é trocada quando a da internet é bem maior que a embutida.

**Limitações.** Remixes, bootlegs e faixas novas podem não existir nos bancos abertos. O código das fontes online foi testado com respostas simuladas, não com os serviços reais. O Discogs é opcional e exige um token gratuito.

## Limites (o que ele não faz)
- O **BPM** é sempre inteiro e é confiável na maioria dos casos. O **tom é uma estimativa**: costuma acertar ou cair numa vizinha da roda Camelot (que ainda combina na mixagem), mas pode errar. Confira nas pastas que mais usa.
- Não recupera o que um MP3 de baixa qualidade já perdeu: só avisa (⚠ qualidade baixa).
- A melhoria de áudio não mexe em distorção nem timbre. A cópia é um MP3 novo de alta qualidade.

## Rodar pelo código (precisa de Python 3.12+ e FFmpeg)
```
pip install -r requirements.txt
python iniciar.py
```
O FFmpeg/FFprobe devem estar na pasta `ferramentas/` ao lado do programa ou no PATH.

## Gerar o .exe do Windows
Use a receita `.github/workflows/build-windows.yml` (GitHub → Actions → “Gerar programa para Windows” → Run workflow). Ainda não foi testada no GitHub.

## Testes
```
python tests/test_basico.py        # unitários (CPU, ~1 min)
python tests/test_identificacao.py # identificação, gêneros, preferências, gravação em cópias (internet simulada)
python tests/e2e_identificacao_ui.py PASTA_PRINTS # fluxo completo no navegador
python tests/e2e_ui.py PASTA_MP3 PASTA_PRINTS   # (e tests/e2e_generos.py) ponta a ponta no navegador (precisa de playwright)
```

## Estrutura
`organizador/analise.py` BPM, tom e qualidade · `planejador.py` padrões de pasta e cópia segura · `melhoria.py` cadeia FFmpeg · `servidor.py` + `web/index.html` interface · `identificacao.py`, `decisao.py`, `casamento.py`, `classificador.py`, `taxonomia.py`, `config.py`, `escrita.py`, `provedores/` identificação e metadados · `store.py` cache SQLite em `%APPDATA%\OrganizadorMusical`.

## Licença

Este projeto usa a **PolyForm Noncommercial License 1.0.0** (veja `LICENSE`): você pode usar, estudar e modificar o programa para fins **não comerciais** (pessoal, hobby, pesquisa, ensino, instituições sem fins lucrativos). **Vender o programa, incluí-lo em produto ou serviço pago ou usá-lo comercialmente exige autorização do autor.** Não é uma licença "open source" no sentido estrito, porque proíbe uso comercial.

As peças de terceiros (FFmpeg, numpy, scipy etc.) seguem as licenças delas, listadas em `LICENCAS.md`. O programa é fornecido como está, sem garantia.
