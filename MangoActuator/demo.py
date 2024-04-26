list1 = [1, 2, 3, 4, 5]
list2 = ['a', 'b', ]

# 获取两个列表的最大长度
max_len = max(len(list1), len(list2))

for i in range(max_len):
    # 从list1和list2中获取元素,如果索引超出列表长度,则从头开始
    item1 = list1[i % len(list1)]
    item2 = list2[i % len(list2)]

    print(f"List1 item: {item1}, List2 item: {item2}")
