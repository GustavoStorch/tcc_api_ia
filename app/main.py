from fastapi import FastAPI
from app.api.controller import AgendamentoController, AuthController, ChatController, SinconizacaoController, UsuarioController

app = FastAPI(
    title="API da Clínica Médica",
    description="API para gerir agendamentos, pacientes e a integração com o chatbot.",
    version="1.0.0"
)

# Configuração das rotas
app.include_router(AuthController.router, prefix="/auth", tags=["Autenticação"])
app.include_router(UsuarioController.router, prefix="/users", tags=["Utilizadores"]) 
app.include_router(SinconizacaoController.router, prefix="/sync", tags=["Sincronização"]) 
app.include_router(ChatController.router, prefix="/chat", tags=["Chat"])
app.include_router(AgendamentoController.router, prefix="/agendamentos", tags=["Agendamentos"])

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Bem-vindo à API da Clínica Médica!"}