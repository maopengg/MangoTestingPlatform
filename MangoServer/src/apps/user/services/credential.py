import html
import secrets
import smtplib
import string

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from mangotools.exceptions import MangoToolsError
from mangotools.models import EmailNoticeModel
from mangotools.notice import EmailSend

from src.apps.system.enums import CacheDataKeyEnum
from src.apps.system.services.system_config import SystemConfigService
from src.apps.user.exceptions import (
    USER_CREDENTIAL_INVALID,
    USER_CREDENTIAL_USER_BINDING_INVALID,
    USER_CREDENTIAL_USER_INVALID,
    USER_CREDENTIAL_EMAIL_CONFIG_FAILED,
    USER_CREDENTIAL_CONFIG_REQUIRED,
    UserError,
)
from src.apps.user.models import User
from src.common.exceptions import MangoServerError


class UserCredentialService:
    PASSWORD_LENGTH = 14
    PASSWORD_SYMBOLS = "!@#$%&*+-_"

    @staticmethod
    def is_valid_email(value: str | None) -> bool:
        email = (value or "").strip()
        if not email or len(email) > User._meta.get_field("username").max_length:
            return False
        try:
            validate_email(email)
        except ValidationError:
            return False
        return True

    @staticmethod
    def normalize_email(value: str | None) -> str:
        email = (value or "").strip().lower()
        if not UserCredentialService.is_valid_email(email):
            raise UserError(USER_CREDENTIAL_INVALID)
        return email

    @classmethod
    def is_email_login(cls, user: User) -> bool:
        return cls.is_valid_email(user.username)

    @classmethod
    def primary_email(cls, user: User) -> str:
        if cls.is_email_login(user):
            return cls.normalize_email(user.username)
        raise UserError(USER_CREDENTIAL_USER_BINDING_INVALID)

    @classmethod
    def ensure_email_available(cls, email: str, *, exclude_user_id: int | None = None) -> None:
        users = User.objects.all()
        if exclude_user_id is not None:
            users = users.exclude(id=exclude_user_id)
        if users.filter(username__iexact=email).exists():
            raise UserError(USER_CREDENTIAL_USER_INVALID)

    @classmethod
    def generate_password(cls) -> str:
        random_source = secrets.SystemRandom()
        characters = string.ascii_letters + string.digits + cls.PASSWORD_SYMBOLS
        password = [
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.digits),
            secrets.choice(cls.PASSWORD_SYMBOLS),
        ]
        password.extend(secrets.choice(characters) for _ in range(cls.PASSWORD_LENGTH - len(password)))
        random_source.shuffle(password)
        return "".join(password)

    @staticmethod
    def _mail_config() -> tuple[str, str, str]:
        try:
            values = (
                SystemConfigService.get(CacheDataKeyEnum.SYSTEM_SEND_USER.name),
                SystemConfigService.get(CacheDataKeyEnum.SYSTEM_EMAIL_HOST.name),
                SystemConfigService.get(CacheDataKeyEnum.SYSTEM_STAMP_KET.name),
            )
        except MangoServerError as error:
            raise UserError(USER_CREDENTIAL_CONFIG_REQUIRED, error=str(error)) from error
        normalized_values = tuple(value.strip() if isinstance(value, str) else value for value in values)
        if not all(normalized_values):
            raise UserError(USER_CREDENTIAL_CONFIG_REQUIRED)
        return normalized_values

    @classmethod
    def send_password(cls, *, email: str, name: str, password: str, action: str) -> None:
        safe_name = html.escape(name or email)
        safe_email = html.escape(email)
        safe_password = html.escape(password)
        platform_name = SystemConfigService.get_platform_name()
        content = f"""<!doctype html>
<html>
<body style="font-family: Arial, sans-serif; color: #1d2129; line-height: 1.7;">
  <h2>{html.escape(platform_name)}{html.escape(action)}</h2>
  <p>{safe_name}，您好：</p>
  <p>您的登录邮箱为 <strong>{safe_email}</strong>，系统随机密码为：</p>
  <p style="font-size: 20px; font-weight: 700; letter-spacing: 1px;">{safe_password}</p>
  <p>请登录后前往个人中心修改为您自己的密码。请勿向他人转发本邮件。</p>
</body>
</html>"""
        cls.send_email(
            email=email,
            subject=f"{platform_name}{action}",
            content=content,
        )

    @classmethod
    def send_email(
            cls,
            *,
            email: str,
            subject: str,
            content: str,
            subtype: str = "html",
    ) -> None:
        normalized_email = cls.normalize_email(email)
        send_user, email_host, stamp_key = cls._mail_config()
        try:
            EmailSend(
                EmailNoticeModel(
                    send_user=send_user,
                    email_host=email_host,
                    stamp_key=stamp_key,
                    send_list=[normalized_email],
                ), platform_name=SystemConfigService.get_platform_name(),
            ).send_mail(subject, content, subtype=subtype)
        except (MangoToolsError, smtplib.SMTPException, OSError) as error:
            raise UserError(USER_CREDENTIAL_EMAIL_CONFIG_FAILED, error=str(error)) from error
