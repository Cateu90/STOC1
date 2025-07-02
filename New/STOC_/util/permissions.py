from fastapi import Request, HTTPException, status

def require_role(request: Request, allowed_roles):
    user = request.scope.get('user')
    if not user or user.get('role') not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")
