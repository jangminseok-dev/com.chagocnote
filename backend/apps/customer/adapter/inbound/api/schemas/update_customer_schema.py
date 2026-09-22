from customer.adapter.inbound.api.schemas.register_customer_schema import CustomerFieldsSchema


class UpdateCustomerRequestSchema(CustomerFieldsSchema):
    """보호자 폼 전체를 보낸다(PUT). 번호를 바꿀 수 있고, 겹치면 409 다."""
