import enum
from sqlalchemy import (
    Column, 
    Integer, 
    String, 
    DateTime, 
    Enum as SQLAlchemyEnum
)
from sqlalchemy.sql import func
from .base import Base

class TipoSituacaoClinica(str, enum.Enum):
    Ativa = "Ativa"
    Inativa = "Inativa"

class Clinica(Base):
    __tablename__ = 'clinicas'
    codclinica = Column(Integer, primary_key=True)
    nome_fantasia = Column(String(150), nullable=True)
    cnpj = Column(String(18), nullable=False, unique=True)
    email = Column(String(100), nullable=False, unique=True)
    telefone = Column(String(20), nullable=True)
    cep = Column(String(9), nullable=True)
    pais = Column(String(50), nullable=False)
    estado = Column(String(50), nullable=False)
    cidade = Column(String(100), nullable=False)
    bairro = Column(String(100), nullable=False)
    rua = Column(String(150), nullable=False)
    numero = Column(String(10), nullable=False)
    complemento = Column(String(100), nullable=True)
    situacao = Column(
        SQLAlchemyEnum(TipoSituacaoClinica, name="tipo_situacao_clinica"), 
        nullable=False, 
        default=TipoSituacaoClinica.Ativa
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