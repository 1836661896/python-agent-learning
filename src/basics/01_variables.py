"""
变量与数据类型联系
这个文件用于联系 Python 中的变量、字符串、数字、列表、字典等基础类型
"""

print("=" * 50)
print("开始变量与数据类型练习")
print("=" * 50)

print("\n --- 1. 变量与字符串 ---")

NAME = "Python Agent"
VERSION = "1.0.0"

print(f"项目名称：{NAME}")
print(f"版本号：{VERSION}")

# 字符串的常用操作
greeting = "hELlo"
print(f"原始字符串：{greeting}")
print(f"大写：{greeting.upper()}")
print(f"小写：{greeting.lower()}")
print(f"首字母大写：{greeting.capitalize()}")



print("\n--- 2. 数字类型 ---")

# 整数
age = 25
count = 100

# 浮点数（小数）
price = 99.99
pi = 3.14159

# 数字运算
sum_result = age + count
product = price * 2

print(f"整数：age = {age}, count = {count}")
print(f"浮点数：price = {price}, pi = {pi}")
print(f"加法：{age} + {count} = {sum_result}")
print(f"乘法：{price} * 2 = {product}")


print("\n--- 3. 列表（List）---")

# 创建列表
fruits = ["苹果", "香蕉", "橙子"]
numbers = [1, 2, 3, 4, 5]

print(f"水果列表：{fruits}")
print(f"数字列表：{numbers}")

# 访问列表元素（索引从 0 开始）
print(f"第一个水果：{fruits[0]}")
print(f"最后一个水果：{fruits[-1]}")

# 列表操作
fruits.append("葡萄")  # 添加元素
print(f"添加后：{fruits}")

# 前两个水果
print(f"前两个水果：{fruits[:2]}")
# 从第二个开始
print(f"从第二个开始：{fruits[1:]}")


print("\n--- 4. 字典（Dictionary）---")

# 创建字典（键值对）
user_info = {
    "name": "张三",
    "age": 25,
    "city": "北京"
}

print(f"用户信息：{user_info}")

# 访问字典元素
print(f"姓名：{user_info['name']}")
print(f"年龄：{user_info['age']}")

# 修改字典
user_info["age"] = 26
user_info["email"] = "zhangsan@example.com"
print(f"更新后：{user_info}")

# 获取所有键和值
print(f"所有键：{list(user_info.keys())}")
print(f"所有值：{list(user_info.values())}")


print("\n--- 5. 类型检查 ---")

# 使用 type() 函数查看变量类型
name = "Python"
age = 25
price = 99.99
fruits = ["苹果", "香蕉"]
user = {"name": "张三"}

print(f"name 的类型：{type(name)}")
print(f"age 的类型：{type(age)}")
print(f"price 的类型：{type(price)}")
print(f"fruits 的类型：{type(fruits)}")
print(f"user 的类型：{type(user)}")
