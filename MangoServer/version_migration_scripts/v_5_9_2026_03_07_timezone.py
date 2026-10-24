# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 时区转换脚本 - 将UTC时间转换为Asia/Shanghai时间（+8小时）
# @Time   : 2026-03-07 16:00
# @Author : 毛鹏
from django.db import connection


def update_timezone_for_all_tables():
    """
    将数据库中所有表的时间字段从UTC时间转换为Asia/Shanghai时间（+8小时）
    适用于从 USE_TZ=True 迁移到 USE_TZ=False 的场景
    """

    print("=" * 80)
    print("开始执行时区转换脚本")
    print("将所有时间字段从 UTC 时间转换为 Asia/Shanghai 时间（+8小时）")
    print("=" * 80)

    # 定义需要更新的表和时间字段
    # 格式: {'表名': ['时间字段1', '时间字段2', ...]}
    tables_to_update = {
        # auto_system 模块
        'project': ['create_time', 'update_time'],
        'project_product': ['create_time', 'update_time'],
        'product_module': ['create_time', 'update_time'],
        'test_object': ['create_time', 'update_time'],
        'tasks': ['create_time', 'update_time'],
        'tasks_details': ['create_time', 'update_time'],
        'timing_strategy': ['create_time', 'update_time'],
        'test_suite': ['create_time', 'update_time'],
        'test_suite_details': ['create_time', 'update_time'],
        'notice_group': ['create_time', 'update_time'],
        'file_data': ['create_time', 'update_time'],
        'cache_data': ['create_time', 'update_time'],

        # auto_api 模块
        'api_info': ['create_time', 'update_time'],
        'api_case': ['create_time', 'update_time'],
        'api_case_detailed': ['create_time', 'update_time'],
        'api_case_detailed_parameter': ['create_time', 'update_time'],
        'api_public': ['create_time', 'update_time'],
        'api_headers': ['create_time', 'update_time'],

        # auto_ui 模块
        'page': ['create_time', 'update_time'],
        'page_element': ['create_time', 'update_time'],
        'page_steps': ['create_time', 'update_time'],
        'page_steps_detailed': ['create_time', 'update_time'],
        'ui_case': ['create_time', 'update_time'],
        'ui_case_steps_detailed': ['create_time', 'update_time'],
        'ui_public': ['create_time', 'update_time'],

        # auto_pytest 模块
        'pytest_product': ['create_time', 'update_time'],
        'pytest_test_file': ['create_time', 'update_time'],
        'pytest_case': ['create_time', 'update_time'],
        'pytest_act': ['create_time', 'update_time'],

        # auto_user 模块
        'user': ['create_time', 'update_time'],
        'role': ['create_time', 'update_time'],
        'user_logs': ['create_time'],

        # monitoring 模块
        'monitoring_task': ['create_time', 'update_time'],
        'monitoring_report': ['create_time', 'update_time'],

        # auto_perf 模块（如果有的话）
        'perf_case': ['create_time', 'update_time'],
    }

    total_updated = 0
    failed_tables = []

    with connection.cursor() as cursor:
        for table_name, time_fields in tables_to_update.items():
            try:
                # 检查表是否存在
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                if not cursor.fetchone():
                    print(f"⚠️  表 {table_name} 不存在，跳过")
                    continue

                # 检查字段是否存在
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                existing_columns = [row[0] for row in cursor.fetchall()]

                valid_fields = [field for field in time_fields if field in existing_columns]

                if not valid_fields:
                    print(f"⚠️  表 {table_name} 中没有找到时间字段，跳过")
                    continue

                # 构建更新SQL
                update_parts = []
                for field in valid_fields:
                    update_parts.append(f"{field} = DATE_ADD({field}, INTERVAL 8 HOUR)")

                update_sql = f"UPDATE {table_name} SET {', '.join(update_parts)}"

                # 执行更新
                cursor.execute(update_sql)
                affected_rows = cursor.rowcount

                if affected_rows > 0:
                    print(f"✅ 表 {table_name}: 更新了 {affected_rows} 行数据，字段: {', '.join(valid_fields)}")
                    total_updated += affected_rows
                else:
                    print(f"ℹ️  表 {table_name}: 没有数据需要更新")

            except Exception as e:
                error_msg = f"表 {table_name} 更新失败: {str(e)}"
                print(f"❌ {error_msg}")
                failed_tables.append(error_msg)
                continue

    print("\n" + "=" * 80)
    print("时区转换脚本执行完成")
    print("=" * 80)
    print(f"✅ 总共更新了 {total_updated} 行数据")

    if failed_tables:
        print(f"\n⚠️  以下表更新失败:")
        for error in failed_tables:
            print(f"   - {error}")
    else:
        print("\n🎉 所有表都成功更新！")

    print("\n" + "=" * 80)
    print("注意事项:")
    print("1. 请确保已经将 settings 中的 USE_TZ 改为 False")
    print("2. 建议在执行此脚本前备份数据库")
    print("3. 执行完成后请重启 Django 服务")
    print("=" * 80)


def main_timezone():
    """
    主函数入口
    """
    try:
        # 确认是否执行
        print("\n⚠️  警告：此脚本将修改数据库中所有时间字段！")
        print("请确保：")
        print("1. 已经备份数据库")
        print("2. 已经将 USE_TZ 设置为 False")
        print("3. 当前数据库中的时间是 UTC 时间")

        update_timezone_for_all_tables()

    except Exception as e:
        print(f"\n❌ 脚本执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e


if __name__ == '__main__':
    # 如果直接运行此脚本，需要先设置 Django 环境
    import os
    import sys
    import django

    # 添加项目路径
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 设置 Django 环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
    django.setup()

    # 执行主函数
    main_timezone()
