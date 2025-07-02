from pydantic import BaseModel

class Mesa(BaseModel):
    id: int | None = None
    nome: str
    status: str = "disponivel"