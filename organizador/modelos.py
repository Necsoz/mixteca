"""Modelo de dados de uma música analisada."""
from dataclasses import asdict, dataclass, field, fields
from typing import Optional


@dataclass
class Faixa:
    caminho: str
    titulo: str = ""
    artista: str = ""
    album: str = ""
    genero: str = ""
    genero_manual: bool = False
    duracao: float = 0.0
    bitrate_kbps: Optional[int] = None
    codec: str = ""
    bpm: Optional[int] = None
    bpm_conf: float = 0.0
    bpm_fora_da_faixa: bool = False
    tom_pc: Optional[int] = None
    tom_menor: Optional[bool] = None
    tom_conf: float = 0.0
    camelot: Optional[str] = None
    corte_hz: Optional[float] = None
    pico_db: Optional[float] = None
    rms_db: Optional[float] = None
    clip_pct: Optional[float] = None
    qualidade_baixa: bool = False
    erro: Optional[str] = None
    ano: str = ""
    tem_capa: bool = False
    genero_fonte: str = ""          # de onde veio o gênero: tag, manual, MusicBrainz, som...
    vetor: list = field(default_factory=list)   # impressão da sonoridade (usada na classificação por som)
    ajustes: dict = field(default_factory=dict)  # metadados aceitos pelo usuário (só vão para as CÓPIAS)

    def para_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def de_dict(d: dict) -> "Faixa":
        nomes = {f.name for f in fields(Faixa)}
        return Faixa(**{k: v for k, v in d.items() if k in nomes})
