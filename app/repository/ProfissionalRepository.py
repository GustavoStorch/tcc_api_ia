from sqlalchemy.orm import Session
from ..models.ProfissionalModel import Profissional

class ProfissionalRepository:
    def get_profissional_by_name(self, db: Session, nome: str) -> Profissional | None:
        return db.query(Profissional).filter(Profissional.nome.ilike(f"%{nome}%")).first()

profissional_repo = ProfissionalRepository() 