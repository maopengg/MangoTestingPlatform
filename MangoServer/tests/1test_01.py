key = '下周文件地址'
value = "SELECT oss_url FROM `data_subscription_mine_task_send_detail` WHERE id = '2716';"
res = [{'oss_url': None}]
print( key is not None)
print( key != '')
print( len(res) > 0)
if key is not None and key != '' and len(res) > 0:
    print(1)