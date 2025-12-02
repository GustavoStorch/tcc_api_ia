import pytest
from datetime import time
from app.main import app
from app.api.deps import get_current_user
from app.models import (
    UsuarioModel, 
    PacienteModel, 
    ProfissionalModel, 
    ClinicaModel, 
    TipoConsultaModel, 
    ValorConsultaModel,
    GradeHorariosModel 
)

def mock_get_current_user():
    return UsuarioModel.Usuario(
        id=1, 
        usuario="admin_teste", 
        funcao=UsuarioModel.TipoFuncaoUsuario.Admin, 
        situacao=UsuarioModel.TipoSituacaoUsuario.Ativo
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

def setup_dados_agendamento(db):
    clinica = ClinicaModel.Clinica(
        nome_fantasia="Clínica Teste",
        cnpj="00.000.000/0001-00",
        email="clinica@teste.com",
        pais="Brasil",
        estado="SC",
        cidade="Jaraguá do Sul",
        bairro="Centro",
        rua="Rua Teste",
        numero="100",
        situacao=ClinicaModel.TipoSituacaoClinica.Ativa
    )
    db.add(clinica)
    db.commit()
    
    profissional = ProfissionalModel.Profissional(
        nome="Dr. Teste", 
        crm="12345-SC",
        especialidade="Psicologia",
        situacao=ProfissionalModel.TipoSituacaoProfissional.Ativo
    )
    db.add(profissional)
    
    paciente = PacienteModel.Paciente(
        nome="Paciente Teste", 
        cpf="123.456.789-00",
        telefone="4799999999",
        situacao=PacienteModel.TipoSituacaoPaciente.Ativo
    )
    db.add(paciente)

    tipo_consulta = TipoConsultaModel.TipoConsulta(
        nome="Consulta Rotina",
        duracao_padrao_minutos=60
    )
    db.add(tipo_consulta)

    db.commit() 

    valor_consulta = ValorConsultaModel.ValorConsulta(
        codprofissional=profissional.codprofissional,
        codtipoconsulta=tipo_consulta.codtipoconsulta,
        valor=150.00
    )
    db.add(valor_consulta)

    grade = GradeHorariosModel.GradeHorarios(
        codprofissional=profissional.codprofissional,
        dia="Quinta", 
        horainciomanha=time(8, 0),
        horafimmanha=time(12, 0),
        horainciotarde=time(13, 0),
        horafimtarde=time(18, 0),
        horaincionoite=time(19, 0),
        horafimnoite=time(22, 0) 
    )
    db.add(grade)

    db.commit()
    
    return {
        "clinica": clinica,
        "profissional": profissional,
        "paciente": paciente,
        "tipo_consulta": tipo_consulta
    }

def test_criar_agendamento_sucesso(client, db_session):
    dados = setup_dados_agendamento(db_session)
    horario_iso = "2025-12-25T14:00:00"

    response = client.post(
        "/agendamentos/", 
        data={
            "nomepaciente": dados["paciente"].nome,
            "nomeprofissional": dados["profissional"].nome,
            "nometipoconsulta": dados["tipo_consulta"].nome,
            "codclinica": dados["clinica"].codclinica,
            "horario_inicio": horario_iso
        }
    )
    
    if response.status_code != 201:
        print(f"\nERRO RETORNADO PELA API: {response.json()}")

    assert response.status_code == 201
    data = response.json()
    
    assert "codagendamento" in data
    assert data["codpaciente"] == dados["paciente"].codpaciente
    assert data["codprofissional"] == dados["profissional"].codprofissional

def test_criar_agendamento_profissional_nao_encontrado(client, db_session):
    dados = setup_dados_agendamento(db_session)
    
    response = client.post(
        "/agendamentos/", 
        data={
            "nomepaciente": dados["paciente"].nome,
            "nomeprofissional": "Dr. Fantasma", 
            "nometipoconsulta": dados["tipo_consulta"].nome,
            "codclinica": dados["clinica"].codclinica,
            "horario_inicio": "2025-12-25T15:00:00"
        }
    )

    assert response.status_code == 404

def test_criar_agendamento_paciente_nao_encontrado(client, db_session):
    dados = setup_dados_agendamento(db_session)
    
    response = client.post(
        "/agendamentos/", 
        data={
            "nomepaciente": "Paciente Inexistente",
            "nomeprofissional": dados["profissional"].nome,
            "nometipoconsulta": dados["tipo_consulta"].nome,
            "codclinica": dados["clinica"].codclinica,
            "horario_inicio": "2025-12-25T16:00:00"
        }
    )

    assert response.status_code == 404