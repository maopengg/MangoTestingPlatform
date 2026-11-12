"""Transactional mutations for user accounts and credentials."""

from django.db import transaction

from src.apps.user.models import Role, User, UserDepartment
from src.apps.user.services.authentication.credential import UserCredentialService
from src.apps.user.services.authentication.password import encode_plain_password


class UserAccountMutationService:
    @staticmethod
    def replace_departments(user: User, department_ids: list[int], operator_id: int | None = None) -> None:
        UserDepartment.objects.filter(user=user).delete()
        UserDepartment.objects.bulk_create(
            UserDepartment(user=user, department_id=department_id, update_user_id=operator_id)
            for department_id in department_ids
        )

    @classmethod
    @transaction.atomic
    def create_from_validated_data(
            cls,
            validated_data: dict,
            *,
            department_ids: list[int] | None = None,
            operator_id: int | None = None,
    ) -> User:
        values = dict(validated_data)
        values.pop("department_ids", None)
        password = values.pop("password", None)
        if password:
            values["password"] = encode_plain_password(password)
        values.setdefault("api_key", User.unique_api_key())
        user = User.objects.create(**values)
        cls.replace_departments(user, department_ids or [], operator_id)
        return user

    @staticmethod
    def update_password(user: User, password: str, *, username: str | None = None) -> User:
        user.password = encode_plain_password(password)
        fields = ["password"]
        if username is not None and username != user.username:
            user.username = username
            fields.append("username")
        user.save(update_fields=fields)
        return user

    @classmethod
    @transaction.atomic
    def register(
            cls,
            *,
            name: str,
            email: str,
            role: Role,
            is_super_admin: bool = False,
            operator: User | None = None,
    ) -> User:
        password = UserCredentialService.generate_password()
        user = User.objects.create(
            name=name,
            username=email,
            password=encode_plain_password(password),
            role=role,
            is_super_admin=is_super_admin,
            api_key=User.unique_api_key(),
            update_user=operator,
        )
        UserCredentialService.send_password(email=email, name=name, password=password, action="账号注册")
        return user

    @classmethod
    @transaction.atomic
    def reset_password(cls, user_id: int, *, operator: User | None = None) -> User | None:
        user = User.objects.select_for_update().filter(id=user_id).first()
        if user is None:
            return None
        email = UserCredentialService.primary_email(user)
        password = UserCredentialService.generate_password()
        user.password = encode_plain_password(password)
        fields = ["password"]
        if operator is not None:
            user.update_user = operator
            fields.extend(["update_user", "update_time"])
        user.save(update_fields=fields)
        UserCredentialService.send_password(email=email, name=user.name, password=password, action="密码重置")
        return user

    @staticmethod
    def reset_api_key(user: User, *, operator: User | None = None) -> str:
        user.api_key = User.unique_api_key()
        fields = ["api_key"]
        if operator is not None:
            user.update_user = operator
            fields.extend(["update_user", "update_time"])
        user.save(update_fields=fields)
        return user.api_key

    @staticmethod
    def record_login(
            user: User,
            *,
            ip: str | None,
            upgraded_password: str | None = None,
    ) -> None:
        fields = ["ip"]
        user.ip = ip
        if upgraded_password:
            user.password = upgraded_password
            fields.append("password")
        user.save(update_fields=fields)


__all__ = ["UserAccountMutationService"]
