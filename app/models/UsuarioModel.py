from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum
from .base import Base
import datetime
import enum

class TipoFuncaoUsuario(str, enum.Enum):
    Admin = "Admin"
    Doutor = "Doutor"
    Secretaria = "Secretaria"

class TipoSituacaoUsuario(str, enum.Enum):
    Ativo = "Ativo"
    Inativo = "Inativo"

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    usuario = Column(String(50), unique=True, nullable=False)
    senha = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    telefone = Column(String(20), nullable=True) 
    funcao = Column(SQLAlchemyEnum(TipoFuncaoUsuario), nullable=False)
    situacao = Column(SQLAlchemyEnum(TipoSituacaoUsuario), nullable=False, default=TipoSituacaoUsuario.Ativo)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.datetime.utcnow)