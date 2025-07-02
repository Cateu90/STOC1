# Modelo de comanda
from pydantic import BaseModel
from typing import Optional

class Comanda(BaseModel):
    id: int | None = None
    mesa_id: int | None = None
    garcom_id: Optional[int] = None
    status: str  
    total: float = 0.0
    pagamento: str | None = None
