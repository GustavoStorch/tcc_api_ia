from pydantic import BaseModel

class PredictionFeatures(BaseModel):
    antecedencia_dias: int
    idade: int
    dia_da_semana: int
    mes: int
    hora_do_dia: int
    historico_no_shows: int
    historico_agendamentos: int
    taxa_no_show: float

class PredictionResponse(BaseModel):
    probabilidade_no_show: float
    risco: str