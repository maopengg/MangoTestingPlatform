import type { TaskSearchItem } from './types'
import { reactive } from 'vue'

export const monitoringTaskPageSize = 20
export const monitoringLogLimit = 500
export const monitoringLogInterval = 2000

export function createConditionItems() {
  return reactive<TaskSearchItem[]>([
    { key: 'name', label: '任务名称', type: 'input', placeholder: '请输入任务名称', value: '', reset() { this.value = '' } },
    { key: 'project_product', label: '项目/产品', type: 'cascader', placeholder: '请选择产品', value: null, reset() { this.value = null } },
  ])
}

export const basicMonitoringDemoCode = `# -*- coding: utf-8 -*-
"""监控脚本 Demo：展示循环检查、实时日志、异常捕获和通知写法。"""

import time

from mangotools.monitoring import MonitorBase


class DemoMonitor(MonitorBase):
    CHECK_INTERVAL_SECONDS = 10

    def run(self):
        self.log("Demo 监控任务启动成功")
        check_count = 0

        while True:
            try:
                # 在这里编写检查逻辑，例如查询接口、数据库或业务指标。
                check_count += 1
                self.log(f"第 {check_count} 次检查完成，当前未发现异常")

                has_problem = False
                if has_problem:
                    # 检测到不满足监控条件的数据后，发送给任务通知组中的对应人员。
                    self.send("发现不满足监控条件的数据，请及时处理", msg="Demo 监控告警")
            except Exception as error:
                # 单次检查失败不应让常驻任务直接退出。
                self.log_error(f"检查失败: {error}")

            time.sleep(self.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    DemoMonitor().start_monitoring()
`
export const environmentMonitoringDemoCode = `# -*- coding: utf-8 -*-
"""测试环境 Demo：读取任务所选环境的域名和逻辑数据库配置。"""

import time

from mangotools.monitoring import MonitorBase


class EnvironmentMonitor(MonitorBase):
    CHECK_INTERVAL_SECONDS = 30

    def run(self):
        if self.test_config is None:
            self.log_warning("当前任务未选择测试环境，无法读取域名和数据库配置")
            return

        # self.domain 默认优先取API自动化域名，其次取通用、UI自动化配置。
        self.log(f"开始检查 {self.test_env_name}，目标域名：{self.domain or '未配置'}")
        self.log(f"可用逻辑数据库：{list(self.database_configs)}")

        # 多数据库时请传逻辑数据库名称，例如 self.get_database_config("订单库")。
        database = self.get_database_config()
        if database:
            self.log(
                f"使用数据库 {database['alias']}："
                f"{database['db_type_name']} {database['host']}:{database['port']}"
            )

        while True:
            try:
                # 可通过 self.domain、self.domains、self.database_configs 编写检查逻辑。
                has_problem = False
                if database is None:
                    self.log_warning("当前没有唯一可用的数据库，请按逻辑数据库名称获取连接")
                else:
                    connection = self.get_database_connection()
                    try:
                        database_result = connection.condition_execute("SELECT 1 AS health")
                    finally:
                        connection.close()
                    has_problem = not bool(database_result)

                if has_problem:
                    # 检测到不满足监控条件的数据后，发送给任务通知组中的对应人员。
                    self.send("发现不满足监控条件的数据，请及时处理", msg="环境监控告警")
                else:
                    self.log("本次环境检查完成，未发现异常")
            except Exception as error:
                self.log_error(f"环境检查失败: {error}")

            time.sleep(self.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    EnvironmentMonitor().start_monitoring()
`
