from data.db import get_db
from models.item_comanda import ItemComanda

class ItemComandaRepo:
    @staticmethod
    def adicionar_item(item: ItemComanda, user_email=None, db=None, cursor=None):
        print(f"[DEBUG] Inserindo item: comanda_id={item.comanda_id}, produto_id={item.produto_id}, quantidade={item.quantidade}, preco_unitario={item.preco_unitario}")
        own_connection = False
        if db is None or cursor is None:
            db = get_db(user_email)
            cursor = db.cursor()
            own_connection = True
        sql = "INSERT INTO itens_comanda (comanda_id, produto_id, quantidade, preco_unitario) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (item.comanda_id, item.produto_id, item.quantidade, item.preco_unitario))
        if own_connection:
            db.commit()
            cursor.close()
            db.close()

    @staticmethod
    def listar_itens(comanda_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM itens_comanda WHERE comanda_id = %s", (comanda_id,))
        itens = cursor.fetchall()
        cursor.close()
        db.close()
        return itens
