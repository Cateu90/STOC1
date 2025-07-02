from data.db import get_db
from models.mesa import Mesa

class MesaRepo:
    @staticmethod
    def listar_mesas(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mesas ORDER BY nome")
        mesas = cursor.fetchall()
        cursor.close()
        db.close()
        return mesas

    @staticmethod
    def criar_mesa(mesa: Mesa, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("DESCRIBE mesas")
        columns = [col[0] for col in cursor.fetchall()]
        
        if 'numero' in columns:
            import re
            match = re.search(r'\d+', mesa.nome)
            numero = int(match.group()) if match else 1
            
            cursor.execute("INSERT INTO mesas (nome, status, numero) VALUES (%s, %s, %s)", 
                          (mesa.nome, mesa.status, numero))
        else:
            cursor.execute("INSERT INTO mesas (nome, status) VALUES (%s, %s)", 
                          (mesa.nome, mesa.status))
        
        mesa_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        return mesa_id

    @staticmethod
    def get_mesa_por_id(mesa_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mesas WHERE id = %s", (mesa_id,))
        mesa = cursor.fetchone()
        cursor.close()
        db.close()
        return mesa

    @staticmethod
    def editar_mesa(mesa_id: int, nome: str, status: str, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("UPDATE mesas SET nome = %s, status = %s WHERE id = %s", 
                      (nome, status, mesa_id))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def excluir_mesa(mesa_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE mesa_id = %s AND status = 'aberta'", (mesa_id,))
        result = cursor.fetchone()
        if result[0] > 0:
            cursor.close()
            db.close()
            raise Exception("Não é possível excluir uma mesa com comandas abertas")
        
        cursor.execute("DELETE FROM mesas WHERE id = %s", (mesa_id,))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def contar_mesas(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM mesas")
        count = cursor.fetchone()[0]
        cursor.close()
        db.close()
        return count
