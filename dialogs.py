from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database import Connect, User, Task, TaskLog, PriorityLevel
from bot import check_and_notify_specific_task
from datetime import datetime


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


class TaskEditDialog(QDialog):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.is_new_task = task.id is None
        self.setWindowTitle("Новая задача" if self.is_new_task else "Редактирование задачи")
        self.setGeometry(300, 300, 400, 400)
        self.task = task
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

        title_label = QLabel("Новая задача" if self.is_new_task else "Редактирование задачи")
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Bold)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #0D0D0D;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.title_input = QLineEdit(task.title)
        self.title_input.setReadOnly(True)
        self.title_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        layout.addWidget(QLabel("Название:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.title_input)

        self.description_input = QLineEdit(task.description or "")
        self.description_input.setReadOnly(True)
        self.description_input.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        layout.addWidget(QLabel("Описание:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.description_input)

        self.priority_combo = QComboBox()
        self.priority_combo.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        for level in PriorityLevel:
            self.priority_combo.addItem(level.value, level)
        self.priority_combo.setCurrentText(task.priority.value if task.priority else PriorityLevel.Low.value)
        self.priority_combo.setEnabled(False)
        layout.addWidget(QLabel("Приоритет:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.priority_combo)

        self.employee_combo = QComboBox()
        self.employee_combo.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
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
            print(f"Ошибка загрузки сотрудников: {e}")
        self.employee_combo.setEnabled(False)
        layout.addWidget(QLabel("Сотрудник:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.employee_combo)

        self.completed_check = QComboBox()
        self.completed_check.setStyleSheet("""
            color: #0D0D0D; 
            border: 2px solid #0D0D0D; 
            border-radius: 10px; 
            padding: 5px; 
            background-color: #FFFFFF;
        """)
        self.completed_check.addItems(["Активна", "Завершена"])
        self.completed_check.setCurrentText("Завершена" if task.is_completed else "Активна")
        self.completed_check.setEnabled(False)
        layout.addWidget(QLabel("Статус:", styleSheet="color: #0D0D0D;"))
        layout.addWidget(self.completed_check)

        self.edit_save_btn = QPushButton("Редактировать" if not self.is_new_task else "Сохранить")
        font = QFont("Montserrat", 14)
        font.setWeight(QFont.Medium)
        self.edit_save_btn.setFont(font)
        self.edit_save_btn.setStyleSheet("""
            QPushButton { background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 10px; }
            QPushButton:hover { background-color: #2A6FD6; }
        """)
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
        else:
            try:
                self.task.title = self.title_input.text()
                self.task.description = self.description_input.text() or None
                self.task.priority = self.priority_combo.currentData()
                self.task.user_id = self.employee_combo.currentData()
                is_completed = self.completed_check.currentText() == "Завершена"
                if is_completed and not self.task.is_completed and self.task.user_id:
                    task_log = TaskLog(
                        task_id=self.task.id,
                        user_id=self.task.user_id,
                        completed_at=datetime.now()
                    )
                    self.session.add(task_log)
                self.task.is_completed = is_completed
                if self.is_new_task:
                    self.session.add(self.task)
                self.session.commit()
                if self.task.user_id and not self.is_new_task:
                    check_and_notify_specific_task(self.task.id)
                self.session.close()
                self.accept()
            except Exception as e:
                print(f"Ошибка сохранения задачи: {e}")
                self.session.rollback()
                self.reject()