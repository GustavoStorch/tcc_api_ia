import sys
import os

# Garante que o python encontre a pasta 'app' se houver problemas de path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.PredicaoService import PredictionService
from app.dto.PredicaoDTO import PredictionFeatures

def executar_teste():
    try:
        service = PredictionService()
    except Exception as e:
        print(f"ERRO CRÍTICO: Não foi possível iniciar o serviço. Verifique os arquivos .pkl. Detalhes: {e}")
        return

    # "Paciente Problema"
    try:
        features_ruim = PredictionFeatures(
            antecedencia_dias=30,
            dia_da_semana=4,
            mes=12,
            hora_do_dia=18,
            historico_no_shows=5,
            historico_agendamentos=6,
            taxa_no_show=0.83
        )
        resultado_ruim = service.predict(features_ruim)
        print(f"\n[TESTE 1] Paciente Alto Risco:")
        print(f"   -> Resultado: {resultado_ruim}")
    except Exception as e:
        print(f"Erro no Teste 1: {e}")

    # "Paciente Exemplar"
    try:
        features_bom = PredictionFeatures(
            antecedencia_dias=1,
            dia_da_semana=1,
            mes=3,
            hora_do_dia=9,
            historico_no_shows=0,
            historico_agendamentos=10,
            taxa_no_show=0.0
        )
        resultado_bom = service.predict(features_bom)
        print(f"\n[TESTE 2] Paciente Baixo Risco:")
        print(f"   -> Resultado: {resultado_bom}")
    except Exception as e:
        print(f"Erro no Teste 2: {e}")

    print("\n--- FIM DO TESTE ---")

if __name__ == "__main__":
    executar_teste()