# Mixteca

[Português](README.md) · **English**

A music organizer for Windows, built for people who mix: it reads the **BPM** and **key** of each track straight from the audio, fills in missing information from the internet, and builds organized copies in folders by **genre → BPM → key (Camelot)**, so you can quickly find what blends well.

Mixteca **only creates copies**. Your original files are never moved, changed or deleted.

> Free for **noncommercial** use. See [License](#license).

> The interface is available in English (US) and Portuguese (Brazil). It starts in your Windows language, and you can switch at any time under **Idioma / Language** in the bottom-left corner.

## What it does

- **Analyzes the audio:** BPM (always a whole number) and key in Camelot notation, without playing the tracks.
- **Fills in information:** looks up title, artist, album, year, genre and cover art for whatever is missing.
- **Respects what is already there:** tags that are filled in and plausible are left alone. Only obvious junk is fixed (for example, an "Unknown" genre or a website name in the title).
- **Suggests a genre** for tracks left without one, by cross-checking other tracks from the same artist, how the track sounds, and the internet. Suggestions are marked as unconfirmed.
- **Organizes into folders** in the order you choose, with a preview before copying.
- **Cleans names and tags on the copies:** files become `Artist - Title`, without leftovers from videos or websites, and tags keep only what is useful. BPM and key are written to the tags (mp3 and flac) for DJ software.
- **Improves the audio (optional):** evens out the volume across tracks, cuts inaudible sub-bass and tames peaks, always in separate copies.
- **Shows what matches:** click a track in the list to highlight the ones with a compatible key and a similar BPM.

## Installation

1. Open the **Actions** tab of this repository.
2. Choose **Gerar programa para Windows** ("Build the Windows program", the workflow name) and click **Run workflow**.
3. When it finishes, download from **Artifacts**:
   - **Mixteca-Instalador** (`Mixteca-Setup.exe`): the installer. It installs the program, creates shortcuts and includes an uninstaller.
   - **Mixteca-Portatil**: the portable version. It runs straight from its folder, no installation.

The installer is not digitally signed, so Windows may show a "Windows protected your PC" warning. Click **More info** and then **Run anyway**.

To update, run the new installer over the old one. Your settings are kept.

Requirements: Windows 10 or 11. The program opens in its own window (WebView2); if that component is missing, it opens in your browser.

## How to use it

The program is a four-step walkthrough.

### 1. Folders
Pick the folder with your music and a destination folder for the organized copies. Click **Analyze music**. The analysis is saved, so the second time is fast.

Before analyzing, you can open **Keys and internet search options** to enter optional keys (see [Information sources](#information-sources)).

### 2. Review
- **What I found online:** a summary of what was filled in automatically. **Search again** is for when the connection drops.
- **Suggestions the program was not sure about:** changes it did not apply on its own. Accept or reject them one by one, or use **Accept the ones shown** / **Reject the ones shown**. The confidence filter decides what is in the list; low-confidence suggestions can only be accepted one by one.
- **Your music:** the full list. The pencil next to a genre changes that track's genre. The "suggestion" label marks an unconfirmed genre.
- **Genres to review:** one row per track without a confirmed genre, with the suggestion and where it came from. Confirm one at a time or all at once.

### 3. Organize
- Build the **folder order** by dragging the blocks (or clicking them): Genre, BPM, Key (Camelot), Artist and Year, in any sequence. For example `Genre → BPM → Key` or `Key → BPM → Genre`. Ready-made templates are also available, with examples from your own music.
- **Put the key at the start of the file name:** instead of one subfolder per key, each file becomes `08A - Artist - Title`. Remove the Key block from the folder order and the tracks inside each folder sort in harmonic order.
- **BPM in folders:**
  - *Automatic:* merges neighbouring BPMs that have few tracks (up to 5 BPM apart), within each genre.
  - *Exact:* one folder per BPM.
  - *Fixed ranges:* fixed-size ranges (2, 3, 5 or 10 BPM).
- **Put similar genres in the same folder:** for example, Tech House and Deep House go to "House". You can move any genre to another folder, create a new folder, and rename any folder (the pencil next to its name). The track's tag keeps the exact genre.
- The **preview** shows the folders that will be created and lists the tracks going to **Review**, with the reason for each (no genre, uncertain BPM or key).

Key folders use a leading zero (`01A`, `01B`, `02A`…), so they sort in Camelot wheel order in any program.

### 4. Copy
- **Copy music** creates the folders and the copies. A summary at the end confirms what was done.
- **Improve the audio** creates improved copies in the `Improved` subfolder of the destination (`Melhoradas` when the program is in Portuguese). You can choose only low-quality tracks, only tracks that clip, or all of them.

### Organizing again into the same destination
If you add music or change the options and organize again into the same destination, Mixteca does not duplicate anything: copies whose folder changed are **moved**, copies already in place are skipped, and only new tracks are copied. The same applies to the `Improved` folder.

## Information sources

With no setup, Mixteca uses **MusicBrainz** (track data) and the **Cover Art Archive** (cover art). Optional free keys improve the results:

| Service | What for | How to get it |
|---|---|---|
| Discogs | more detailed styles; identifies tracks MusicBrainz does not have | account at discogs.com → Settings → Developers → generate token |
| Last.fm | genres tagged by the community | account at last.fm → create an "API account" |
| AcoustID | recognizes a track by its sound, even with no name or tags | account at acoustid.org → register an application |

Keys are stored only on your computer. These services have their own terms and are free for noncommercial use only.

**Confidence levels.** What is found with high or medium confidence fills empty fields automatically. Weak guesses become suggestions for you to decide on. Replacing information that already existed always asks for your confirmation.

## Safety of your files

- Originals are never changed. New tags, covers and names go only to the copies.
- Nothing is overwritten or deleted in the destination. When reorganizing, the program only moves copies it created itself and removes folders left empty.
- Every copy is logged in `.organizador` inside the destination, along with its previous tags.
- The program runs only on your computer. The internet is used only to query the sources above, sending the track's title, artist and duration (and the audio fingerprint, if AcoustID is enabled).

## Limits

- The **key is an estimate**. It is usually right or lands on a neighbouring key on the Camelot wheel, but it can be wrong. Double-check the folders you use most.
- Remixes, bootlegs and recent releases may be missing from the open sources.
- Audio improvement does not recover what a low-quality MP3 already lost, and does not fix distortion baked into the file.
- With automatic BPM, folder names depend on the tracks you have and may change when you add music (copies are moved to follow).

## Where data is stored

Settings, keys and analyses live in `%APPDATA%\Mixteca`. Errors are logged to `mixteca.log` in that folder. Uninstalling the program does not delete it.

Advanced options, as files in that same folder:
- `user_preferences.json`: your own rules for genre names and extra words to strip from titles.
- `extras\*.py`: additional genre sources. Whoever adds one is responsible for respecting the terms of the service it queries, and should only place trusted files there.

## For developers

Requires Python 3.12+ and FFmpeg/FFprobe (in the `ferramentas/` folder or on PATH).

```
pip install -r requirements.txt
python iniciar.py
```

Tests:

```
python tests/test_basico.py
python tests/test_identificacao.py
python tests/e2e_identificacao_ui.py SCREENSHOT_DIR   # on-screen flow (needs Playwright)
```

The Windows package is built by `.github/workflows/build-windows.yml` (PyInstaller + Inno Setup). Third-party licenses are listed in `LICENCAS.md`. The code and its comments are written in Portuguese.

Layout: `organizador/analise.py` (BPM, key, quality) · `identificacao.py`, `decisao.py`, `casamento.py`, `classificador.py`, `provedores/` (metadata lookup and decisions) · `planejador.py` (folders and safe copying) · `escrita.py` (tags on copies) · `melhoria.py` (audio) · `servidor.py` + `web/index.html` (interface).

## License

**PolyForm Noncommercial License 1.0.0** (`LICENSE` file). You may use, study and modify the program for noncommercial purposes: personal use, hobby, research, teaching and non-profit organizations. **Selling the program, including it in a paid product or service, or using it commercially requires the author's permission.**

The program is provided as is, without warranty. Third-party components (FFmpeg, numpy, scipy and others) follow their own licenses.
