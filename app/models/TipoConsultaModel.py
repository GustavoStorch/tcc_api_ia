from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .base import Base

class TipoConsulta(Base):
    __tablename__ = 'tipos_consulta'

    codtipoconsulta = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text, nullable=True)
    duracao_padrao_minutos = Column(Integer, nullable=False)
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