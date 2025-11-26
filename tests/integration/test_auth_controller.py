from app.core.security import get_password_hash
from app.models.UsuarioModel import Usuario, TipoFuncaoUsuario, TipoSituacaoUsuario

def test_login_successful(client, db_session):
    password_raw = "minha_senha_forte"
    username = "usuario_teste"
    
    usuario = Usuario(
        usuario=username,
        senha=get_password_hash(password_raw), 
        nome="Usuario Teste",
        email="teste@exemplo.com",
        telefone="4799999999", 
        funcao=TipoFuncaoUsuario.Admin, 
        situacao=TipoSituacaoUsuario.Ativo
    )
    db_session.add(usuario)
    db_session.commit()

    response = client.post(
        "/auth/login", 
        data={
            "username": username,
            "password": password_raw
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_incorrect_password(client, db_session):
    username = "usuario_erro"
    password_correto = "123456"
    
    usuario = Usuario(
        usuario=username,
        senha=get_password_hash(password_correto),
        nome="Usuario Erro",
        email="erro@exemplo.com",
        telefone="4788888888",
        funcao=TipoFuncaoUsuario.Admin,
        situacao=TipoSituacaoUsuario.Ativo
    )
    db_session.add(usuario)
    db_session.commit()

    response = client.post(
        "/auth/login",
        data={
            "username": username,
            "password": "senha_errada_aqui"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha incorretos"

def test_login_user_not_found(client):
    response = client.post(
        "/auth/login",
        data={
            "username": "fantasma",
            "password": "123"
        }
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário ou senha incorretos"