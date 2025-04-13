from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database import Connect, User, Task, TaskLog, PriorityLevel
from bot import check_and_notify_specific_task
from datetime import datetime
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskEditDialog(QDialog):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.is_new_task = task.id is None
        self.setWindowTitle("Новая задача" if self.is_new_task else "Редактирование задачи")
        self.setGeometry(300, 300, 400, 400)
        self.task = task
        try:
            self.session = Connect.create_connection()
            logger.info(f"Сессия создана для задачи: id={task.id}, title={task.title}")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            self.session = None
            return

        self.setStyleSheet("background-color: #F2F2F2;")
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Новая задача" if self.is_new_task else "Редактирование задачи")
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Bold)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #0D0D0D;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.title_input = QLineEdit(task.title)
        self.title_input.setReadOnly(True)
        self.title_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px; background-color: #FFFFFF;")
        layout.addWidget(QLabel("Название:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.title_input)

        self.description_input = QLineEdit(task.description or "")
        self.description_input.setReadOnly(True)
        self.description_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px; background-color: #FFFFFF;")
        layout.addWidget(QLabel("Описание:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.description_input)

        # Обновлённый стиль QComboBox с аккуратной стрелкой
        combo_box_style = """
            QComboBox {
                color: #0D0D0D;
                border: 2px solid #0D0D0D;
                border-radius: 10px;
                padding: 5px;
                background-color: #FFFFFF;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
                background-color: transparent;
            }
            QComboBox::down-arrow {
                image: url(icons/down_arrow.png); 
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #0D0D0D;
                border-radius: 10px;
                background-color: #FFFFFF;
                color: #0D0D0D;
                selection-background-color: #3889F2;
                selection-color: #FFFFFF;
                padding: 5px;
            }
            QComboBox QAbstractItemView::item {
                height: 30px;
                padding: 5px;
            }
        """

        self.priority_combo = QComboBox()
        self.priority_combo.setStyleSheet(combo_box_style)
        for level in PriorityLevel:
            self.priority_combo.addItem(level.value, level)
        self.priority_combo.setCurrentText(task.priority.value if task.priority else PriorityLevel.Low.value)
        self.priority_combo.setEnabled(False)
        layout.addWidget(QLabel("Приоритет:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.priority_combo)

        self.employee_combo = QComboBox()
        self.employee_combo.setStyleSheet(combo_box_style)
        self.employee_combo.addItem("Не назначено", None)
        try:
            users = self.session.query(User).all()
            for user in users:
                self.employee_combo.addItem(user.username or user.email or f"User {user.id}", user.id)
            if task.user_id:
                user = self.session.query(User).filter_by(id=task.user_id).first()
                if user:
                    self.employee_combo.setCurrentText(user.username or user.email or f"User {user.id}")
        except Exception as e:
            logger.error(f"Ошибка загрузки сотрудников: {e}")
        self.employee_combo.setEnabled(False)
        layout.addWidget(QLabel("Сотрудник:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.employee_combo)

        self.completed_check = QComboBox()
        self.completed_check.setStyleSheet(combo_box_style)
        self.completed_check.addItems(["Активна", "Завершена"])
        self.completed_check.setCurrentText("Завершена" if task.is_completed else "Активна")
        self.completed_check.setEnabled(False)
        layout.addWidget(QLabel("Статус:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.completed_check)

        self.edit_save_btn = QPushButton("Редактировать" if not self.is_new_task else "Сохранить")
        font = QFont("Montserrat", 14)
        font.setWeight(QFont.Medium)
        self.edit_save_btn.setFont(font)
        self.edit_save_btn.setStyleSheet("QPushButton { background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 10px; } QPushButton:hover { background-color: #2A6FD6; }")
        self.edit_save_btn.clicked.connect(self.toggle_edit)
        layout.addWidget(self.edit_save_btn, alignment=Qt.AlignCenter)

        self.is_editing = self.is_new_task
        if self.is_new_task:
            self.title_input.setReadOnly(False)
            self.description_input.setReadOnly(False)
            self.priority_combo.setEnabled(True)
            self.employee_combo.setEnabled(True)
            self.completed_check.setEnabled(True)

        layout.addStretch()


    def toggle_edit(self):
        if not self.session:
            logger.error("Сессия не инициализирована")
            self.reject()
            return

        if not self.is_editing:
            self.title_input.setReadOnly(False)
            self.description_input.setReadOnly(False)
            self.priority_combo.setEnabled(True)
            self.employee_combo.setEnabled(True)
            self.completed_check.setEnabled(True)
            self.edit_save_btn.setText("Сохранить")
            self.is_editing = True
            logger.info("Переключение в режим редактирования")
        else:
            try:
                # Для существующей задачи загружаем её из текущей сессии
                if not self.is_new_task:
                    self.task = self.session.query(Task).filter_by(id=self.task.id).first()
                    if not self.task:
                        logger.error(f"Задача с id={self.task.id} не найдена в базе")
                        self.reject()
                        return
                    logger.info(f"Загружена задача из базы: id={self.task.id}, title={self.task.title}")

                # Обновляем данные задачи
                new_title = self.title_input.text().strip()
                if not new_title:
                    logger.warning("Название задачи не может быть пустым")
                    return
                self.task.title = new_title
                self.task.description = self.description_input.text() or None
                self.task.priority = self.priority_combo.currentData()
                self.task.user_id = self.employee_combo.currentData()
                is_completed = self.completed_check.currentText() == "Завершена"

                logger.info(f"Обновлены данные: title={self.task.title}, description={self.task.description}, "
                            f"priority={self.task.priority}, user_id={self.task.user_id}, is_completed={is_completed}")

                # Добавляем запись в TaskLog, если задача завершена впервые
                if is_completed and not self.task.is_completed and self.task.user_id:
                    task_log = TaskLog(
                        task_id=self.task.id,
                        user_id=self.task.user_id,
                        completed_at=datetime.now()
                    )
                    self.session.add(task_log)
                    logger.info(f"Добавлена запись в TaskLog для задачи id={self.task.id}")

                self.task.is_completed = is_completed

                # Для новой задачи добавляем её в сессию
                if self.is_new_task:
                    self.session.add(self.task)
                    logger.info("Новая задача добавлена в сессию")

                # Проверяем, отслеживается ли объект
                logger.info(f"Объект в сессии: {self.task in self.session}")

                # Фиксируем изменения
                self.session.commit()
                logger.info(f"Изменения сохранены для задачи id={self.task.id}")

                # Проверяем данные в базе после commit
                saved_task = self.session.query(Task).filter_by(id=self.task.id).first()
                logger.info(f"Данные в базе после сохранения: title={saved_task.title}, user_id={saved_task.user_id}, "
                            f"is_completed={saved_task.is_completed}")

                # Уведомляем пользователя, если задача назначена
                if self.task.user_id and not self.is_new_task:
                    check_and_notify_specific_task(self.task.id)

                self.accept()
            except Exception as e:
                logger.error(f"Ошибка сохранения задачи: {e}")
                self.session.rollback()
                self.reject()
            finally:
                self.session.close()
                logger.info("Сессия закрыта")

    def closeEvent(self, event):
        if self.session:
            self.session.close()
            logger.info("Сессия закрыта при закрытии диалога")
        event.accept()

class EmployeeEditDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование сотрудника")
        self.setGeometry(300, 300, 400, 400)
        self.user = user
        try:
            self.session = Connect.create_connection()
        except Exception as e:
            print(f"Ошибка подключения к базе данных: {e}")
            self.session = None
            return

        self.setStyleSheet("background-color: #F2F2F2;")
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Редактирование сотрудника")
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Bold)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #0D0D0D;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.username_input = QLineEdit(user.username or "")
        self.username_input.setReadOnly(True)
        self.username_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        username_label = QLabel("Имя пользователя:")
        username_label.setStyleSheet("color: #0D0D0D;")
        layout.addWidget(username_label)
        layout.addWidget(self.username_input)

        self.email_input = QLineEdit(user.email or "")
        self.email_input.setReadOnly(True)
        self.email_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        email_label = QLabel("Email:")
        email_label.setStyleSheet("color: #0D0D0D;")
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)

        self.phone_input = QLineEdit(user.phone or "")
        self.phone_input.setReadOnly(True)
        self.phone_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        phone_label = QLabel("Телефон:")
        phone_label.setStyleSheet("color: #0D0D0D;")
        layout.addWidget(phone_label)
        layout.addWidget(self.phone_input)

        self.photo_input = QLineEdit(user.photo or "")
        self.photo_input.setReadOnly(True)
        self.photo_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        photo_label = QLabel("URL фото:")
        photo_label.setStyleSheet("color: #0D0D0D;")
        layout.addWidget(photo_label)
        layout.addWidget(self.photo_input)

        self.edit_save_btn = QPushButton("Редактировать")
        font = QFont("Montserrat", 14)
        font.setWeight(QFont.Medium)
        self.edit_save_btn.setFont(font)
        self.edit_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #3889F2; 
                color: #FFFFFF; 
                border-radius: 10px; 
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2A6FD6;
            }
        """)
        self.edit_save_btn.clicked.connect(self.toggle_edit)
        layout.addWidget(self.edit_save_btn, alignment=Qt.AlignCenter)

        self.is_editing = False
        layout.addStretch()

    def toggle_edit(self):
        if not self.session:
            self.reject()
            return
        if not self.is_editing:
            self.username_input.setReadOnly(False)
            self.email_input.setReadOnly(False)
            self.phone_input.setReadOnly(False)
            self.photo_input.setReadOnly(False)
            self.edit_save_btn.setText("Сохранить")
            self.is_editing = True
        else:
            try:
                self.user.username = self.username_input.text() or None
                self.user.email = self.email_input.text() or None
                self.user.phone = self.phone_input.text() or None
                self.user.photo = self.photo_input.text() or None
                self.session.commit()
                self.session.close()
                self.accept()
            except Exception as e:
                print(f"Ошибка сохранения данных сотрудника: {e}")
                self.session.rollback()
                self.reject()