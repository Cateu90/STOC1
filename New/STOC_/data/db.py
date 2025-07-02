import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def ensure_database_exists():
    db_name = os.getenv("DB_NAME", "stoc")
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar banco de dados: {e}")

ensure_database_exists()

def get_db(user_email=None, db_name=None):
    if not db_name:
        if user_email:
            db_name = f"stoc_{user_email.split('@')[0].replace('.', '_').replace('-', '_')}"
        else:
            db_name = os.getenv("DB_NAME", "stoc")
            
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=db_name
    )

def ensure_user_database_exists(user_email):
    db_name = f"stoc_{user_email.split('@')[0].replace('.', '_').replace('-', '_')}"
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar banco de dados do usuário {db_name}: {e}")

def get_all_user_dbs():
    dbs = []
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", "")
        )
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'stoc_%'")
        for (db_name,) in cursor:
            dbs.append(db_name)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao listar bancos de dados de usuários: {e}")
    return dbs
