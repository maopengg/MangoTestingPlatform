# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description:
# @Time   : 2023/1/17 10:20
# @Author : 毛鹏
import threading

import atexit
import time
from django.apps import AppConfig
from src.common.tools.obtain_assertion import func_info
from mangotools.enums import CacheValueTypeEnum

from src.common.enums.system_enum import CacheDataKeyEnum
from src.common.tools import is_main_process
from src.common.tools.log_collector import log


class AutoSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.apps.auto_system'

    def ready(self):
        # 多进程保护机制，防止在多进程环境下重复执行
        if is_main_process(lock_name='mango_system_init', logger=log.system):
            return

        def run():
            try:
                time.sleep(10)
                self.save_cache()
                self.populate_time_tasks()
                self.init_ass()
            except (RuntimeError, SystemError) as e:
                # 忽略进程关闭时的错误（开发服务器重载时常见）
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in
                       ['shutdown', 'interpreter', 'cannot schedule', 'after shutdown']):
                    log.system.debug(f'系统模块：忽略进程关闭错误: {e}')
                    return
                log.system.error(f'系统模块初始化异常: {e}')
            except Exception as e:
                log.system.error(f'系统模块初始化异常: {e}')
                import traceback
                traceback.print_exc()

        # 启动后台任务（设置为 daemon 线程，确保在服务关闭时能够快速退出）
        task1 = threading.Thread(target=run, daemon=True)
        task1.start()
        # 只在主进程中注册退出处理函数，避免在开发服务器重载时被意外触发
        # 使用模块级别的标志确保只注册一次
        if not hasattr(AutoSystemConfig, '_shutdown_registered'):
            atexit.register(self.shutdown)
            AutoSystemConfig._shutdown_registered = True

    @staticmethod
    def save_cache():
        try:
            from src.apps.auto_system.views.cache_data import CacheDataSerializers, CacheData
            key_list = [{'describe': i.value, 'key': i.name} for i in CacheDataKeyEnum]
            for key in key_list:
                try:
                    CacheData.objects.get(key=key.get('key'))
                except CacheData.DoesNotExist:
                    for i, value in CacheDataKeyEnum.obj().items():
                        if i == key.get('key') and value:
                            key['value'] = value
                    serializer = CacheDataSerializers(data=key)
                    if serializer.is_valid():
                        serializer.save()
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')

    @staticmethod
    def populate_time_tasks():
        try:
            from src.apps.auto_system.models import TimeTasks
            required_tasks = [
                {"name": "每1分钟触发", "cron": "*/1 * * * *"},
                {"name": "每3分钟触发", "cron": "*/3 * * * *"},
                {"name": "每5分钟触发", "cron": "*/5 * * * *"},
                {"name": "每10分钟触发", "cron": "*/10 * * * *"},
                {"name": "每20分钟触发", "cron": "*/20 * * * *"},
                {"name": "每30分钟触发", "cron": "*/30 * * * *"},
                {"name": "每1小时触发", "cron": "0 * * * *"},
                {"name": "每2小时触发", "cron": "0 */2 * * *"},
                {"name": "每3小时触发", "cron": "0 */3 * * *"},
                {"name": "每4小时触发", "cron": "0 */4 * * *"},
                {"name": "每5小时触发", "cron": "0 */5 * * *"},
                {"name": "每6小时触发", "cron": "0 */6 * * *"},
                {"name": "每天1点触发", "cron": "0 1 * * *"},
                {"name": "每天5点触发", "cron": "0 5 * * *"},
                {"name": "每天8点触发", "cron": "0 8 * * *"},
                {"name": "每天9点触发", "cron": "0 9 * * *"},
                {"name": "每天10点触发", "cron": "0 10 * * *"},
                {"name": "每天12点触发", "cron": "0 12 * * *"},
                {"name": "每天14点触发", "cron": "0 14 * * *"},
                {"name": "每天16点触发", "cron": "0 16 * * *"},
                {"name": "每天17点触发", "cron": "0 17 * * *"},
                {"name": "每天18点触发", "cron": "0 18 * * *"},
                {"name": "每天19点触发", "cron": "0 19 * * *"},
                {"name": "每天22点触发", "cron": "0 22 * * *"},
                {"name": "每天9点，14点，17点触发", "cron": "0 9,14,17 * * *"},
                {"name": "每天早上9点-晚上7点每小时触发", "cron": "0 9-19 * * *"},
                {"name": "每周一8点触发", "cron": "0 8 * * 1"},
            ]

            existing_crons = set(TimeTasks.objects.values_list('cron', flat=True))
            missing_tasks = [task for task in required_tasks if task['cron'] not in existing_crons]

            if missing_tasks:
                # 创建不存在的定时任务配置
                time_tasks_to_create = [
                    TimeTasks(name=task['name'], cron=task['cron'])
                    for task in missing_tasks
                ]

                created_count = len(time_tasks_to_create)
                TimeTasks.objects.bulk_create(time_tasks_to_create, ignore_conflicts=True)
                log.system.info(f'成功创建 {created_count} 个缺失的定时任务配置')
            else:
                log.system.info('所有定时任务配置已存在，跳过初始化')
        except Exception as e:
            log.system.error(f'初始化定时任务配置失败: {e}')
            # 重新抛出异常，让调用者知道初始化失败
            raise

    def shutdown(self):
        pass

    def init_ass(self):
        try:
            import json

            from src.apps.auto_system.models import CacheData
            from src.apps.auto_system.views.cache_data import CacheDataCRUD
            from src.common.enums.system_enum import CacheDataKey2Enum

            data = {
                'describe': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'key': CacheDataKey2Enum.ASS_SELECT_VALUE.value,
                'value': json.dumps(func_info, ensure_ascii=False),
                'value_type': CacheValueTypeEnum.DICT.value,
            }
            try:
                cache_data = CacheData.objects.get(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)
            except CacheData.DoesNotExist:
                CacheDataCRUD.inside_post(data)
            except CacheData.MultipleObjectsReturned:
                cache_data_list = CacheData.objects.filter(key=CacheDataKey2Enum.ASS_SELECT_VALUE.value)
                for cache_data in cache_data_list:
                    cache_data.delete()
                CacheDataCRUD.inside_post(data)
            else:
                CacheDataCRUD.inside_put(cache_data.id, data)
        except Exception as e:
            log.system.error(f'异常提示:{e}, 首次启动项目，请启动完成之后再重启一次！')
