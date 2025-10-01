from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, BackgroundTasks, File
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.api.deps import get_current_user
from app.models import UsuarioModel
from app.services import TreinamentoService
from app.services.PredicaoService import prediction_service
from app.dto.PredicaoDTO import PredictionFeatures, PredictionResponse

router = APIRouter()

# Define rota que cria o treinamento do modelo (Deixei semi preparado para caso um dia vamos subir arquivos csv por exemplo 
# para realizar o treinamento)
@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def upload_arquivo_treinamento(
    background_tasks: BackgroundTasks,
    current_user: UsuarioModel.Usuario = Depends(get_current_user),
):
    # Validação de permissão: Apenas Admins podem treinar o modelo
    if current_user.funcao.value != "Admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem iniciar o treinamento de modelos.",
        )

    # Realiza o treinamento em segundo plano
    background_tasks.add_task(
        TreinamentoService.processar_e_treinar_modelo
    )

    print(f"Tarefa de treinamento iniciada em background.")

    return {
        "message": "Arquivo recebido. O processo de treinamento foi iniciado em segundo plano."
    }

# Define rota que realiza a predição de no-show do paciente/agendamento
@router.post("/predict", status_code=status.HTTP_202_ACCEPTED, response_model=PredictionResponse)
def predict_no_show(
    features: PredictionFeatures,
    current_user: UsuarioModel.Usuario = Depends(get_current_user)
):
    try:
        result = prediction_service.predict(features)
        return result
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro inesperado: {str(e)}")