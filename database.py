from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import enum

Base = declarative_base()

class PriorityLevel(enum.Enum):
    Low = "Низкий"
    Medium = "Средний"
    High = "Высокий"

class Admin(Base):
    __tablename__ = 'admins'
    login = Column(String, primary_key=True)
    password = Column(String, nullable=False)
    username = Column(String)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String)
    email = Column(String)
    phone = Column(String)
    photo = Column(String)
    is_confirmed = Column(Boolean, default=False)

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.Low)
    is_completed = Column(Boolean, default=False)

class TaskLog(Base):
    __tablename__ = 'task_logs'
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    completed_at = Column(DateTime)

class Connect:
    @staticmethod
    def create_connection():
        engine = create_engine("postgresql://postgres:1234@localhost:5432/tasklist")
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        return Session()