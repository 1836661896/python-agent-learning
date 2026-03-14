"""
控制流练习
这个文件用于练习 Python 中的条件判断（if/else）和循环（for/while）
"""

print("=" * 50)
print("开始控制流练习")
print("=" * 50)

print("\n--- 1. if/else 条件判断 ---")

# 基本 if 语句
age = 20
if age >= 18:
    print(f"年龄 {age} 岁，已成年")

# if-else 语句
score = 85
if score >= 60:
    print(f"分数 {score}，及格了！")
else:
    print(f"分数 {score}，不及格")

# if-elif-else 语句（多条件判断）
temperature = 25
if temperature > 30:
    print("天气很热")
elif temperature > 20:
    print("天气温暖")
elif temperature > 10:
    print("天气凉爽")
else:
    print("天气很冷")

# 比较运算符
a = 10
b = 20
print(f"\n比较运算示例：")
print(f"a = {a}, b = {b}")
print(f"a == b: {a == b}")  # 等于
print(f"a != b: {a != b}")  # 不等于
print(f"a < b: {a < b}")    # 小于
print(f"a > b: {a > b}")    # 大于
print(f"a <= b: {a <= b}")  # 小于等于
print(f"a >= b: {a >= b}")  # 大于等于

print("\n--- 2. for 循环 ---")

# 遍历列表
fruits = ["苹果", "香蕉", "橙子"]
print("遍历水果列表：")
for fruit in fruits:
    print(f"  - {fruit}")

# 遍历数字范围（类似 JavaScript 的 for (let i = 0; i < 5; i++)）
print("\n遍历数字 0 到 4：")
for i in range(5):
    print(f"  数字：{i}")

# range() 的更多用法
print("\nrange(1, 5) 生成 1 到 4：")
for i in range(1, 5):
    print(f"  数字：{i}")

print("\nrange(0, 10, 2) 生成 0 到 9，步长为 2：")
for i in range(0, 10, 2):
    print(f"  数字：{i}")

# 遍历字典
user_info = {"name": "张三", "age": 25, "city": "北京"}
print("\n遍历字典的键值对：")
for key, value in user_info.items():
    print(f"  {key}: {value}")

# 只遍历字典的键
print("\n只遍历字典的键：")
for key in user_info.keys():
    print(f"  键：{key}")

# 只遍历字典的值
print("\n只遍历字典的值：")
for value in user_info.values():
    print(f"  值：{value}")

print("\n--- 3. while 循环 ---")

# 基本 while 循环
count = 0
print("使用 while 循环计数：")
while count < 5:
    print(f"  计数：{count}")
    count += 1  # count = count + 1 的简写

# while 循环处理用户输入（模拟）
print("\n模拟处理任务列表：")
tasks = ["任务1", "任务2", "任务3"]
task_index = 0
while task_index < len(tasks):
    print(f"  处理：{tasks[task_index]}")
    task_index += 1

print("\n--- 4. 循环控制（break 和 continue）---")

# break：跳出循环
print("使用 break 提前退出循环：")
for i in range(10):
    if i == 5:
        print(f"  遇到 5，提前退出")
        break
    print(f"  数字：{i}")

# continue：跳过当前迭代，继续下一次
print("\n使用 continue 跳过某些值：")
for i in range(10):
    if i % 2 == 0:  # 如果是偶数
        continue  # 跳过，不打印
    print(f"  奇数：{i}")

print("\n--- 5. 嵌套循环 ---")

# 嵌套 for 循环（打印乘法表的一部分）
print("打印 3x3 的乘法表：")
for i in range(1, 4):
    for j in range(1, 4):
        result = i * j
        print(f"  {i} x {j} = {result}", end="  ")
    print()  # 换行