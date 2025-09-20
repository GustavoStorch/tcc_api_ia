from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    GOOGLE_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_INDEX_NAME: str = "clinica-index"
    GOOGLE_CALENDAR_ID: str 
    GOOGLE_SERVICE_ACCOUNT_FILE: str = "service-account.json"

    class Config:
        env_file = ".env"

settings = Settings()