from django.test import SimpleTestCase

from src.apps.user.services.authorization.permission import PermissionMenuService


class MenuBetaConfigTests(SimpleTestCase):
    @staticmethod
    def _flatten(items):
        for item in items:
            yield item
            yield from MenuBetaConfigTests._flatten(item.get('children') or [])

    def test_beta_flags_are_returned_as_booleans(self):
        items = list(self._flatten(PermissionMenuService.permission_tree()))
        items_by_url = {item['menuUrl']: item for item in items}

        self.assertTrue(items_by_url['/functional-test']['isBeta'])
        self.assertTrue(items_by_url['/perf']['isBeta'])
        self.assertTrue(items_by_url['/report/execution-efficiency/index']['isBeta'])
        self.assertFalse(items_by_url['/report']['isBeta'])
        self.assertNotIn('/ai', items_by_url)
        self.assertFalse(items_by_url['/help']['isBeta'])
        self.assertTrue(all('badge' not in item for item in items))
        self.assertTrue(all(isinstance(item['isBeta'], bool) for item in items))

    def test_child_menu_can_enable_beta_independently(self):
        item = {
            'menuUrl': '/example',
            'menuName': '示例',
            'children': [
                {
                    'menuUrl': '/example/child',
                    'menuName': '子菜单',
                    'isBeta': True,
                }
            ],
        }

        PermissionMenuService._decorate_menu_item(item)

        self.assertFalse(item['isBeta'])
        self.assertTrue(item['children'][0]['isBeta'])

    def test_pytest_menu_separates_repository_management_and_project_binding(self):
        items = list(self._flatten(PermissionMenuService.permission_tree()))
        names_by_url = {item['menuUrl']: item['menuName'] for item in items}

        self.assertEqual(names_by_url['/pytest/repository/index'], '仓库管理')
        self.assertEqual(names_by_url['/pytest/product/index'], '项目绑定')
        self.assertEqual(names_by_url['/pytest/case/index'], 'Pytest用例')

    def test_menu_uses_two_level_information_architecture(self):
        tree = PermissionMenuService.permission_tree()

        self.assertEqual(
            [item['menuName'] for item in tree],
            [
                '首页',
                '研发协同',
                'UI自动化',
                'API自动化',
                'Pytest自动化',
                '性能测试',
                '评测中心',
                '监控中心',
                '报告分析',
                '数据工厂',
                '测试配置',
                '设备中心',
                '任务调度',

                '组织与权限',
                '系统运维',
                '帮助与规范',
            ],
        )
        self.assertTrue(all(
            not any(child.get('children') for child in item.get('children') or [])
            for item in tree
        ))
        development = next(item for item in tree if item['menuUrl'] == '/functional-test')
        self.assertEqual(
            [item['menuName'] for item in development['children']],
            ['迭代管理', '需求管理', '开发设计', '测试用例', '测试计划', '缺陷管理'],
        )
        online_monitoring = next(item for item in tree if item['menuUrl'] == '/monitoring')
        self.assertEqual(
            [item['menuName'] for item in online_monitoring['children']],
            ['脚本运行器', '预警监控报告'],
        )
        equipment = next(item for item in tree if item['menuUrl'] == '/equipment')
        self.assertEqual(
            [item['menuName'] for item in equipment['children']],
            ['执行器管理'],
        )
        task_scheduling = next(item for item in tree if item['menuUrl'] == '/timing')
        fire_record = next(
            item
            for item in task_scheduling['children']
            if item['menuName'] == '触发记录'
        )
        self.assertEqual(fire_record['menuUrl'], '/timing/fire-record/index')
        self.assertEqual(fire_record['localFilePath'], '/system/fire-record/index')
        system_operations = next(item for item in tree if item['menuUrl'] == '/system')
        self.assertIn(
            '系统定时任务',
            [item['menuName'] for item in system_operations['children']],
        )

    def test_organization_permission_pages_use_an_independent_route_namespace(self):
        tree = PermissionMenuService.permission_tree()
        organization = next(
            item for item in tree if item['menuUrl'] == '/organization-permission'
        )
        children_by_name = {
            item['menuName']: item for item in organization['children']
        }

        expected = {
            '用户管理': (
                '/organization-permission/user/index',
                '/system/user/index',
                'system.user',
            ),
            '角色管理': (
                '/organization-permission/role/index',
                '/system/role/index',
                'system.role',
            ),
            '部门管理': (
                '/organization-permission/department/index',
                '/system/department/index',
                'system.department',
            ),
        }
        for name, (menu_url, local_file_path, permission_key) in expected.items():
            item = children_by_name[name]
            self.assertEqual(item['menuUrl'], menu_url)
            self.assertEqual(item['localFilePath'], local_file_path)
            self.assertEqual(item['permissionKey'], permission_key)

    def test_child_page_urls_stay_in_their_visible_menu_namespace(self):
        for group in PermissionMenuService.permission_tree():
            group_url = group['menuUrl'].rstrip('/')
            for child in group.get('children') or []:
                child_url = child['menuUrl']
                if child_url.startswith('/'):
                    self.assertTrue(
                        child_url.startswith(f'{group_url}/'),
                        f"{group['menuName']} 下的 {child['menuName']} 路径不属于当前菜单分组",
                    )

    def test_usage_document_is_available_after_permission_filtering(self):
        configured_tree = PermissionMenuService.permission_tree()
        configured_url = next(
            item['menuUrl'] for item in self._flatten(configured_tree)
            if item.get('permissionKey') == 'help.documents'
        )
        tree = PermissionMenuService.filter_routes_by_permissions(
            configured_tree,
            {'help.documents', 'help.documents:read'},
        )
        items = list(self._flatten(tree))
        usage_document = next(
            item for item in items if item['menuName'] == '使用文档'
        )

        self.assertEqual(usage_document['menuUrl'], configured_url)
        self.assertEqual(usage_document['permissionKey'], 'help.documents')
