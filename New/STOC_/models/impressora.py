from pydantic import BaseModel

class Impressora(BaseModel):
    id: int | None = None
    nome: str
    setor: str
