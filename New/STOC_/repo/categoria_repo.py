# Repositório de categoria
from data.db import get_db
from models.categoria import Categoria

class CategoriaRepo:
    @staticmethod
    def criar_categoria(categoria: Categoria, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        sql = "INSERT INTO categorias (nome, impressora_id) VALUES (%s, %s)"
        cursor.execute(sql, (categoria.nome, categoria.impressora_id))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def listar_categorias(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM categorias")
        categorias = cursor.fetchall()
        cursor.close()
        db.close()
        seen = set()
        categorias_unicas = []
        for cat in categorias:
            if cat['id'] not in seen:
                categorias_unicas.append(cat)
                seen.add(cat['id'])
        return categorias_unicas
