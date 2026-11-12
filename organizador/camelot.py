"""Notação Camelot e compatibilidade harmônica."""

NOTAS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def camelot(pitch_class: int, menor: bool) -> str:
    """Converte (nota 0-11, modo) em código Camelot. Ex.: A menor -> 8A, C maior -> 8B."""
    if menor:
        maior_relativo = (pitch_class + 3) % 12
        letra = "A"
    else:
        maior_relativo = pitch_class % 12
        letra = "B"
    quintas = (maior_relativo * 7) % 12  # C=0, G=1, D=2, ...
    numero = (quintas + 7) % 12 + 1  # C maior = 8B
    return f"{numero}{letra}"


def nome_tom(pitch_class: int, menor: bool) -> str:
    return f"{NOTAS[pitch_class % 12]} {'menor' if menor else 'maior'}"


def compativeis(codigo: str) -> list[str]:
    """Códigos que combinam com o informado: o próprio, +1, -1 e o par A/B do mesmo número."""
    numero, letra = int(codigo[:-1]), codigo[-1]

    def volta(n: int) -> int:
        return (n - 1) % 12 + 1

    outra = "B" if letra == "A" else "A"
    return [codigo, f"{volta(numero - 1)}{letra}", f"{volta(numero + 1)}{letra}", f"{numero}{outra}"]
