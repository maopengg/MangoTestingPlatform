import filetype

file_path = r"D:\code\MangoTestingPlatform\MangoServer\upload_template\元素批量上传模版.xlsx"

# 使用 filetype 替换 magic
kind = filetype.guess(file_path)
if kind is not None:
    mime_type = kind.mime
    print(mime_type)  # 输出: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
else:
    print("无法识别文件类型")
