import pytest
from app.services.PredicaoService import PredictionService
from app.dto.PredicaoDTO import PredictionFeatures

@pytest.fixture(scope="module")
def predicao_service():
    return PredictionService()

def test_predicao_paciente_alto_risco(predicao_service):
    features_ruim = PredictionFeatures(
        antecedencia_dias=30,
        dia_da_semana=4,
        mes=12,
        hora_do_dia=18,
        historico_no_shows=5,
        historico_agendamentos=6,
        taxa_no_show=0.83
    )
    
    resultado = predicao_service.predict(features_ruim)
    
    assert resultado is not None
    print(f"\n[INFO] Resultado Alto Risco: {resultado}")

def test_predicao_paciente_baixo_risco(predicao_service):
    features_bom = PredictionFeatures(
        antecedencia_dias=1,
        dia_da_semana=1,
        mes=3,
        hora_do_dia=9,
        historico_no_shows=0,
        historico_agendamentos=10,
        taxa_no_show=0.0
    )
    
    resultado = predicao_service.predict(features_bom)
    
    assert resultado is not None
    print(f"\n[INFO] Resultado Baixo Risco: {resultado}")