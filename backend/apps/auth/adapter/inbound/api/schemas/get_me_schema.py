from pydantic import BaseModel


class MeResponseSchema(BaseModel):
    id: int
    display_name: str
    profile_image_url: str | None
    identities: list[str]
