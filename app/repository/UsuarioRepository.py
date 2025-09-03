from sqlalchemy.orm import Session
from ..models.UsuarioModel import Usuario

class UsuarioRepository:
    def get_user_by_username(self, db: Session, username: str) -> Usuario | None:
        return db.query(Usuario).filter(Usuario.usuario == username).first()
    
user_repo = UsuarioRepository()