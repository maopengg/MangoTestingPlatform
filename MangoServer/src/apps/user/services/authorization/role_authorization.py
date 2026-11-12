from pydantic import ValidationError

from src.apps.user.exceptions import USER_ROLE_AUTHORIZATION_INVALID, USER_CREDENTIAL_NOT_FOUND, UserError
from src.apps.user.models import Role
from src.apps.user.schemas.role_authorization import RoleAuthorization


class RoleAuthorizationService:
    @staticmethod
    def parse(value):
        try:
            return RoleAuthorization.model_validate(value).model_dump(mode='json')
        except ValidationError as error:
            raise UserError(USER_ROLE_AUTHORIZATION_INVALID) from error

    @classmethod
    def get(cls, role_id):
        if not role_id:
            return cls.parse({})
        value = Role.objects.filter(pk=role_id).values_list('authorization', flat=True).first()
        if value is None:
            raise UserError(USER_CREDENTIAL_NOT_FOUND)
        return cls.parse(value)
