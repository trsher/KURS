from sqlalchemy import create_engine, Column, Integer, String, Boolean, Enum, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import enum
from datetime import datetime
import pytz
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

# Перечисление для уровней приоритета задач
class PriorityLevel(enum.Enum):
    Low = "Низкий"
    Medium = "Средний"
    High = "Высокий"

# Модель администратора
class Admin(Base):
    __tablename__ = 'admins'
    
    login = Column(String, unique=True, primary_key=True)
    password = Column(String, nullable=False)
    username = Column(String, nullable=False)
    theme = Column(Boolean, default=False)
    notification_interval = Column(Integer, default=5000)
    sound_notifications = Column(Boolean, default=True)
    new_user_notifications = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Admin {self.login}>"

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    email = Column(String)
    phone = Column(String)
    photo = Column(String)
    is_confirmed = Column(Boolean, default=False)
    
    tasks = relationship("Task", back_populates="user")
    logs = relationship("TaskLog", back_populates="user")
    
    def __str__(self):
        return self.username or f"User {self.id}"

# Модель задачи
class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.Low)
    is_completed = Column(Boolean, default=False)
    
    user = relationship("User", back_populates="tasks")
    logs = relationship("TaskLog", back_populates="task")

# Модель лога задач
class TaskLog(Base):
    __tablename__ = 'task_logs'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    completed_at = Column(DateTime, default=lambda: datetime.now(pytz.timezone('Europe/Moscow')))
    
    task = relationship("Task", back_populates="logs")
    user = relationship("User", back_populates="logs")

# Класс для работы с подключением к базе данных
class Connect:
    # Создание экземпляра движка базы данных
    @staticmethod
    def create_engine_instance():
        try:
            db_host = os.getenv("PGHOST", "localhost")
            db_port = os.getenv("PGPORT", "5432")
            db_name = os.getenv("PGDATABASE", "tasklist")
            db_user = os.getenv("PGUSER", "postgres")
            db_password = os.getenv("PGPASSWORD", "1234")
            
            db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            logger.info(f"Connecting to database: {db_host}:{db_port}/{db_name} as {db_user}")
            return create_engine(db_url)
        except Exception as e:
            logger.error(f"Error creating database engine: {e}")
            raise

    # Создание сессии подключения к базе данных
    @staticmethod
    def create_connection():
        try:
            engine = Connect.create_engine_instance()
            Base.metadata.create_all(engine)
            Session = sessionmaker(bind=engine)
            logger.info("Успешно подключено к базе данных.")
            return Session()
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            raise
    
    # Инициализация базы данных и создание учетной записи администратора
    @staticmethod
    def initialize_database():
        engine = Connect.create_engine_instance()
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        
        if session.query(Admin).count() == 0:
            admin = Admin(
                login="admin",
                password="admin",
                username="Administrator",
                theme=False,
                sound_notifications=True,
                new_user_notifications=True,
                notification_interval=5000
            )
            session.add(admin)
            session.commit()
            logger.info("Default admin account created")
        
        session.close()