from pydantic import BaseModel

class Categoria(BaseModel):
    id: int | None = None
    nome: str
    impressora_id: int | None = None
