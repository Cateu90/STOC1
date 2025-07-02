"""
Função auxiliar para verificar se coluna numero existe
"""
def coluna_numero_existe(cursor):
    try:
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'comandas' 
              AND COLUMN_NAME = 'numero'
        """)
        result = cursor.fetchone()
        return result[0] if result else 0
    except:
        return 0

def get_select_comandas_sql(cursor):
    if coluna_numero_existe(cursor) > 0:
        return """
            SELECT 
                c.*,
                COALESCE(c.numero, c.id) as numero_exibicao,
                m.nome as mesa_nome
            FROM comandas c
            LEFT JOIN mesas m ON c.mesa_id = m.id
        """
    else:
        return """
            SELECT 
                c.*,
                c.id as numero_exibicao,
                m.nome as mesa_nome
            FROM comandas c
            LEFT JOIN mesas m ON c.mesa_id = m.id
        """

def get_order_by_sql(cursor):
    if coluna_numero_existe(cursor) > 0:
        return "ORDER BY COALESCE(c.numero, c.id) DESC"
    else:
        return "ORDER BY c.id DESC"
