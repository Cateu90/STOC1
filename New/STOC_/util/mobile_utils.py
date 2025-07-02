"""
Utilitários para determinar qual banco usar no app mobile
"""

def get_banco_usuario_para_mobile(user_email, user_role):
    """
    Determina qual banco usar para o app mobile baseado no usuário
    
    Regra:
    - Admins: usam seu próprio banco
    - Garçons: usam o banco do seu admin
    """
    if user_role == 'admin':
        return user_email
    elif user_role == 'garcom':
        from repo.user_repo import UserRepo
        admin_email = UserRepo.get_admin_email_for_garcom(user_email)
        return admin_email if admin_email else user_email
    else:
        return user_email

def extrair_banco_do_token(token_payload):
    """
    Extrai informação do banco do token JWT
    """
    user_email = token_payload.get("email")
    user_role = token_payload.get("role")
    banco_usuario = token_payload.get("banco_usuario")
    
    # Se token tem banco_usuario, usar ele
    if banco_usuario:
        return banco_usuario
    
    # Senão, calcular baseado no role
    return get_banco_usuario_para_mobile(user_email, user_role)
