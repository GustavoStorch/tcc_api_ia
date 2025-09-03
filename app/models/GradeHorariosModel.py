
from sqlalchemy import Column, Integer, Enum as SQLAlchemyEnum, ForeignKey, Time
from .base import Base
import enum

class DiaDaSemanaEnum(str, enum.Enum):
    Domingo = "Domingo"
    Segunda = "Segunda"
    Terca = "Terca"
    Quarta = "Quarta"
    Quinta = "Quinta"
    Sexta = "Sexta"
    Sabado = "Sabado"

class GradeHorarios(Base):
    __tablename__ = 'grade_horarios'
    codhorario = Column(Integer, primary_key=True)
    codprofissional = Column(Integer, ForeignKey('profissionais.codprofissional'))
    dia = Column(SQLAlchemyEnum(DiaDaSemanaEnum, name="dia_da_semana_enum"), nullable=False)
    horainciomanha = Column(Time, nullable=False)
    horafimmanha = Column(Time, nullable=False)
    horainciotarde = Column(Time, nullable=False)
    horafimtarde = Column(Time, nullable=False)
    horaincionoite = Column(Time, nullable=False)
    horafimnoite = Column(Time, nullable=False)