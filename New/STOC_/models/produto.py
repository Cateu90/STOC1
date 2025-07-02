from pydantic import BaseModel

class Produto(BaseModel):
    id: int | None = None
    nome: str
    preco: float
    categoria_id: int
    tipo: str
