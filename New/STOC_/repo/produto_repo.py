from data.db import get_db
from models.produto import Produto

class ProdutoRepo:
    @staticmethod
    def criar_produto(produto: Produto, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        sql = "INSERT INTO produtos (nome, preco, categoria_id, tipo) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (produto.nome, produto.preco, produto.categoria_id, produto.tipo))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def listar_produtos(offset=0, limit=20, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT p.*, c.nome as categoria_nome FROM produtos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.ativo = 1 LIMIT %s OFFSET %s", (limit, offset))
        produtos = cursor.fetchall()
        cursor.close()
        db.close()
        return produtos

    @staticmethod
    def contar_produtos(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM produtos WHERE ativo = 1")
        total = cursor.fetchone()[0]
        cursor.close()
        db.close()
        return total

    @staticmethod
    def get_produto_por_id(produto_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM produtos WHERE id = %s", (produto_id,))
        produto = cursor.fetchone()
        cursor.close()
        db.close()
        return produto

    @staticmethod
    def editar_produto(produto_id: int, nome: str, preco: float, categoria_id: int, tipo: str, user_email: str):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("UPDATE produtos SET nome=%s, preco=%s, categoria_id=%s, tipo=%s WHERE id=%s", (nome, preco, categoria_id, tipo, produto_id))
        db.commit()
        cursor.close()
        db.close()

    @staticmethod
    def listar_produtos_por_categoria(categoria_id: str, user_email: str):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        
        if categoria_id == "all":
            cursor.execute("SELECT p.*, c.nome as categoria_nome FROM produtos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.ativo = 1 ORDER BY p.nome")
        elif categoria_id == "sem-categoria":
            cursor.execute("SELECT p.*, NULL as categoria_nome FROM produtos p WHERE p.categoria_id IS NULL AND p.ativo = 1 ORDER BY p.nome")
        else:
            cursor.execute("SELECT p.*, c.nome as categoria_nome FROM produtos p LEFT JOIN categorias c ON p.categoria_id = c.id WHERE p.categoria_id = %s AND p.ativo = 1 ORDER BY p.nome", (categoria_id,))
            
        produtos = cursor.fetchall()
        cursor.close()
        db.close()
        return produtos

    @staticmethod
    def excluir_produto(produto_id: int, user_email: str):
        db = get_db(user_email)
        cursor = db.cursor()
        cursor.execute("UPDATE produtos SET ativo = 0 WHERE id = %s", (produto_id,))
        db.commit()
        cursor.close()
        db.close()
