from src.common.schemas.base import FrozenSchema


class LiveStreamPermissionScope(FrozenSchema):
    page_key: str
    project_product_id: int
    user_id: int | None = None
