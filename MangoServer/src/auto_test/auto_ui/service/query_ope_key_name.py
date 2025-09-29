# -*- coding: utf-8 -*-
# @Project: 芒果测试平台
# @Description: 
# @Time   : 2025-09-29 15:26
# @Author : 毛鹏

def get_by_object(data, target_value):
    def search_recursive(items):
        for item in items:
            if item.get('value') == target_value and 'parameter' in item:
                return item
            if 'children' in item:
                result = search_recursive(item['children'])
                if result is not None:
                    return result
            if 'children' in item:
                for child in item['children']:
                    if child.get('value') == target_value and 'parameter' in child:
                        return child

        return None

    return search_recursive(data)
