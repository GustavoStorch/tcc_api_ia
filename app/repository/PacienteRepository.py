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

paciente_repo = PacienteRepository()
