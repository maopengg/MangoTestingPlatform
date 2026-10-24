from src.apps.task_center.models import TimeTasks
from src.common.logging import log

DEFAULT_TIME_TASKS = [
    {"name": "不触发", "cron": "0 0 31 2 *"},
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
    {"name": "每天20点触发", "cron": "0 20 * * *"},
    {"name": "每天20点半触发", "cron": "30 20 * * *"},
    {"name": "每天21点触发", "cron": "0 21 * * *"},
    {"name": "每天21点半触发", "cron": "30 21 * * *"},
    {"name": "每天22点触发", "cron": "0 22 * * *"},
    {"name": "每天22点半触发", "cron": "30 22 * * *"},
    {"name": "每天23点触发", "cron": "0 23 * * *"},
    {"name": "每天9点，14点，17点触发", "cron": "0 9,14,17 * * *"},
    {"name": "每天早上9点-晚上7点每小时触发", "cron": "0 9-19 * * *"},
    {"name": "每周一8点触发", "cron": "0 8 * * 1"},
    {"name": "每周一周三晚上20点触发", "cron": "0 20 * * 1,3"},
    {"name": "每周一周三晚上21点触发", "cron": "0 21 * * 1,3"},
    {"name": "每周二周四晚上20点触发", "cron": "0 20 * * 2,4"},
    {"name": "每周二周四晚上21点触发", "cron": "0 21 * * 2,4"},
]


class DefaultTimeTaskService:
    @staticmethod
    def populate() -> int:
        existing_crons = set(TimeTasks.objects.values_list("cron", flat=True))
        missing = [item for item in DEFAULT_TIME_TASKS if item["cron"] not in existing_crons]
        TimeTasks.objects.bulk_create(
            [TimeTasks(name=item["name"], cron=item["cron"]) for item in missing],
            ignore_conflicts=True,
        )
        if missing:
            log.system.info(f"成功创建 {len(missing)} 个缺失的定时任务配置")
        else:
            log.system.info("所有定时任务配置已存在，跳过初始化")
        return len(missing)
