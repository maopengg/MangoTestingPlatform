from src.apps.user.services.credential import UserCredentialService


class EmailConfigTestService:
    @staticmethod
    def send(recipient: str) -> None:
        UserCredentialService.send_email(
            email=recipient,
            subject="芒果测试平台 · 邮箱配置测试",
            content="这是一封邮箱配置测试邮件。收到此邮件说明平台邮件发送配置可用。",
            subtype="plain",
        )
