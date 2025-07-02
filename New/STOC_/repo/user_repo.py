from data.db import get_db
from data.db_manager import get_db_cursor
from models.user import User
from typing import Optional, Dict, Any, List


class UserRepo:
    @staticmethod
    def create_user(user: User, user_email: str = None):
        with get_db_cursor(user_email=user_email) as (cursor, db):
            if user.admin_id:
                sql = "INSERT INTO users (name, email, password, role, admin_id) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(sql, (user.name, user.email, user.password, user.role, user.admin_id))
            else:
                sql = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql, (user.name, user.email, user.password, user.role))
            db.commit()

    @staticmethod
    def get_user_by_email(email: str, user_email: str = None) -> Optional[Dict[Any, Any]]:
        with get_db_cursor(user_email=user_email) as (cursor, db):
            sql = "SELECT * FROM users WHERE LOWER(email) = LOWER(%s)"
            cursor.execute(sql, (email,))
            return cursor.fetchone()

    @staticmethod
    def get_user_by_name(name: str, user_email: str) -> Optional[Dict[Any, Any]]:
        with get_db_cursor(user_email=user_email) as (cursor, db):
            sql = "SELECT * FROM users WHERE name = %s"
            cursor.execute(sql, (name,))
            return cursor.fetchone()

    @staticmethod
    def get_user_by_id(user_id: int, user_email: str = None) -> Optional[Dict[Any, Any]]:
        with get_db_cursor(user_email=user_email) as (cursor, db):
            sql = "SELECT * FROM users WHERE id = %s"
            cursor.execute(sql, (user_id,))
            return cursor.fetchone()

    @staticmethod
    def listar_usuarios(user_email: str = None) -> List[Dict[Any, Any]]:
        with get_db_cursor(user_email=user_email) as (cursor, db):
            cursor.execute("SELECT * FROM users")
            return cursor.fetchall()

    @staticmethod
    def excluir_usuario(usuario_id: int, user_email: str = None) -> bool:
        with get_db_cursor(user_email=user_email) as (cursor, db):
            cursor.execute("DELETE FROM users WHERE id = %s AND role = 'garcom'", (usuario_id,))
            db.commit()
            return cursor.rowcount > 0

    @staticmethod
    def get_admin_email_for_garcom(garcom_email: str) -> Optional[str]:
        with get_db_cursor(user_email=None) as (cursor, db):
            cursor.execute("SELECT admin_id FROM users WHERE LOWER(email) = LOWER(%s) AND role = 'garcom'", (garcom_email,))
            garcom = cursor.fetchone()
            
            if not garcom or not garcom['admin_id']:
                return None
            
       
            cursor.execute("SELECT email FROM users WHERE id = %s AND role = 'admin'", (garcom['admin_id'],))
            admin = cursor.fetchone()
            
            return admin['email'] if admin else None
    
    @staticmethod
    def update_password(user_email: str, new_password_hash: str) -> bool:
        with get_db_cursor(user_email=None) as (cursor, db):
            cursor.execute(
                "UPDATE users SET password = %s WHERE LOWER(email) = LOWER(%s)", 
                (new_password_hash, user_email)
            )
            db.commit()
            return cursor.rowcount > 0
