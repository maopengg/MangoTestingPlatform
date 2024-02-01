error_template = 'jsonpath表达式错误，请{}检查表达式！：{}'

# 定义变量
error_action = "修复"
json_list_str = "your_json_path_expression"

# 使用 format 方法替换占位符
error_message = error_template.format(error_action, json_list_str)

# 输出结果
print(error_message)
