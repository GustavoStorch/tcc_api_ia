import enum
from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    DateTime, 
    BigInteger,
    Enum as SQLAlchemyEnum
)
from sqlalchemy.sql import func
from .base import Base

class TipoSituacaoPaciente(str, enum.Enum):
    Ativo = "Ativo"
    Inativo = "Inativo"
    Arquivado = "Arquivado"

class Paciente(Base):
    __tablename__ = 'pacientes'
    codpaciente = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    telefone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True, unique=True)
    telegram_chat_id = Column(BigInteger, nullable=True, unique=True)
    cep = Column(String(9), nullable=True)
    rua = Column(String(150), nullable=True)
    numero = Column(String(10), nullable=True)
    complemento = Column(String(100), nullable=True)
    bairro = Column(String(100), nullable=True)
    cidade = Column(String(100), nullable=True)
    estado = Column(String(50), nullable=True)
    situacao = Column(
        SQLAlchemyEnum(TipoSituacaoPaciente, name="tipo_situacao_paciente"), 
        nullable=False, 
        default=TipoSituacaoPaciente.Ativo
    )
    data_criacao = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        nullable=False
    )
    data_atualizacao = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )