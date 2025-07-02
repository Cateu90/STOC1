from models.impressora import Impressora
from data.db import get_db

class ImpressoraRepo:
    def __init__(self, user_email=None):
        self.user_email = user_email

    @staticmethod
    def criar_impressora(impressora: Impressora, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        sql = "INSERT INTO impressoras (nome, setor) VALUES (%s, %s)"
        cursor.execute(sql, (impressora.nome, impressora.setor))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def listar_impressoras(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM impressoras")
        impressoras = cursor.fetchall()
        cursor.close()
        db.close()
        return impressoras

    @staticmethod
    def criar_impressora_retorna_id(impressora: Impressora, printer_name: str, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        sql = "INSERT INTO impressoras (nome, setor, printer_name) VALUES (%s, %s, %s)"
        cursor.execute(sql, (impressora.nome, impressora.setor, printer_name))
        impressora_id = cursor.lastrowid
        db.commit()
        cursor.close()
        db.close()
        return impressora_id

    @staticmethod
    def get_impressora_por_id(impressora_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM impressoras WHERE id = %s", (impressora_id,))
        impressora = cursor.fetchone()
        cursor.close()
        db.close()
        return impressora

    @staticmethod
    def excluir_impressora(impressora_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        # Remove associações com categorias primeiro
        cursor.execute("DELETE FROM impressora_categorias WHERE impressora_id = %s", (impressora_id,))
        # Remove a impressora
        cursor.execute("DELETE FROM impressoras WHERE id = %s", (impressora_id,))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def update(impressora: Impressora, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()

        cursor.execute(
            """
            UPDATE impressoras 
            SET nome = %s, setor = %s, printer_name = %s
            WHERE id = %s
            """,
            (impressora.nome, impressora.setor, impressora.printer_name, impressora.id)
        )

   
        cursor.execute("DELETE FROM impressora_categorias WHERE impressora_id = %s", (impressora.id,))
        
        if impressora.categorias:
            for categoria_id in impressora.categorias:
                cursor.execute(
                    "INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)",
                    (impressora.id, categoria_id)
                )
        
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def get_impressora_por_nome_categoria(nome_categoria: str, user_email: str):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        sql = """
            SELECT i.* 
            FROM impressoras i
            JOIN impressora_categorias ic ON i.id = ic.impressora_id
            JOIN categorias c ON ic.categoria_id = c.id
            WHERE c.nome = %s
        """
        cursor.execute(sql, (nome_categoria,))
        impressora = cursor.fetchone()
        cursor.close()
        db.close()
        return impressora

    @staticmethod
    def get_categorias_por_impressora(impressora_id: int, user_email: str) -> list:
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT c.*
            FROM categorias c
            JOIN impressora_categorias ic ON c.id = ic.categoria_id
            WHERE ic.impressora_id = %s
            """,
            (impressora_id,)
        )
        categorias = cursor.fetchall()
        cursor.close()
        db.close()
        return categorias

    @staticmethod
    def get_by_id(impressora_id: int, user_email: str):
        conn = get_db(user_email)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM impressoras WHERE id = %s", (impressora_id,))
        impressora = cursor.fetchone()
        
        if impressora:

            cursor.execute("""
                SELECT c.id, c.nome 
                FROM categorias c
                JOIN impressora_categorias ic ON c.id = ic.categoria_id
                WHERE ic.impressora_id = %s
            """, (impressora_id,))
            categorias = cursor.fetchall()
            impressora['categorias'] = categorias
        
        cursor.close()
        conn.close()
        return impressora

    def update(self, impressora: Impressora, user_email: str):
        conn = self._get_connection(user_email)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE impressoras 
            SET nome = %s, setor = %s, printer_name = %s
            WHERE id = %s
            """,
            (impressora.nome, impressora.setor, impressora.printer_name, impressora.id)
        )

    
        cursor.execute("DELETE FROM impressora_categorias WHERE impressora_id = %s", (impressora.id,))

        if impressora.categorias:
            for categoria_id in impressora.categorias:
                cursor.execute(
                    "INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)",
                    (impressora.id, categoria_id)
                )
        
        conn.commit()
        conn.close()

    def delete(self, impressora_id: int):
        conn = self._get_connection()
        cursor = conn.cursor()


        cursor.execute("DELETE FROM impressora_categorias WHERE impressora_id = %s", (impressora_id,))

        cursor.execute("DELETE FROM impressoras WHERE id = %s", (impressora_id,))

        conn.commit()
        cursor.close()
        conn.close()
