"""放base（所有ORM模型继承于此）"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
  pass