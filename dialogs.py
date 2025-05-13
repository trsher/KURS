from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox, QMessageBox, QCheckBox, QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database import Connect, User, Task, TaskLog, PriorityLevel
from bot import check_and_notify_specific_task
from datetime import datetime
from ui_elements import AvatarWidget
import logging
import requests
import base64
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imgur Client-ID
IMGUR_CLIENT_ID = "53c1d9cf6ecd87e"

class TaskEditDialog(QDialog):
    def __init__(self, theme, task=None, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.is_new_task = task is None
        self.setWindowTitle("Новая задача" if self.is_new_task else "Редактирование задачи")
        self.setGeometry(300, 300, 400, 400)
        
        # Используем имя перечисления вместо значения
        self.task = task if task is not None else Task(title="", priority=PriorityLevel.Low.name, description="")
        try:
            self.session = Connect.create_connection()
            logger.info(f"Сессия создана для задачи: id={self.task.id if not self.is_new_task else 'новая'}, title={self.task.title}")
            # Если задача существует, объединяем её с сессией
            if not self.is_new_task:
                self.task = self.session.merge(self.task)
                logger.info(f"Задача объединена с сессией: id={self.task.id}, title={self.task.title}")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            self.session = None
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к базе данных.")
            self.reject()
            return

        self.setStyleSheet("background-color: #F2F2F2;" if not self.theme else "background-color: #2D2D2D;")
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Новая задача" if self.is_new_task else "Редактирование задачи")
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Bold)
        title_label.setFont(font)
        title_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        self.title_input = QLineEdit(self.task.title)
        self.title_input.setPlaceholderText("Введите название задачи")
        self.title_input.setStyleSheet(
            "color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px; background-color: #FFFFFF;"
            if not self.theme else
            "color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 10px; padding: 5px; background-color: #3D3D3D;"
        )
        layout.addWidget(QLabel("Название:", styleSheet="color: #0D0D0D;" if not self.theme else "color: #FFFFFF;"))
        layout.addWidget(self.title_input)

        self.description_input = QLineEdit(self.task.description or "")
        self.description_input.setPlaceholderText("Введите описание задачи")
        self.description_input.setStyleSheet(
            "color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px; background-color: #FFFFFF;"
            if not self.theme else
            "color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 10px; padding: 5px; background-color: #3D3D3D;"
        )
        layout.addWidget(QLabel("Описание:", styleSheet="color: #0D0D0D;" if not self.theme else "color: #FFFFFF;"))
        layout.addWidget(self.description_input)

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
        """ if not self.theme else """
            QComboBox {
                color: #FFFFFF;
                border: 2px solid #FFFFFF;
                border-radius: 10px;
                padding: 5px;
                background-color: #3D3D3D;
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
                image: url(icons/down_arrow_dark.png);
                width: 14px;
                height: 14px;
            }
            QComboBox QAbstractItemView {
                border: 2px solid #FFFFFF;
                border-radius: 10px;
                background-color: #3D3D3D;
                color: #FFFFFF;
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
        # Отображаем значения ("Низкий", "Средний", "Высокий") для пользователя, но храним объект PriorityLevel
        for level in PriorityLevel:
            self.priority_combo.addItem(level.value, level)
        # Устанавливаем текущий приоритет, преобразуя имя из базы в значение для отображения
        current_priority = self.task.priority if isinstance(self.task.priority, str) else self.task.priority.name
        priority_level = next((level for level in PriorityLevel if level.name == current_priority), PriorityLevel.Low)
        self.priority_combo.setCurrentText(priority_level.value)
        layout.addWidget(QLabel("Приоритет:", styleSheet="color: #0D0D0D;" if not self.theme else "color: #FFFFFF;"))
        layout.addWidget(self.priority_combo)

        self.employee_combo = QComboBox()
        self.employee_combo.setStyleSheet(combo_box_style)
        self.employee_combo.addItem("Не назначено", None)
        try:
            users = self.session.query(User).filter_by(is_confirmed=True).all()
            for user in users:
                self.employee_combo.addItem(user.username or user.email or f"User {user.id}", user.id)
            if self.task.user_id:
                user = self.session.query(User).filter_by(id=self.task.user_id).first()
                if user:
                    self.employee_combo.setCurrentText(user.username or user.email or f"User {user.id}")
        except Exception as e:
            logger.error(f"Ошибка загрузки сотрудников: {e}")
        layout.addWidget(QLabel("Сотрудник:", styleSheet="color: #0D0D0D;" if not self.theme else "color: #FFFFFF;"))
        layout.addWidget(self.employee_combo)

        self.completed_check = QComboBox()
        self.completed_check.setStyleSheet(combo_box_style)
        self.completed_check.addItems(["Активна", "Завершена"])
        self.completed_check.setCurrentText("Завершена" if self.task.is_completed else "Активна")
        layout.addWidget(QLabel("Статус:", styleSheet="color: #0D0D0D;" if not self.theme else "color: #FFFFFF;"))
        layout.addWidget(self.completed_check)

        second_layout = QHBoxLayout()
        self.edit_save_btn = QPushButton("Сохранить" if self.is_new_task else "Редактировать")
        font = QFont("Montserrat", 14)
        font.setWeight(QFont.Medium)
        self.edit_save_btn.setFont(font)
        self.edit_save_btn.setStyleSheet(
            "QPushButton { background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 10px; } "
            "QPushButton:hover { background-color: #2A6FD6; }"
        )
        self.edit_save_btn.clicked.connect(self.toggle_edit)
        second_layout.addWidget(self.edit_save_btn, alignment=Qt.AlignCenter)

        self.cancel_btn = QPushButton("Отмена")
        font = QFont("Montserrat", 14)
        self.cancel_btn.setFont(font)
        self.cancel_btn.setStyleSheet(
            "QPushButton { background-color: #EB3232; color: #FFFFFF; border-radius: 10px; padding: 10px; } "
            "QPushButton:hover { background-color: #CC3333; }"
        )
        self.cancel_btn.clicked.connect(self.reject)
        second_layout.addWidget(self.cancel_btn, alignment=Qt.AlignCenter)
        
        layout.addLayout(second_layout)

        self.is_editing = self.is_new_task
        if not self.is_new_task:
            self.title_input.setReadOnly(True)
            self.description_input.setReadOnly(True)
            self.priority_combo.setEnabled(False)
            self.employee_combo.setEnabled(False)
            self.completed_check.setEnabled(False)

        layout.addStretch()

    def toggle_edit(self):
        if not self.session:
            logger.error("Сессия не инициализирована")
            QMessageBox.critical(self, "Ошибка", "Сессия не инициализирована.")
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
                # Объединяем задачу с текущей сессией перед модификацией
                self.task = self.session.merge(self.task)
                if not self.is_new_task and not self.task:
                    logger.error(f"Задача с id={self.task.id} не найдена в базе")
                    QMessageBox.critical(self, "Ошибка", "Задача не найдена.")
                    self.reject()
                    return
                logger.info(f"Задача объединена с сессией: id={self.task.id}, title={self.task.title}")

                new_title = self.title_input.text().strip()
                if not new_title:
                    logger.warning("Название задачи не может быть пустым")
                    QMessageBox.warning(self, "Ошибка", "Название задачи не может быть пустым!")
                    return
                self.task.title = new_title
                self.task.description = self.description_input.text() or None
                
                # Устанавливаем имя перечисления (Low, Medium, High) вместо значения
                priority_level = self.priority_combo.currentData()  # Это объект PriorityLevel
                self.task.priority = priority_level.name  # Устанавливаем имя, например "Low"
                
                self.task.user_id = self.employee_combo.currentData()
                is_completed = self.completed_check.currentText() == "Завершена"

                logger.info(f"Обновлены данные: title={self.task.title}, description={self.task.description}, "
                            f"priority={self.task.priority}, user_id={self.task.user_id}, is_completed={is_completed}")

                if is_completed and not self.task.is_completed and self.task.user_id:
                    task_log = TaskLog(
                        task_id=self.task.id,
                        user_id=self.task.user_id,
                        completed_at=datetime.now()
                    )
                    self.session.add(task_log)
                    logger.info(f"Добавлена запись в TaskLog для задачи id={self.task.id}")

                self.task.is_completed = is_completed

                if self.is_new_task:
                    self.session.add(self.task)
                    logger.info("Новая задача добавлена в сессию")

                self.session.commit()
                logger.info(f"Изменения сохранены для задачи id={self.task.id}")

                saved_task = self.session.query(Task).filter_by(id=self.task.id).first()
                logger.info(f"Данные в базе после сохранения: title={saved_task.title}, user_id={saved_task.user_id}, "
                            f"is_completed={saved_task.is_completed}, priority={saved_task.priority}")

                if self.task.user_id and not self.is_new_task:
                    check_and_notify_specific_task(self.task.id)

                self.accept()
            except Exception as e:
                logger.error(f"Ошибка сохранения задачи: {e}")
                self.session.rollback()
                QMessageBox.critical(self, "Ошибка", "Не удалось сохранить задачу.")
                self.reject()

    def closeEvent(self, event):
        if self.session:
            self.session.close()
            logger.info("Сессия закрыта при закрытии диалога")
        event.accept()

    def get_task_data(self):
        # Возвращаем данные в формате (title, priority, description)
        # priority теперь имя перечисления (Low, Medium, High)
        return (
            self.task.title,
            self.task.priority,  # Это строка, например "Low"
            self.task.description
        )

class EmployeeEditDialog(QDialog):
    def __init__(self, user, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование сотрудника")
        self.setMinimumSize(450, 500)
        self.user = user
        self.theme = theme
        try:
            self.session = Connect.create_connection()
            logger.info(f"Сессия создана для сотрудника: id={user.id}, username={user.username}")
        except Exception as e:
            logger.error(f"Ошибка подключения к базе данных: {e}")
            self.session = None
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к базе данных.")
            self.reject()
            return

        # Проверка корректности user
        if not user or not isinstance(user, User):
            logger.error(f"Invalid user object received: {user}, type: {type(user)}, user_id: {getattr(user, 'id', 'N/A')}")
            QMessageBox.critical(self, "Ошибка", "Некорректные данные сотрудника.")
            self.reject()
            return

        self.setStyleSheet("background-color: #F2F2F2;" if not self.theme else "background-color: #2D2D2D;")
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        top_container = QHBoxLayout()
        
        avatar_container = QWidget()
        avatar_layout = QHBoxLayout(avatar_container)
        self.avatar_widget = AvatarWidget(clickable=True)
        self.avatar_widget.setFixedSize(128, 128)
        self.avatar_widget.setVisible(True)
        photo_value = str(user.photo) if user.photo is not None and not isinstance(user.photo, bool) else ""
        logger.info(f"User ID: {user.id}, photo value: {photo_value}, type: {type(photo_value)}")
        self.avatar_widget.load_avatar(photo_value)
        avatar_layout.addWidget(self.avatar_widget)
        top_container.addWidget(avatar_container)

        tasks_label = QLabel(f"Кол-во задач: {self.get_completed_tasks()}")
        font = QFont("Montserrat", 18)
        font.setWeight(QFont.Medium)
        tasks_label.setFont(font)
        tasks_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        top_container.addWidget(tasks_label)
        top_container.addStretch()

        layout.addLayout(top_container)

        username_label = QLabel("Имя пользователя:")
        username_label_font = QFont("Montserrat", 14)
        username_label.setFont(username_label_font)
        username_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        layout.addWidget(username_label)

        self.username_input = QLineEdit(user.username or "")
        input_font = QFont("Montserrat", 12)
        self.username_input.setFont(input_font)
        self.username_input.setStyleSheet(
            "color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 8px; background-color: #FFFFFF;"
            if not self.theme else
            "color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 8px; background-color: #3D3D3D;"
        )
        self.username_input.setFixedHeight(40)
        layout.addWidget(self.username_input)

        email_label = QLabel("Email:")
        email_label.setFont(username_label_font)
        email_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        layout.addWidget(email_label)

        self.email_input = QLineEdit(user.email or "")
        self.email_input.setFont(input_font)
        self.email_input.setStyleSheet(
            "color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 8px; background-color: #FFFFFF;"
            if not self.theme else
            "color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 8px; background-color: #3D3D3D;"
        )
        self.email_input.setFixedHeight(40)
        layout.addWidget(self.email_input)

        phone_label = QLabel("Телефон:")
        phone_label.setFont(username_label_font)
        phone_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        layout.addWidget(phone_label)

        self.phone_input = QLineEdit(user.phone or "")
        self.phone_input.setFont(input_font)
        self.phone_input.setStyleSheet(
            "color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 8px; background-color: #FFFFFF;"
            if not self.theme else
            "color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 8px; background-color: #3D3D3D;"
        )
        self.phone_input.setFixedHeight(40)
        layout.addWidget(self.phone_input)

        confirmation_layout = QHBoxLayout()
        confirmation_label = QLabel("Подтверждение:")
        confirmation_label.setFont(username_label_font)
        confirmation_label.setStyleSheet("color: #0D0D0D;" if not self.theme else "color: #FFFFFF;")
        confirmation_layout.addWidget(confirmation_label)

        self.confirmed_check = QCheckBox()
        self.confirmed_check.setChecked(user.is_confirmed)
        self.confirmed_check.setStyleSheet(
            "QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #0D0D0D; border-radius: 5px; background-color: #FFFFFF; } "
            "QCheckBox::indicator:checked { image: url(icons/check.png); }"
            if not self.theme else
            "QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #FFFFFF; border-radius: 5px; background-color: #3D3D3D; } "
            "QCheckBox::indicator:checked { image: url(icons/check.png); }"
        )
        confirmation_layout.addWidget(self.confirmed_check)
        confirmation_layout.addStretch()

        layout.addLayout(confirmation_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        button_font = QFont("Montserrat", 16)
        button_font.setWeight(QFont.Medium)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFont(button_font)
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 10px; } "
            "QPushButton:hover { background-color: #2A6FD6; }"
        )
        self.save_btn.setFixedHeight(50)
        self.save_btn.clicked.connect(self.save)
        buttons_layout.addWidget(self.save_btn)

        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setFont(button_font)
        self.delete_btn.setStyleSheet(
            "QPushButton { background-color: #FF4444; color: #FFFFFF; border-radius: 10px; padding: 10px; } "
            "QPushButton:hover { background-color: #CC3333; }"
        )
        self.delete_btn.setFixedHeight(50)
        self.delete_btn.clicked.connect(self.delete_employee)
        buttons_layout.addWidget(self.delete_btn)

        layout.addLayout(buttons_layout)
        layout.addStretch()

    def get_completed_tasks(self):
        try:
            completed_tasks = self.session.query(TaskLog).filter_by(user_id=self.user.id).count()
            return completed_tasks
        except Exception as e:
            logger.error(f"Ошибка получения количества задач: {e}")
            return 0

    def upload_image_to_imgur(self, file_path):
        if not file_path or file_path.startswith("http"):
            logger.info(f"Пропуск загрузки в Imgur: file_path={file_path}")
            return file_path

        try:
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            headers = {
                "Authorization": f"Client-ID {IMGUR_CLIENT_ID}"
            }
            data = {
                "image": image_data,
                "type": "base64",
                "name": os.path.basename(file_path)
            }

            response = requests.post("https://api.imgur.com/3/image", headers=headers, data=data)
            response.raise_for_status()

            response_json = response.json()
            if response_json.get("success"):
                image_url = response_json["data"]["link"]
                logger.info(f"Изображение успешно загружено в Imgur: {image_url}")
                return image_url
            else:
                logger.error(f"Ошибка загрузки в Imgur: {response_json}")
                return None
        except Exception as e:
            logger.error(f"Ошибка загрузки изображения в Imgur: {e}")
            return None

    def save(self):
        if not self.session:
            logger.error("Сессия не инициализирована")
            QMessageBox.critical(self, "Ошибка", "Сессия не инициализирована.")
            self.reject()
            return
        try:
            self.user = self.session.merge(self.user)
            logger.info(f"Объект после merge: {self.user}, в сессии: {self.user in self.session}")

            new_photo_path = self.avatar_widget.photo_path
            logger.info(f"Попытка сохранить фото: photo_path={new_photo_path}")

            if new_photo_path:
                image_url = self.upload_image_to_imgur(new_photo_path)
                if image_url:
                    new_photo_path = image_url
                else:
                    logger.warning("Не удалось загрузить изображение в Imgur, сохраняем без изменений фото")
            else:
                logger.info("Фото не выбрано, сохраняем без изменений")

            self.user.username = self.username_input.text().strip() or None
            self.user.email = self.email_input.text().strip() or None
            self.user.phone = self.phone_input.text().strip() or None
            self.user.is_confirmed = self.confirmed_check.isChecked()
            self.user.photo = new_photo_path
            logger.info(f"Данные перед сохранением: username={self.user.username}, email={self.user.email}, "
                        f"phone={self.user.phone}, is_confirmed={self.user.is_confirmed}, photo={self.user.photo}")

            self.session.commit()
            logger.info(f"Сохранено в базе данных: photo={self.user.photo}")

            saved_user = self.session.query(User).filter_by(id=self.user.id).first()
            logger.info(f"Данные из базы после сохранения: photo={saved_user.photo}")

            self.accept()
        except Exception as e:
            logger.error(f"Ошибка сохранения данных сотрудника: {e}")
            self.session.rollback()
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить данные сотрудника.")
            self.reject()

    def delete_employee(self):
        if not self.session:
            logger.error("Сессия не инициализирована")
            QMessageBox.critical(self, "Ошибка", "Сессия не инициализирована.")
            self.reject()
            return
        confirm = QMessageBox.question(
            self,
            "Подтверждение удаления",
            "Вы уверены, что хотите удалить этого сотрудника?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            try:
                self.user = self.session.merge(self.user)
                self.session.delete(self.user)
                self.session.commit()
                logger.info(f"Сотрудник удален: id={self.user.id}")
                self.accept()
            except Exception as e:
                logger.error(f"Ошибка удаления сотрудника: {e}")
                self.session.rollback()
                QMessageBox.critical(self, "Ошибка", "Не удалось удалить сотрудника.")
                self.reject()

    def closeEvent(self, event):
        if self.session:
            self.session.close()
            logger.info("Сессия закрыта")
        event.accept()

    def get_employee_data(self):
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        return username, email
    