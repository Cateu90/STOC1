import os
from data.db import get_db
from pathlib import Path

def executar_sqls_iniciais(sql_dir="sql", user_email=None):
    # Get the absolute path to the sql directory relative to the project root
    if not os.path.isabs(sql_dir):
        # Get the directory where this script is located
        current_dir = Path(__file__).parent
        # Go up one level to the project root and then to the sql directory
        sql_dir = current_dir.parent / sql_dir
    
    # Convert to string for os operations
    sql_dir = str(sql_dir)
    
    # Check if the sql directory exists
    if not os.path.exists(sql_dir):
        print(f"[SQL INIT] Diretório SQL não encontrado: {sql_dir}")
        return
    
    db = get_db(user_email=user_email)
    cursor = db.cursor()
    
    for filename in sorted(os.listdir(sql_dir)):
        if filename.endswith(".sql"):
            path = os.path.join(sql_dir, filename)
            
            try:
                with open(path, encoding="utf-8") as f:
                    sql_content = f.read()
                
                # Detectar se o arquivo contém comandos preparados (PREPARE/EXECUTE/DEALLOCATE)
                if 'PREPARE' in sql_content.upper() and 'EXECUTE' in sql_content.upper():
                    # Para arquivos com comandos preparados, executar como um bloco único
                    try:
                        for result in cursor.execute(sql_content, multi=True):
                            if result.with_rows:
                                # Consumir todos os resultados para evitar "Unread result found"
                                rows = result.fetchall()
                        db.commit()
                        print(f"[SQL INIT] Executado com sucesso: {filename}")
                    except Exception as e:
                        print(f"[SQL INIT] Erro ao executar {filename}: {e}")
                        db.rollback()
                else:
                    # Para arquivos SQL normais, dividir por statement
                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                    
                    for statement in statements:
                        try:
                            cursor.execute(statement)
                            # Consumir resultados se houver
                            if cursor.with_rows:
                                cursor.fetchall()
                        except Exception as e:
                            print(f"[SQL INIT] Erro ao executar {filename}: {e}")
                            break
                    else:
                        # Se todos os statements foram executados sem erro
                        db.commit()
                        print(f"[SQL INIT] Executado com sucesso: {filename}")
                        
            except Exception as e:
                print(f"[SQL INIT] Erro ao ler arquivo {filename}: {e}")
    
    cursor.close()
    
    # Adicionar usuário PDV
    try:
        cursor = db.cursor()
        
        # Verificar se o usuário PDV já existe
        cursor.execute("SELECT id FROM users WHERE name = %s", ("PDV",))
        if cursor.fetchone():
            print("Usuário PDV já existe.")
        else:
            from util.auth import hash_password
            hashed_password = hash_password("pdv")
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)", ("PDV", "pdv@system.com", hashed_password, "garcom"))
            db.commit()
            print(f"Usuário PDV criado no banco de dados.")
            
    except Exception as err:
        print(f"Erro ao criar/verificar usuário PDV: {err}")
        db.rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'db' in locals() and db.is_connected():
            db.close()
