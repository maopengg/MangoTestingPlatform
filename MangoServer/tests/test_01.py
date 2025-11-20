import mimetypes

file_path = r"C:\Users\Administrator\Desktop\蒲公英代下单字段模版-成功场景.xlsx"
mime_type, _ = mimetypes.guess_type(file_path)
print(mime_type)
