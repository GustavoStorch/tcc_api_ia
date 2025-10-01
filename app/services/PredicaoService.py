import joblib
import pandas as pd
from fastapi import HTTPException

from ..dto.PredicaoDTO import PredictionFeatures

class PredictionService:
    def __init__(self):
        # Carregamento do modelo e colunas treinado.
        try:
            self.model = joblib.load("no_show_model.pkl")
            self.model_columns = joblib.load("model_columns.pkl")
            print("Serviço de Predição: Modelo carregado com sucesso!")
        except FileNotFoundError:
            self.model = None
            self.model_columns = None
            print("ERRO no Serviço de Predição: Ficheiros do modelo não encontrados.")

    def predict(self, features: PredictionFeatures) -> dict:
        # Aqui se realiza a predição de no-show om base nas features que fornecemos
        if not self.model or not self.model_columns:
            raise HTTPException(status_code=500, detail="Modelo de IA não está carregado.")

        try:
            # Converte os dados de entrada para o formato que o modelo espera (DataFrame)
            input_data = pd.DataFrame([features.dict()], columns=self.model_columns)

            # Realiza a predição de probabilidade
            probability = self.model.predict_proba(input_data)[0][1]

            return {
                "probabilidade_no_show": float(probability),
                "risco": "Alto" if probability > 0.7 else "Médio" if probability > 0.4 else "Baixo"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao realizar a predição: {e}")

prediction_service = PredictionService()        
