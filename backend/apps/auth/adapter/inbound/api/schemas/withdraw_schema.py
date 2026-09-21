from pydantic import BaseModel, Field


class WithdrawRequestSchema(BaseModel):
    confirm_close_shops: bool = Field(
        False, description="혼자 사장이고 멤버가 본인뿐인 매장을 함께 닫는 데 동의한다."
    )
