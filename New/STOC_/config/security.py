import os
from typing import List

def get_cors_origins() -> List[str]:
    if os.getenv("ENVIRONMENT") == "development":
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://192.168.1.100:3000", 
            "http://192.168.1.101:3000",  
        ]
    elif os.getenv("ENVIRONMENT") == "production":
        return [
            "https://stoc.suaempresa.com",
            "https://app.stoc.suaempresa.com"
        ]
    else:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

class SecuritySettings:
    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "stoc-jwt-secret-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = 30
    BCRYPT_ROUNDS = 12
    
    @classmethod
    def validate_config(cls):
        if cls.JWT_SECRET_KEY == "stoc-jwt-secret-change-in-production":
            if os.getenv("ENVIRONMENT") == "production":
                raise ValueError("JWT_SECRET must be changed in production!")
            print("⚠️  WARNING: Using default JWT secret in development")
