from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum
from .base import Base
import datetime
import enum

class TipoSituacaoProfissional(str, enum.Enum):
    Ativo = "Ativo"
    Inativo = "Inativo"
    De_Ferias = "De Ferias"
    Licenca = "Licenca"

class Profissional(Base):
    __tablename__ = "profissionais"
    codprofissional = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    telefone = Column(String(20), nullable=True)
    crm = Column(String(20), unique=True, nullable=False)
    especialidade = Column(String(100), nullable=False)
    situacao = Column(SQLAlchemyEnum(TipoSituacaoProfissional), nullable=False, default=TipoSituacaoProfissional.Ativo)
    data_criacao = Column(DateTime, default=datetime.datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.datetime.utcnow)