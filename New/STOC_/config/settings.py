import os
from typing import Optional
from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    host: str = os.getenv("DB_HOST", "localhost")
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "")
    port: int = int(os.getenv("DB_PORT", "3306"))
    charset: str = "utf8mb4"
    
    def get_database_name(self, user_email: str = None) -> str:
        if user_email:
            return f"stoc_{user_email.split('@')[0].replace('.', '_')}"
        return os.getenv("DB_NAME", "stoc")


class AppSettings(BaseModel):
    """Configurações gerais da aplicação."""
    title: str = "STOC - Sistema de Comandas"
    description: str = "Sistema de gerenciamento de comandas para restaurantes"
    version: str = "2.0.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # Servidor
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # Sessão
    secret_key: str = os.getenv("SECRET_KEY", "stoc-secret-key")
    session_expire_hours: int = int(os.getenv("SESSION_EXPIRE_HOURS", "24"))


class Settings:
    """Configurações centralizadas do sistema."""
    
    def __init__(self):
        self.app = AppSettings()
        self.database = DatabaseSettings()
        
        # Validar configurações em produção
        if self.app.environment == "production":
            self._validate_production_config()
    
    def _validate_production_config(self):
        """Valida configurações para ambiente de produção."""
        errors = []
        
        if self.app.secret_key == "stoc-secret-key":
            errors.append("SECRET_KEY deve ser alterada em produção")
        
        if self.database.password == "":
            errors.append("DB_PASSWORD deve ser definida em produção")
        
        if self.app.debug:
            errors.append("DEBUG deve ser False em produção")
        
        if errors:
            raise ValueError(f"Configurações inválidas para produção: {'; '.join(errors)}")
    
    @property
    def is_development(self) -> bool:
        """Verifica se está em ambiente de desenvolvimento."""
        return self.app.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Verifica se está em ambiente de produção."""
        return self.app.environment == "production"


# Instância global das configurações
settings = Settings()
