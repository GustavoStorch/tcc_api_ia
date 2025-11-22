from sqlalchemy.orm import Session
from ..models import PacienteModel

class PacienteRepository:
    def get_by_telegram_id(self, db: Session, telegram_id: int) -> PacienteModel.Paciente | None:
        return db.query(PacienteModel.Paciente).filter(PacienteModel.Paciente.telegram_chat_id == telegram_id).first()

    def update_refresh_token(self, db: Session, paciente: PacienteModel.Paciente, token: str) -> PacienteModel.Paciente:
        paciente.token = token
        db.commit()
        db.refresh(paciente)
        return paciente
    
    def update_fuso_horario(self, db: Session, paciente: PacienteModel.Paciente, fuso_horario: str) -> PacienteModel.Paciente:
        paciente.fuso_horario = fuso_horario
        paciente.alteracao_pendente = True
        db.commit()
        db.refresh(paciente)
        return paciente
    
    def create_pacient(self, db: Session, telegram_id: int, nome: str | None) -> PacienteModel.Paciente:
        novo_paciente = PacienteModel.Paciente(
            telegram_chat_id=telegram_id,
            nome=nome,
            cpf=f"Tmp{telegram_id}",    
            telefone="00000000",
            situacao=PacienteModel.TipoSituacaoPaciente.Ativo
        )
        
        db.add(novo_paciente)
        db.commit()
        db.refresh(novo_paciente)
        return novo_paciente

paciente_repo = PacienteRepository()
