from data.db import get_db
from models.comanda import Comanda
from util.numero_comanda_global import get_proximo_numero_comanda
from .comanda_utils import get_select_comandas_sql, get_order_by_sql

class ComandaRepo:
    @staticmethod
    def abrir_comanda(comanda: Comanda, user_email=None):

        numero_comanda = get_proximo_numero_comanda()
        
        db = get_db(user_email)
        cursor = db.cursor()
        
        try:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                  AND TABLE_NAME = 'comandas' 
                  AND COLUMN_NAME = 'numero'
            """)
            result = cursor.fetchone()
            coluna_numero_existe = result[0] if result else 0
            
            if coluna_numero_existe > 0:
                sql = "INSERT INTO comandas (numero, mesa_id, garcom_id, status) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (numero_comanda, comanda.mesa_id, comanda.garcom_id, comanda.status))
            else:
                print(f"[WARNING] Coluna 'numero' não existe na tabela comandas. Usando apenas ID.")
                sql = "INSERT INTO comandas (mesa_id, garcom_id, status) VALUES (%s, %s, %s)"
                cursor.execute(sql, (comanda.mesa_id, comanda.garcom_id, comanda.status))
            
            comanda_id = cursor.lastrowid
            db.commit()
            
            print(f"[INFO] Comanda criada - ID: {comanda_id}, Número: {numero_comanda}")
            return comanda_id
            
        except Exception as e:
            db.rollback()
            print(f"[ERROR] Erro ao criar comanda: {e}")
            raise e
        finally:
            cursor.close()
            db.close()

    @staticmethod
    def listar_comandas_abertas(user_email=None, garcom_id=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        
        base_sql = get_select_comandas_sql(cursor)
        order_sql = get_order_by_sql(cursor)
        
        if garcom_id:
            sql = base_sql + """
                WHERE c.status = 'aberta' AND c.garcom_id = %s
            """ + order_sql
            cursor.execute(sql, (garcom_id,))
        else:
            sql = base_sql + """
                WHERE c.status = 'aberta'
            """ + order_sql
            cursor.execute(sql)
            
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def listar_comandas_por_garcom(garcom_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        
        base_sql = get_select_comandas_sql(cursor)
        order_sql = get_order_by_sql(cursor)
        sql = base_sql + """
            WHERE c.garcom_id = %s AND c.status = 'aberta'
        """ + order_sql
        cursor.execute(sql, (garcom_id,))
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def listar_todas_comandas(user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        
        base_sql = get_select_comandas_sql(cursor)
        order_sql = get_order_by_sql(cursor)
        sql = base_sql + " " + order_sql
        cursor.execute(sql)
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas

    @staticmethod
    def fechar_comanda(comanda_id: int, total: float, pagamento: str, user_email=None, db=None, cursor=None):
        own_connection = False
        if db is None or cursor is None:
            db = get_db(user_email)
            cursor = db.cursor()
            own_connection = True
        sql = "UPDATE comandas SET status = 'fechada', total = %s, pagamento = %s WHERE id = %s"
        cursor.execute(sql, (total, pagamento, comanda_id))
        if own_connection:
            db.commit()
            cursor.close()
            db.close()

    @staticmethod
    def listar_todas_comandas_admin(admin_email: str):
        from repo.user_repo import UserRepo
        
        todas_comandas = []
        
        try:
            comandas_admin = ComandaRepo.listar_todas_comandas(user_email=admin_email)
            for comanda in comandas_admin:
                comanda['origem'] = 'admin'
                comanda['banco'] = admin_email
            todas_comandas.extend(comandas_admin)
        except Exception as e:
            print(f"[WARNING] Erro ao buscar comandas do admin {admin_email}: {e}")
        
        try:
            admin_user = UserRepo.get_user_by_email(admin_email)
            if admin_user:
                admin_id = admin_user['id']
                usuarios = UserRepo.listar_usuarios()
                garcons_do_admin = [u for u in usuarios if u.get('admin_id') == admin_id and u['role'] == 'garcom']

                for garcom in garcons_do_admin:
                    try:
                        comandas_garcom = ComandaRepo.listar_todas_comandas(user_email=garcom['email'])
                        for comanda in comandas_garcom:
                            comanda['origem'] = 'garcom'
                            comanda['banco'] = garcom['email']
                            comanda['garcom_email'] = garcom['email']
                        todas_comandas.extend(comandas_garcom)
                    except Exception as e:
                        print(f"[WARNING] Erro ao buscar comandas do garçom {garcom['email']}: {e}")
                        
        except Exception as e:
            print(f"[ERROR] Erro ao buscar garçons do admin {admin_email}: {e}")
        todas_comandas.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        print(f"[INFO] Total de comandas encontradas para admin {admin_email}: {len(todas_comandas)}")
        return todas_comandas

    @staticmethod
    def listar_comandas_por_mesa(mesa_id: int, user_email=None):
        db = get_db(user_email)
        cursor = db.cursor(dictionary=True)
        base_sql = get_select_comandas_sql(cursor)
        order_sql = get_order_by_sql(cursor)
        sql = base_sql + """
            WHERE c.mesa_id = %s
        """ + order_sql
        cursor.execute(sql, (mesa_id,))
        comandas = cursor.fetchall()
        cursor.close()
        db.close()
        return comandas
