from pydantic import BaseModel, ConfigDict
from typing import Optional


class ProductDetailsSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    productId: str
    name: str
    price: int
    qty: int
    category: str
    imageUrls: list
    brandName: Optional[str] = None
    details: Optional[dict] = None


class ParsingItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    link: str

