# Mixteca

**Português** · [English](README.en.md)

Organizador de músicas para Windows, pensado para quem toca: lê o **BPM** e o **tom** de cada música direto do áudio, completa as informações que faltam pela internet e monta cópias organizadas em pastas por **gênero → BPM → tom (Camelot)**, para você achar rápido o que combina na hora de mixar.

O Mixteca **só cria cópias**. As músicas originais nunca são movidas, alteradas ou apagadas.

> Uso gratuito para fins **não comerciais**. Veja [Licença](#licença).

## O que ele faz

- **Analisa o áudio:** BPM (sempre inteiro) e tom na notação Camelot, sem precisar tocar as músicas.
- **Completa as informações:** procura sozinho nome, artista, álbum, ano, gênero e capa do que estiver faltando. Capa, álbum e ano nunca vêm de coletâneas (como "Hits do Verão"), só de lançamentos do próprio artista.
- **Respeita o que já existe:** tags preenchidas e plausíveis não são mexidas. Só é corrigido o que é claramente lixo (por exemplo, gênero "Unknown" ou nome de site no título).
- **Sugere gênero** para as músicas que ficarem sem, cruzando outras músicas do mesmo artista, a sonoridade e a internet. Sugestões ficam marcadas como não confirmadas.
- **Organiza em pastas** na ordem que você escolher, com prévia antes de copiar.
- **Limpa nomes e tags nas cópias:** o arquivo vira `Artista - Título`, sem restos de vídeo ou de sites, e as tags ficam só com o que é útil. BPM e tom são gravados nas tags (mp3 e flac) para programas de DJ.
- **Melhora o áudio (opcional):** iguala o volume entre as músicas com um ajuste fixo por música (sem compressor nem limitador, então o volume não fica subindo e descendo) e corta subgrave inaudível, sempre em cópias separadas. Se chegar ao volume alvo fizesse a música estourar, ela fica um pouco abaixo do alvo.
- **Mostra o que combina:** na lista, clique numa música e veja as de tom compatível e BPM parecido.

## Instalação

1. Abra a aba **Actions** deste repositório.
2. Escolha **Gerar programa para Windows** e clique em **Run workflow**.
3. Quando terminar, baixe em **Artifacts**:
   - **Mixteca-Instalador** (`Mixteca-Setup.exe`): instala, cria atalhos e tem desinstalador.
   - **Mixteca-Portatil**: roda direto da pasta, sem instalar.

Como o instalador não tem assinatura digital, o Windows pode mostrar o aviso "O Windows protegeu o computador". Clique em **Mais informações** e **Executar assim mesmo**.

Para atualizar, rode o instalador novo por cima do antigo. Suas configurações são mantidas.

**Idioma:** o programa tem Português (Brasil) e Inglês (EUA). Ele começa no idioma do Windows, e você troca quando quiser em **Idioma / Language**, no canto inferior esquerdo. Em inglês, as pastas que o programa cria também ficam em inglês (`Review`, `Improved`).

Requisitos: Windows 10 ou 11. O programa abre em janela própria (WebView2); se o componente não existir, abre no navegador.

## Como usar

O programa é um passo a passo de quatro etapas.

### 1. Pastas
Escolha a pasta das suas músicas e uma pasta de destino para as cópias organizadas. Clique em **Analisar músicas**. A análise fica guardada: da segunda vez é rápida.

Antes de analisar, você pode abrir **Chaves e opções da busca na internet** para informar chaves opcionais (veja [Fontes de informação](#fontes-de-informação)).

### 2. Conferir
- **O que encontrei na internet:** resumo do que foi preenchido sozinho. O botão **Buscar de novo** serve para quando a conexão cair.
- **Sugestões que o programa não teve certeza:** trocas que ele não aplicou sozinho. Aceite ou recuse uma a uma, ou use **Aceitar as mostradas** e **Recusar as mostradas** (o filtro de confiança define o que está na lista; as de baixa confiança só são aceitas uma a uma).
- **Suas músicas:** a lista completa. O lápis ao lado do gênero troca o gênero daquela música. A etiqueta "sugestão" indica gênero não confirmado.
- **Gêneros para conferir:** uma linha por música sem gênero confirmado, com a sugestão e de onde ela veio. Confirme uma a uma ou todas de uma vez.

### 3. Organizar
- Monte a **ordem das pastas** arrastando os blocos (ou clicando neles): Gênero, BPM, Tom (Camelot), Artista e Ano, na sequência que quiser. Por exemplo `Gênero → BPM → Tom` ou `Tom → BPM → Gênero`. Há também modelos prontos, com exemplos das suas músicas.
- **Colocar o tom no começo do nome do arquivo:** em vez de uma subpasta por tom, cada arquivo vira `08A - Artista - Título`. Dentro de cada pasta, as músicas ficam em ordem harmônica.
- **Colocar o BPM no começo do nome do arquivo:** cada arquivo vira `128 - Artista - Título` (BPM sempre com 3 dígitos, como `090`, para a ordem ficar certa em qualquer aparelho). Com as duas opções ligadas, vira `128 - 08A - Artista - Título`: deixando só o Gênero na ordem das pastas, cada gênero fica numa lista única, do BPM mais baixo ao mais alto e, dentro do mesmo BPM, em ordem harmônica.
- O que vai no nome do arquivo não vira pasta ao mesmo tempo: ao marcar uma dessas opções, o bloco correspondente (BPM ou Tom) sai da ordem das pastas. O bloco Tom fica bloqueado, assim como os modelos prontos que o usam. O bloco BPM pode voltar, mas só em faixas: pastas como `126-130 BPM` com o BPM exato no nome se completam, enquanto a pasta de BPM exato repetiria o nome. A opção **BPM nas pastas** só fica ativa quando o BPM é uma das pastas. BPM ou tom incerto no nome também manda a música para a Revisão.
- **BPM nas pastas:**
  - *Automático:* junta BPMs vizinhos que têm poucas músicas (até 5 BPM de diferença), dentro de cada gênero.
  - *Exato:* uma pasta por BPM.
  - *Em faixas fixas:* intervalos de tamanho fixo (2, 3, 5 ou 10 BPM).
- **Juntar gêneros próximos na mesma pasta:** por exemplo, Tech House e Deep House vão para "House". Você pode mover qualquer gênero para outra pasta, criar uma pasta nova e renomear qualquer pasta (o lápis ao lado do nome). A tag da música continua com o gênero exato.
- A **prévia** mostra as pastas que serão criadas e lista as músicas que vão para **Revisão**, com o motivo de cada uma (sem gênero, BPM ou tom incerto).

As pastas de tom usam zero à esquerda (`01A`, `01B`, `02A`…), então ficam na ordem da roda harmônica em qualquer programa.

### 4. Copiar
- **Copiar músicas** cria as pastas e as cópias. No fim aparece um resumo com a conferência do que foi feito.
- **Concluir** volta para a tela inicial quando você terminar. O programa continua aberto e a análise fica guardada.
- **Melhorar o áudio** gera cópias melhoradas na subpasta `Melhoradas` do destino. Dá para escolher só as de qualidade baixa, só as que estouram ou todas.

### Músicas repetidas de outra pasta
Se você escolher **outra pasta de origem** e o mesmo destino, o Mixteca compara as músicas novas com o que já organizou ali antes (inclusive na pasta `Melhoradas`). As que já existem aparecem no passo 2, em **Músicas repetidas**, com a qualidade e a duração das duas versões. Para cada uma o programa sugere ficar com a de **qualidade melhor** (sem perdas, agudos menos cortados ou mais kbps; se forem parecidas, fica a que já está no destino), e você escolhe: **manter a do destino**, **trocar pela nova** ou **manter as duas**. Há botões para aplicar a todas de uma vez.

Duas músicas contam como a mesma quando artista e título batem e a duração é quase igual. **Outras versões** da mesma música, como Extended e Radio Edit, também aparecem na lista, marcadas como "outra versão": por padrão ficam as duas, mas você pode ficar só com uma (há um botão para ficar só com a mais longa em todas). Remix, VIP e bootleg contam como músicas diferentes. Nada é apagado: quando a nova entra no lugar, a antiga vai para a pasta `Substituídas` dentro do destino. As músicas que não se repetem são organizadas normalmente.

O mesmo vale para músicas que aparecem **mais de uma vez na própria pasta das músicas** (por exemplo, `Música.mp3` e `Música (1).mp3`): elas aparecem na mesma lista, o programa sugere ficar só com a de melhor qualidade e a outra deixa de ser copiada (o original continua na pasta, intacto).

### Organizar de novo no mesmo destino
Se você adicionar músicas ou mudar as opções e organizar outra vez no mesmo destino, o Mixteca não duplica nada: as cópias que mudaram de pasta são **movidas**, as que já estão no lugar são puladas e só as novas são copiadas. O mesmo vale para a pasta `Melhoradas`: tudo o que já foi melhorado antes acompanha a organização nova, mesmo as músicas que ficaram fora da escolha desta vez (por exemplo, "só as de qualidade baixa").

## Fontes de informação

Sem configurar nada, o Mixteca usa o **MusicBrainz** (dados das músicas) e o **Cover Art Archive** (capas). Chaves gratuitas opcionais melhoram o resultado:

| Serviço | Para quê | Como obter |
|---|---|---|
| Discogs | estilos mais detalhados; identifica músicas que o MusicBrainz não tem | conta em discogs.com → Settings → Developers → gerar token |
| Last.fm | gêneros marcados pela comunidade | conta em last.fm → criar uma "API account" |
| AcoustID | reconhece a música pelo som, mesmo sem nome nem tags | conta em acoustid.org → registrar uma aplicação |

As chaves ficam guardadas só no seu computador. Esses serviços têm termos próprios e são gratuitos apenas para uso não comercial.

**Níveis de confiança.** O que é encontrado com confiança alta ou média preenche sozinho os campos vazios. Palpites fracos viram sugestões para você decidir. Trocar uma informação que já existia sempre pede sua confirmação.

## Segurança dos seus arquivos

- Os originais nunca são alterados. Tags, capas e nomes novos vão apenas para as cópias.
- Nada é sobrescrito ou apagado no destino. Ao reorganizar, o programa só move cópias que ele mesmo criou e remove pastas que ficaram vazias. Cópias trocadas por versões melhores vão para `Substituídas`.
- Cada cópia fica registrada em `.organizador` dentro do destino, com as tags anteriores.
- O programa roda só no seu computador. A internet é usada apenas para consultar as fontes acima, enviando nome, artista e duração da música (e a impressão digital do áudio, se o AcoustID estiver ligado).

## Limites

- O **tom é uma estimativa**. Comparado com o que o djay mostra numa biblioteca de EDM, o Mixteca deu o mesmo tom em cerca de 7 de cada 10 músicas e um tom compatível (vizinho na roda Camelot) em cerca de 9 de cada 10. Confira nas pastas que mais usa.
- Remixes, bootlegs e lançamentos recentes podem não existir nas fontes abertas.
- A melhoria de áudio não recupera o que um MP3 de baixa qualidade já perdeu, nem corrige distorção gravada. Melhoradas feitas por versões anteriores ao ajuste fixo (que usavam compressão e podiam oscilar o volume) são refeitas sozinhas na próxima vez que você melhorar as mesmas músicas.
- No BPM automático, os nomes das pastas dependem das músicas que existem e podem mudar quando você adiciona músicas (as cópias são movidas para acompanhar).

## Onde ficam os dados

Configurações, chaves e análises ficam em `%APPDATA%\Mixteca`. Erros são registrados em `mixteca.log` nessa pasta. Desinstalar o programa não apaga essa pasta.

Opções avançadas, por arquivo nessa mesma pasta:
- `user_preferences.json`: regras próprias de nomes de gênero e palavras extras para limpar dos títulos.
- `extras\*.py`: fontes de gênero adicionais. Quem adiciona é responsável por respeitar os termos de uso do serviço consultado, e só deve colocar ali arquivos em que confia.

## Para desenvolvedores

Requer Python 3.12+ e FFmpeg/FFprobe (na pasta `ferramentas/` ou no PATH).

```
pip install -r requirements.txt
python iniciar.py
```

Testes:

```
python tests/test_basico.py
python tests/test_identificacao.py
python tests/e2e_identificacao_ui.py PASTA_PRINTS   # fluxo na tela (precisa do Playwright)
```

O pacote do Windows é gerado por `.github/workflows/build-windows.yml` (PyInstaller + Inno Setup). As licenças das peças de terceiros estão em `LICENCAS.md`.

Estrutura: `organizador/analise.py` (BPM, tom, qualidade) · `identificacao.py`, `decisao.py`, `casamento.py`, `classificador.py`, `provedores/` (busca e decisão de metadados) · `planejador.py` (pastas e cópia segura) · `repetidas.py` (músicas repetidas) · `escrita.py` (tags nas cópias) · `melhoria.py` (áudio) · `servidor.py` + `web/index.html` (interface).

## Licença

**PolyForm Noncommercial License 1.0.0** (arquivo `LICENSE`). Você pode usar, estudar e modificar o programa para fins não comerciais: uso pessoal, hobby, pesquisa, ensino e organizações sem fins lucrativos. **Vender o programa, incluí-lo em produto ou serviço pago ou usá-lo comercialmente exige autorização do autor.**

O programa é fornecido como está, sem garantia. As peças de terceiros (FFmpeg, numpy, scipy e outras) seguem as licenças delas.
