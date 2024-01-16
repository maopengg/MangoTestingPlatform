from django.apps import AppConfig


class AutoUserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'PyAutoTest.auto_test.auto_user'

    def ready(self):
        from PyAutoTest.auto_test.auto_user.service.files_crud import FilesCRUD
        # 文件存储初始化
        FilesCRUD().initialization()
        # socket接口反射服务
        # ServerInterfaceReflection().while_get_data()
