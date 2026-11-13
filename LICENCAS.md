# Inventário de dependências e licenças

**Licença do próprio projeto:** PolyForm Noncommercial 1.0.0 (veja `LICENSE`): uso não comercial livre; uso comercial só com autorização do autor. As peças abaixo mantêm as licenças delas.

Objetivo: manter o projeto livre de peças que impeçam uma venda futura. **Esta lista foi montada
por pesquisa e conhecimento geral, não por revisão jurídica. Antes de comercializar, confira cada item
na versão que for distribuir e consulte um advogado.**

| Peça | Para quê | Licença | Situação |
|---|---|---|---|
| Python 3.12 (embutido no .exe) | linguagem | PSF (permissiva) | a confirmar na versão usada |
| numpy | cálculo da análise | BSD-3 | a confirmar na versão usada |
| scipy | cálculo da análise | BSD-3 | a confirmar na versão usada |
| PyInstaller | gerar o .exe | GPL com exceção que permite distribuir programas empacotados | a confirmar |
| FFmpeg / FFprobe (build **LGPL**) | ler áudio e tags, melhorar volume | LGPL 2.1+ | verificado no site do FFmpeg: não usar `--enable-gpl` nem `--enable-nonfree`; distribuir como programa separado, com o texto da licença e o link do código-fonte |
| MusicBrainz (API) | identificar músicas e gêneros | dados centrais CC0; tags/avaliações possivelmente CC BY-NC-SA | **a confirmar antes de vender**; exige User-Agent com contato, máx. ~1 req/s |
| Cover Art Archive | capas | API aberta; imagens com direitos dos titulares | **a confirmar**; uso comercial das imagens pode exigir cuidado |
| AcoustID + Chromaprint (`fpcalc`, opcional) | reconhecimento por som | AcoustID gratuito só para uso não comercial; Chromaprint MIT/LGPL | **a confirmar**; o `fpcalc` (binário oficial do Chromaprint 1.5.1, que embute partes do FFmpeg sob LGPL) é baixado pelo workflow e vai na pasta `ferramentas` |
| Last.fm (opcional) | tags de gênero | termos da API Last.fm | **a confirmar** (uso comercial) |
| Discogs (opcional, token gratuito) | estilos de música eletrônica | termos da API Discogs | **a confirmar** (uso comercial) |
| Interface (HTML/CSS/JS próprios) | tela | do próprio projeto | sem fontes nem ícones externos |

## Evitadas de propósito
- **mutagen** (GPL 2+), **Pedalboard** (GPL 3), **Essentia** (AGPL 3; modelos em CC BY-NC-ND).
- **librosa** (ISC, permissiva) chegou a ser avaliada, mas não é necessária: a análise usa só numpy/scipy.

## Ao distribuir o FFmpeg
Incluir `ferramentas/FFMPEG-LICENSE.txt`, avisar na tela “Sobre” ou no README que o programa usa FFmpeg
(LGPL 2.1) e oferecer o link do código-fonte da versão exata distribuída.
