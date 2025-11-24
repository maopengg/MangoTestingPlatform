import magic

file_path = r"D:\code\MangoTestingPlatform\MangoServer\upload_template\元素批量上传模版.xlsx"
mime = magic.Magic(mime=True)
mime_type = mime.from_file(file_path)
print(mime_type)  # 输出: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
