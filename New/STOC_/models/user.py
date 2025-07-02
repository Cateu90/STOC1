from pydantic import BaseModel

class User(BaseModel):
    id: int | None = None
    name: str
    email: str
    password: str
    role: str  
    admin_id: int | None = None
