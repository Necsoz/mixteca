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
    pasta = Path(base or Path.home()) / "Mixteca"
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


_CS_DIALOGO = r"""
using System;
using System.Runtime.InteropServices;
public class SeletorDePasta {
    [ComImport, Guid("DC1C5A9C-E88A-4dde-A5A1-60F82A20AEF7")] class FileOpenDialog { }
    [ComImport, Guid("42f85136-db7e-439c-85f1-e4075d135fc8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IFileDialog {
        [PreserveSig] int Show(IntPtr dono);
        void SetFileTypes(); void SetFileTypeIndex(); void GetFileTypeIndex(); void Advise(); void Unadvise();
        void SetOptions(uint opcoes); void GetOptions(out uint opcoes);
        void SetDefaultFolder(); void SetFolder(); void GetFolder(); void GetCurrentSelection();
        void SetFileName(); void GetFileName();
        void SetTitle([MarshalAs(UnmanagedType.LPWStr)] string titulo);
        void SetOkButtonLabel(); void SetFileNameLabel();
        void GetResult(out IShellItem item);
    }
    [ComImport, Guid("43826D1E-E718-42EE-BC55-A1E261C37BFE"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IShellItem {
        void BindToHandler(); void GetParent();
        void GetDisplayName(uint tipo, [MarshalAs(UnmanagedType.LPWStr)] out string nome);
    }
    public static string Escolher(string titulo, IntPtr dono) {
        IFileDialog d = (IFileDialog)new FileOpenDialog();
        uint o; d.GetOptions(out o);
        d.SetOptions(o | 0x20 | 0x40);   // escolher PASTAS, só do sistema de arquivos
        d.SetTitle(titulo);
        if (d.Show(dono) != 0) return "";
        IShellItem item; d.GetResult(out item);
        string caminho; item.GetDisplayName(0x80058000, out caminho);
        return caminho;
    }
}
"""


def escolher_pasta(titulo: str) -> str | None:
    """Abre o seletor de pastas no estilo do Explorador de Arquivos (com barra de endereço, atalhos e busca).
    Se o Windows não aceitar, cai para o seletor antigo (árvore). Em outros sistemas devolve None."""
    if os.name != "nt":
        return None
    import base64
    titulo = titulo.replace("'", "").replace("\n", " ")
    script = (
        "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$o=New-Object System.Windows.Forms.Form;$o.TopMost=$true;$o.ShowInTaskbar=$false;$o.Opacity=0;"
        "$o.StartPosition='CenterScreen';$o.Show();$o.Activate();"
        "$p='';"
        "try{Add-Type -TypeDefinition @'\n" + _CS_DIALOGO + "\n'@;"
        f"$p=[SeletorDePasta]::Escolher('{titulo}',$o.Handle)}}"
        "catch{$f=New-Object System.Windows.Forms.FolderBrowserDialog;"
        f"$f.Description='{titulo}';"
        "if($f.ShowDialog($o) -eq 'OK'){$p=$f.SelectedPath}};"
        "[Console]::Out.Write($p);$o.Close()"
    )
    codificado = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    r = executar(["powershell", "-NoProfile", "-STA", "-EncodedCommand", codificado])
    return r.stdout.decode("utf-8", errors="ignore").strip() or None
