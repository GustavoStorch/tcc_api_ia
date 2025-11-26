from sqlalchemy import (
    Column, 
    Integer, 
    Numeric, 
    DateTime, 
    ForeignKey,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class ValorConsulta(Base):
    __tablename__ = 'valores_consulta'
    codvalorconsulta = Column(Integer, primary_key=True)
    codprofissional = Column(Integer, ForeignKey('profissionais.codprofissional', ondelete="CASCADE"), nullable=False)
    codtipoconsulta = Column(Integer, ForeignKey('tipos_consulta.codtipoconsulta', ondelete="RESTRICT"), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
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

    profissional = relationship("Profissional")
    tipo_consulta = relationship("TipoConsulta")

    __table_args__ = (
        UniqueConstraint('codprofissional', 'codtipoconsulta', name='uq_profissional_tipoconsulta'),
    )