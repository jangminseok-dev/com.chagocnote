from pydantic import BaseModel


class MeShopSchema(BaseModel):
    shop_id: int
    shop_name: str
    role: str


class MeResponseSchema(BaseModel):
    id: int
    display_name: str
    profile_image_url: str | None
    identities: list[str]
    shops: list[MeShopSchema]
