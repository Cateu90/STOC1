from pydantic import BaseModel

class ItemComanda(BaseModel):
    id: int | None = None
    comanda_id: int
    produto_id: int
    quantidade: int
    preco_unitario: float
