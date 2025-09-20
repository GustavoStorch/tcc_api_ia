from sqlalchemy import Column, Integer, DateTime, Enum as SQLAlchemyEnum, ForeignKey, Numeric
from .base import Base
from sqlalchemy.orm import relationship 
from .ClinicaModel import Clinica
from .PacienteModel import Paciente
from .ProfissionalModel import Profissional
from .TipoConsultaModel import TipoConsulta
import enum

class TipoSituacaoAgendamento(str, enum.Enum):
    Agendado = "Agendado"
    Confirmado = "Confirmado"
    Concluido = "Concluido"
    Cancelado_Pelo_Paciente = "Cancelado Pelo Paciente"
    Cancelado_Pela_Clinica = "Cancelado Pela Clinica"
    Nao_Compareceu = "Nao Compareceu"

class Agendamento(Base):
    __tablename__ = 'agendamentos'
    codagendamento = Column(Integer, primary_key=True)
    codpaciente = Column(Integer, ForeignKey('pacientes.codpaciente'))
    codprofissional = Column(Integer, ForeignKey('profissionais.codprofissional'))
    codtipoconsulta = Column(Integer, ForeignKey('tipos_consulta.codtipoconsulta'))
    codclinica = Column(Integer, ForeignKey('clinicas.codclinica'))
    horario_inicio = Column(DateTime(timezone=True), nullable=False)
    horario_fim = Column(DateTime(timezone=True), nullable=False)
    valor_cobrado = Column(Numeric(10, 2), nullable=False)
    situacao = Column(SQLAlchemyEnum(TipoSituacaoAgendamento, name="tipo_situacao_agendamento"), nullable=False, default=TipoSituacaoAgendamento.Agendado)

    clinica = relationship("Clinica")
    paciente = relationship("Paciente")
    profissional = relationship("Profissional")
    tipoConsulta = relationship("TipoConsulta")
    