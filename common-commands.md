# Backend 常用命令速查（Python / FastAPI / Alembic）

> 目标：把本项目日常最常用命令集中记录，避免每次都回忆。

---

## 0. 先进入项目目录

```bash
cd /Users/mrsun/Documents/myproject/backend
```

---

## 1. 本地环境（虚拟环境）相关

### 1.1 创建虚拟环境（首次）

```bash
python3 -m venv .venv
```

### 1.2 激活虚拟环境（每次新开终端都要做）

```bash
source .venv/bin/activate
```

### 1.3 退出虚拟环境

```bash
deactivate
```

---

## 2. pip 依赖管理

### 2.1 安装单个依赖

```bash
pip install fastapi
```

### 2.2 安装多个常用依赖

```bash
pip install fastapi uvicorn sqlalchemy alembic
```

### 2.3 根据 requirements.txt 安装依赖

```bash
pip install -r requirements.txt
```

### 2.4 导出当前依赖到 requirements.txt

```bash
pip freeze > requirements.txt
```

### 2.5 查看已安装包

```bash
pip list
```

### 2.6 查看某个包信息

```bash
pip show alembic
```

---

## 3. 启动后端服务（FastAPI）

> 假设 FastAPI app 在 `src/api.py`，变量名是 `app`。

### 3.1 开发模式启动（推荐）

```bash
uvicorn src.api:app --reload
```

### 3.2 指定端口启动

```bash
uvicorn src.api:app --reload --port 8000
```

---

## 4. Alembic（数据库迁移）常用命令

### 4.1 初始化 Alembic（只做一次）

```bash
alembic init alembic
```

### 4.2 创建迁移文件（自动比较模型变化）

```bash
alembic revision --autogenerate -m "create tasks table"
```

### 4.3 执行迁移到最新版本

```bash
alembic upgrade head
```

### 4.4 回退一个版本

```bash
alembic downgrade -1
```

### 4.5 查看当前数据库迁移版本

```bash
alembic current
```

### 4.6 查看迁移历史

```bash
alembic history
```

### 4.7 查看是否有多个 head

```bash
alembic heads
```

---

## 5. 常用检查命令

### 5.1 查看 Python 版本

```bash
python --version
```

### 5.2 查看 pip 版本

```bash
pip --version
```

### 5.3 查看当前解释器路径（确认是否在 .venv）

```bash
which python
which pip
```

---

## 6. 推荐工作流

### 6.1 每天开始开发

```bash
cd /Users/mrsun/Documents/myproject/backend
source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.api:app --reload
```

### 6.2 修改数据库模型后

```bash
source .venv/bin/activate
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

---

## 7. 常见问题

- `command not found: alembic`：通常是未激活虚拟环境，先执行 `source .venv/bin/activate`。
- `No module named ...`：依赖未安装，执行 `pip install -r requirements.txt`。
- Alembic 自动生成为空：通常是 `alembic/env.py` 里没有正确设置 `target_metadata`。
