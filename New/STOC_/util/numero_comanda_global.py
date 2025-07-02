# util/numero_comanda_global.py
from data.db import get_db
import threading
import time

# Lock para garantir atomicidade na geração de números
numero_lock = threading.Lock()

def get_proximo_numero_comanda():
    """
    Gera próximo número sequencial global para comandas.
    Usa o banco principal (sem user_email) para controlar a sequência.
    """
    with numero_lock:
        # Conectar ao banco principal (global)
        db = get_db(user_email=None)
        cursor = db.cursor(dictionary=True)
        
        try:
            # Garantir que a tabela de controle de números existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS controle_numeros (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    tipo VARCHAR(50) NOT NULL UNIQUE,
                    ultimo_numero INT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Buscar último número usado para comandas
            cursor.execute("""
                SELECT ultimo_numero FROM controle_numeros 
                WHERE tipo = 'comanda' 
                FOR UPDATE
            """)
            
            result = cursor.fetchone()
            
            if result:
                # Incrementar número existente
                proximo_numero = result['ultimo_numero'] + 1
                cursor.execute("""
                    UPDATE controle_numeros 
                    SET ultimo_numero = %s 
                    WHERE tipo = 'comanda'
                """, (proximo_numero,))
            else:
                # Primeiro número da sequência
                proximo_numero = 1
                cursor.execute("""
                    INSERT INTO controle_numeros (tipo, ultimo_numero) 
                    VALUES ('comanda', %s)
                """, (proximo_numero,))
            
            db.commit()
            
            print(f"[INFO] Próximo número de comanda gerado: {proximo_numero}")
            return proximo_numero
            
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Erro ao gerar número da comanda: {e}")
            # Fallback: usar timestamp como número único
            import time
            return int(time.time() * 1000) % 999999
            
        finally:
            cursor.close()
            db.close()


def resetar_numeracao_comandas():
    """
    CUIDADO: Reseta a numeração de comandas para 0.
    Use apenas para testes ou início de operação.
    """
    with numero_lock:
        db = get_db(user_email=None)
        cursor = db.cursor()
        
        try:
            cursor.execute("""
                UPDATE controle_numeros 
                SET ultimo_numero = 0 
                WHERE tipo = 'comanda'
            """)
            
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO controle_numeros (tipo, ultimo_numero) 
                    VALUES ('comanda', 0)
                """)
            
            db.commit()
            print("[INFO] Numeração de comandas resetada para 0")
            
        finally:
            cursor.close()
            db.close()


def get_estatisticas_numeracao():
    """
    Retorna estatísticas da numeração global.
    """
    db = get_db(user_email=None)
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT tipo, ultimo_numero, updated_at 
            FROM controle_numeros 
            ORDER BY tipo
        """)
        
        return cursor.fetchall()
        
    finally:
        cursor.close()
        db.close()


# Função para migrar comandas existentes (usar apenas uma vez)
def migrar_numeracao_existente():
    """
    ATENÇÃO: Use apenas uma vez para migrar comandas existentes.
    Busca o maior ID de comanda em todos os bancos e ajusta a numeração.
    """
    print("[INFO] Iniciando migração de numeração existente...")
    
    maior_id = 0
    
    # Verificar banco principal
    try:
        db = get_db(user_email=None)
        cursor = db.cursor()
        cursor.execute("SELECT MAX(id) as max_id FROM comandas")
        result = cursor.fetchone()
        if result and result[0]:
            maior_id = max(maior_id, result[0])
        cursor.close()
        db.close()
        print(f"[INFO] Maior ID no banco principal: {result[0] if result and result[0] else 0}")
    except Exception as e:
        print(f"[WARNING] Erro ao verificar banco principal: {e}")
    
    # Verificar bancos de usuários (buscar bancos que começam com 'stoc_')
    try:
        import mysql.connector
        import os
        
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"), 
            password=os.getenv("DB_PASSWORD", "")
        )
        
        cursor = connection.cursor()
        cursor.execute("SHOW DATABASES LIKE 'stoc_%'")
        bancos = cursor.fetchall()
        
        for banco in bancos:
            nome_banco = banco[0]
            try:
                cursor.execute(f"USE {nome_banco}")
                cursor.execute("SELECT MAX(id) as max_id FROM comandas")
                result = cursor.fetchone()
                if result and result[0]:
                    maior_id = max(maior_id, result[0])
                    print(f"[INFO] Maior ID em {nome_banco}: {result[0]}")
            except Exception as e:
                print(f"[WARNING] Erro ao verificar {nome_banco}: {e}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"[ERROR] Erro ao verificar bancos de usuários: {e}")
    
    # Ajustar numeração global
    with numero_lock:
        db = get_db(user_email=None)
        cursor = db.cursor()
        
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS controle_numeros (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    tipo VARCHAR(50) NOT NULL UNIQUE,
                    ultimo_numero INT NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                INSERT INTO controle_numeros (tipo, ultimo_numero) 
                VALUES ('comanda', %s)
                ON DUPLICATE KEY UPDATE ultimo_numero = %s
            """, (maior_id, maior_id))
            
            db.commit()
            print(f"[SUCCESS] Numeração global ajustada para {maior_id}")
            
        finally:
            cursor.close()
            db.close()


if __name__ == "__main__":
    # Executar migração se chamado diretamente
    print("=== MIGRAÇÃO DE NUMERAÇÃO DE COMANDAS ===")
    migrar_numeracao_existente()
    
    # Testar geração de números
    print("\n=== TESTE DE GERAÇÃO ===")
    for i in range(3):
        numero = get_proximo_numero_comanda()
        print(f"Número gerado: {numero}")
    
    # Mostrar estatísticas
    print("\n=== ESTATÍSTICAS ===")
    stats = get_estatisticas_numeracao()
    for stat in stats:
        print(f"{stat['tipo']}: {stat['ultimo_numero']} (atualizado em {stat['updated_at']})")
