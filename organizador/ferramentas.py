"""Localiza FFmpeg/FFprobe, roda comandos sem abrir janela e define a pasta de dados do app."""
import functools
import os
import shutil
import subprocess
import sys
from pathlib import Path


def pasta_app() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


@functools.lru_cache(maxsize=None)
def achar(nome: str) -> str:
    exe = nome + (".exe" if os.name == "nt" else "")
    for pasta in (pasta_app() / "ferramentas", pasta_app()):
        candidato = pasta / exe
        if candidato.is_file():
            return str(candidato)
    achado = shutil.which(nome)
    if achado:
        return achado
    raise FileNotFoundError(f"Não encontrei o {nome}. Ele deve ficar na pasta 'ferramentas' do programa.")


def executar(cmd: list[str]) -> subprocess.CompletedProcess:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    return subprocess.run(cmd, capture_output=True, creationflags=flags)


def pasta_dados() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    pasta = Path(base or Path.home()) / "OrganizadorMusical"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def escolher_pasta(titulo: str) -> str | None:
    """Abre o seletor de pastas do Windows. Em outros sistemas devolve None (o usuário cola o caminho)."""
    if os.name != "nt":
        return None
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$o=New-Object System.Windows.Forms.Form;$o.TopMost=$true;$o.ShowInTaskbar=$false;$o.Opacity=0;"
        "$o.StartPosition='CenterScreen';$o.Show();$o.Activate();"
        "$f=New-Object System.Windows.Forms.FolderBrowserDialog;"
        f"$f.Description='{titulo.replace(chr(39), '')}';"
        "if($f.ShowDialog($o) -eq 'OK'){[Console]::Out.Write($f.SelectedPath)};$o.Close()"
    )
    r = executar(["powershell", "-NoProfile", "-STA", "-Command", script])
    return r.stdout.decode("utf-8", errors="ignore").strip() or None
