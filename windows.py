from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QLineEdit, QLabel, QFrame, QStackedWidget, QListWidget, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QIcon
from ui_elements import CustomAddButton, RoundedButton, EmployeeWidget, UnconfirmedEmployeeWidget
from dialogs import EmployeeEditDialog, TaskEditDialog
from database import Connect, Admin, User, Task, TaskLog, PriorityLevel
from bot import save_user_profile_photo, notify_and_show_menu


class NotificationWidget(QWidget):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setFixedSize(400, 150)
        self.setStyleSheet("""
            background-color: #3889F2;
            border-radius: 25px;
            color: #FFFFFF;
            padding: 15px;
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel(message)
        label.setWordWrap(True)
        label.setFont(QFont("Montserrat", 12))
        label.setStyleSheet("color: #FFFFFF;")
        layout.addWidget(label)
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)
        self.timer.start(5000)

    def show_notification(self):
        self.show()
        start_pos = self.pos()
        end_pos = QPoint(self.parent().width() - self.width() - 20, 20)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    def hide_notification(self):
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(self.parent().width(), 20))
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(0, 0, 1280, 720)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        central_widget.setStyleSheet("background-color: #F2F2F2;")
        
        welcome_label = QLabel("Добро пожаловать")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        welcome_label.setFont(font)
        welcome_label.setStyleSheet("color: #0D0D0D;")
        welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addSpacing(85)
        main_layout.addWidget(welcome_label)
        main_layout.addStretch()
        
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.StyledPanel)
        input_frame.setStyleSheet("background-color: #FFFFFF; border-radius: 15px;")
        input_frame.setFixedSize(430, 263)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(20)
        
        self.login_input = QLineEdit()
        self.login_input.setFixedWidth(300)
        self.login_input.setPlaceholderText("Логин")
        self.login_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px;")
        input_layout.addStretch()
        input_layout.addWidget(self.login_input, alignment=Qt.AlignCenter)
        
        self.password_input = QLineEdit()
        self.password_input.setFixedWidth(300)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px;")
        input_layout.addWidget(self.password_input, alignment=Qt.AlignCenter)
        input_layout.addStretch()
        
        main_layout.addWidget(input_frame, alignment=Qt.AlignCenter)
        main_layout.addSpacing(100)
        
        login_btn = QPushButton("Авторизоваться")
        login_btn.setFixedSize(348, 69)
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Medium)
        login_btn.setFont(font)
        login_btn.setStyleSheet("background-color: #3889F2; color: #FFFFFF; border-radius: 16px;")
        login_btn.clicked.connect(self.authenticate)
        main_layout.addWidget(login_btn, alignment=Qt.AlignCenter)
        main_layout.addStretch()

    def authenticate(self):
        login = self.login_input.text()
        password = self.password_input.text()
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=login).first()
            session.close()
            if admin and admin.password == password:
                self.hide()
                self.admin_panel = AdminPanel(login)
                self.admin_panel.show()
            else:
                self.login_input.clear()
                self.password_input.clear()
                self.login_input.setPlaceholderText("Неверный логин или пароль")
                self.password_input.setPlaceholderText("Неверный логин или пароль")
        except Exception as e:
            print(f"Ошибка авторизации: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к базе данных.")


class AdminPanel(QMainWindow):
    def __init__(self, login):
        super().__init__()
        self.login = login
        self.setWindowTitle("Окно с задачами")
        self.setGeometry(0, 0, 1280, 720)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        central_widget.setStyleSheet("background-color: #F2F2F2;")
        main_layout.addSpacing(40)

        nav_frame = QFrame()
        nav_frame.setStyleSheet("background-color: #0554F2; border-radius: 60px;")
        nav_frame.setFixedSize(160, 640)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.addSpacing(60)
        nav_layout.setSpacing(40)

        icon_path = "icons/"
        def create_placeholder_icon(text, color):
            from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor
            pixmap = QPixmap(100, 100)
            pixmap.fill(Qt.transparent)
            if pixmap.isNull():
                print(f"Не удалось создать QPixmap для placeholder-иконки: {text}")
                return QIcon()
            painter = QPainter(pixmap)
            if not painter.isActive():
                print(f"Не удалось начать рисование для placeholder-иконки: {text}")
                painter.end()
                return QIcon(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.NoPen)
            painter.drawRect(0, 0, 100, 100)
            painter.setPen(QColor("#FFFFFF"))
            font = QFont("Arial", 10)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
            painter.end()
            return QIcon(pixmap)

        def load_icon(filename):
            path = f"{icon_path}{filename}"
            icon = QIcon(path)
            if icon.isNull():
                print(f"Иконка не найдена: {path}. Используется placeholder.")
                icon = create_placeholder_icon(filename.split('.')[0], "#AAAAAA")
            return icon

        self.tasks_btn = QPushButton()
        self.tasks_btn.setFixedSize(100, 100)
        self.tasks_btn.setStyleSheet("background: transparent; border: none;")
        tasks_icon = load_icon("Task.PNG")
        self.tasks_btn.setIcon(tasks_icon)
        self.tasks_btn.setIconSize(QSize(100, 100))
        self.tasks_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        nav_layout.addWidget(self.tasks_btn, alignment=Qt.AlignCenter)

        self.employees_btn = QPushButton()
        self.employees_btn.setFixedSize(100, 100)
        self.employees_btn.setStyleSheet("background: transparent; border: none;")
        employees_icon = load_icon("Emploe.PNG")
        self.employees_btn.setIcon(employees_icon)
        self.employees_btn.setIconSize(QSize(100, 100))
        self.employees_btn.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        nav_layout.addWidget(self.employees_btn, alignment=Qt.AlignCenter)

        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(100, 100)
        self.settings_btn.setStyleSheet("background: transparent; border: none;")
        settings_icon = load_icon("Setting.PNG")
        self.settings_btn.setIcon(settings_icon)
        self.settings_btn.setIconSize(QSize(100, 100))
        self.settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        nav_layout.addWidget(self.settings_btn, alignment=Qt.AlignCenter)

        self.logout_btn = QPushButton()
        self.logout_btn.setFixedSize(100, 100)
        self.logout_btn.setStyleSheet("background: transparent; border: none;")
        logout_icon = load_icon("Exit.PNG")
        self.logout_btn.setIcon(logout_icon)
        self.logout_btn.setIconSize(QSize(100, 100))
        self.logout_btn.clicked.connect(self.logout)
        nav_layout.addWidget(self.logout_btn, alignment=Qt.AlignCenter)

        nav_layout.addSpacing(60)
        nav_layout.addStretch()
        main_layout.addWidget(nav_frame)

        self.stack = QStackedWidget()
        self.stack.currentChanged.connect(self.update_button_highlight)

        self.tasks_page = QWidget()
        tasks_layout = QVBoxLayout(self.tasks_page)
        self.setup_tasks_page(tasks_layout)
        self.stack.addWidget(self.tasks_page)

        self.employees_page = QWidget()
        employees_layout = QVBoxLayout(self.employees_page)
        self.setup_employees_page(employees_layout)
        self.stack.addWidget(self.employees_page)

        self.confirmation_page = QWidget()
        confirmation_layout = QVBoxLayout(self.confirmation_page)
        self.setup_confirmation_page(confirmation_layout)
        self.stack.addWidget(self.confirmation_page)

        self.settings_page = QWidget()
        settings_layout = QVBoxLayout(self.settings_page)
        self.setup_settings_page(settings_layout)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack)
        self.update_button_highlight(0)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_new_users)
        self.timer.start(5000)
        self.last_unconfirmed_count = self.get_unconfirmed_count()

    def update_button_highlight(self, index):
        icon_path = "icons/"
        def load_icon(filename):
            path = f"{icon_path}{filename}"
            icon = QIcon(path)
            if icon.isNull():
                print(f"Иконка не найдена: {path}. Используется placeholder.")
                from PySide6.QtGui import QPixmap, QPainter, QBrush, QColor
                pixmap = QPixmap(100, 100)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QBrush(QColor("#AAAAAA")))
                painter.setPen(Qt.NoPen)
                painter.drawRect(0, 0, 100, 100)
                painter.setPen(QColor("#FFFFFF"))
                font = QFont("Arial", 10)
                painter.setFont(font)
                painter.drawText(pixmap.rect(), Qt.AlignCenter, filename.split('.')[0])
                painter.end()
                icon = QIcon(pixmap)
            return icon
        self.tasks_btn.setIcon(load_icon("Taskg.PNG" if index == 0 else "Task.PNG"))
        self.employees_btn.setIcon(load_icon("Emploeg.PNG" if index == 1 else "Emploe.PNG"))
        self.settings_btn.setIcon(load_icon("Settingg.PNG" if index == 3 else "Setting.PNG"))

    def setup_tasks_page(self, layout):
        tasks_label = QLabel("Задачи")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        tasks_label.setFont(font)
        tasks_label.setStyleSheet("color: #0D0D0D;")
        tasks_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tasks_label)
        layout.addSpacing(40)

        self.tasks_list = QListWidget()
        self.tasks_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tasks_list.setStyleSheet("""
            QListWidget { background-color: #F2F2F2; color: #0D0D0D; border: none; }
            QListWidget::item { background-color: #FFFFFF; border: 2px solid #0D0D0D; border-radius: 15px; padding: 15px; margin: 20px 0; max-width: 900px; }
            QScrollBar:vertical { border: none; background: rgba(255, 255, 255, 0.2); width: 10px; margin: 0px 0px 0px 0px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #0554F2; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #0443C2; }
            QScrollBar::add-line:vertical { height: 0px; subcontrol-position: bottom; subcontrol-origin: margin; }
            QScrollBar::sub-line:vertical { height: 0px; subcontrol-position: top; subcontrol-origin: margin; }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        self.tasks_list.itemClicked.connect(self.open_task_edit_dialog)
        layout.addWidget(self.tasks_list)

        add_btn = CustomAddButton()
        add_btn.clicked.connect(self.add_task)
        add_btn.setParent(self.tasks_page)
        add_btn.move(self.tasks_page.width() - 100 - 40, self.tasks_page.height() - 100 - 40)
        add_btn.raise_()
        self.load_tasks()
        self.tasks_page.resizeEvent = lambda event: add_btn.move(
            self.tasks_page.width() - 100 - 40, self.tasks_page.height() - 100 - 40
        )

    def setup_employees_page(self, layout):
        employees_label = QLabel("Сотрудники")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        employees_label.setFont(font)
        employees_label.setStyleSheet("color: #0D0D0D;")
        employees_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(employees_label)
        layout.addSpacing(40)
        
        confirm_btn = RoundedButton("Подтверждение входа")
        confirm_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        layout.addWidget(confirm_btn, alignment=Qt.AlignHCenter)
        layout.addSpacing(40)
        
        self.employees_list = QListWidget()
        self.employees_list.setSelectionMode(QListWidget.NoSelection)
        self.employees_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.employees_list.setStyleSheet("""
            QListWidget { background-color: #F2F2F2; color: #0D0D0D; border: none; }
            QListWidget::item { background-color: #FFFFFF; border: 2px solid #0D0D0D; border-radius: 15px; padding: 0px; margin: 20px 0; max-width: 900px; }
            QScrollBar:vertical { border: none; background: rgba(255, 255, 255, 0.2); width: 10px; margin: 0px 0px 0px 0px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #0554F2; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #0443C2; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        self.employees_list.itemClicked.connect(self.open_employee_edit_dialog)
        layout.addWidget(self.employees_list)
        self.load_employees()

    def setup_confirmation_page(self, layout):
        confirmation_label = QLabel("Подтверждение")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        confirmation_label.setFont(font)
        confirmation_label.setStyleSheet("color: #0D0D0D;")
        confirmation_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(confirmation_label)
        
        self.unconfirmed_list = QListWidget()
        self.unconfirmed_list.setSelectionMode(QListWidget.NoSelection)
        self.unconfirmed_list.setFocusPolicy(Qt.NoFocus)
        self.unconfirmed_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.unconfirmed_list.setStyleSheet("""
            QListWidget { background-color: #F2F2F2; color: #0D0D0D; border: none; }
            QListWidget::item { background-color: #FFFFFF; border: 2px solid #0D0D0D; border-radius: 15px; padding: 0px; margin: 20px 0; max-width: 900px; }
            QListWidget::item:focus, QListWidget::item:selected { border: 2px solid #0D0D0D; outline: none !important; border-style: solid; }
            QScrollBar:vertical { border: none; background: rgba(255, 255, 250, 0.2); width: 10px; margin: 0px 0px 0px 0px; border-radius: 5px; }
            QScrollBar::handle:vertical { background: #0554F2; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #0443C2; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical { background: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """)
        layout.addWidget(self.unconfirmed_list)
        self.load_unconfirmed_employees()

    def setup_settings_page(self, layout):
        settings_label = QLabel("Настройки")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        settings_label.setFont(font)
        settings_label.setStyleSheet("color: #0D0D0D;")
        settings_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(settings_label)
        
        try:
            session = Connect.create_connection()
            # Фильтрация по login вместо id
            admin = session.query(Admin).filter_by(login=self.login).first()
            session.close()
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            admin = None
        
        login_layout = QHBoxLayout()
        login_label = QLabel("Логин:")
        login_label.setStyleSheet("color: #0D0D0D;")
        login_display = QLineEdit(self.login)
        login_display.setReadOnly(True)
        login_display.setFixedWidth(200)
        login_display.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px; background-color: #E0E0E0;")
        login_layout.addWidget(login_label)
        login_layout.addWidget(login_display)
        login_layout.addStretch()
        layout.addLayout(login_layout)
        layout.addSpacing(20)
        
        username_layout = QHBoxLayout()
        username_label = QLabel("Имя пользователя:")
        username_label.setStyleSheet("color: #0D0D0D;")
        self.username_input = QLineEdit(admin.username if admin else "")
        self.username_input.setFixedWidth(200)
        self.username_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px;")
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        username_layout.addStretch()
        layout.addLayout(username_layout)
        layout.addSpacing(20)
        
        old_password_layout = QHBoxLayout()
        old_password_label = QLabel("Старый пароль:")
        old_password_label.setStyleSheet("color: #0D0D0D;")
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.old_password_input.setFixedWidth(200)
        self.old_password_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px;")
        old_password_layout.addWidget(old_password_label)
        old_password_layout.addWidget(self.old_password_input)
        old_password_layout.addStretch()
        layout.addLayout(old_password_layout)
        layout.addSpacing(20)
        
        password_layout = QHBoxLayout()
        password_label = QLabel("Новый пароль:")
        password_label.setStyleSheet("color: #0D0D0D;")
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setFixedWidth(200)
        self.new_password_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 10px; padding: 5px;")
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.new_password_input)
        password_layout.addStretch()
        layout.addLayout(password_layout)
        layout.addSpacing(20)
        
        save_btn = QPushButton("Сохранить настройки")
        save_btn.setStyleSheet("background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 5px;")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignHCenter)
        layout.addStretch()

    def save_settings(self):
        new_username = self.username_input.text().strip()
        old_password = self.old_password_input.text().strip()
        new_password = self.new_password_input.text().strip()
        if not new_username:
            QMessageBox.warning(self, "Ошибка", "Имя пользователя не может быть пустым!")
            return
        try:
            session = Connect.create_connection()
            # Фильтрация по login вместо id
            admin = session.query(Admin).filter_by(login=self.login).first()
            if not admin or old_password != admin.password:
                session.close()
                QMessageBox.warning(self, "Ошибка", "Неверный старый пароль!")
                return
            admin.username = new_username
            if new_password:
                admin.password = new_password
            session.commit()
            session.close()
            self.username_input.clear()
            self.old_password_input.clear()
            self.new_password_input.clear()
            QMessageBox.information(self, "Успех", "Настройки успешно сохранены!")
        except Exception as e:
            print(f"Ошибка сохранения настроек: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить настройки.")

    def load_tasks(self):
        try:
            session = Connect.create_connection()
            tasks = session.query(Task).all()
            self.tasks_list.clear()
            for task in tasks:
                item = QListWidgetItem(f"{task.title} [{'Завершена' if task.is_completed else 'Активна'}]")
                item.setData(Qt.UserRole, task.id)
                item.setSizeHint(QSize(900, 100))
                self.tasks_list.addItem(item)
            session.close()
        except Exception as e:
            print(f"Ошибка загрузки задач: {e}")

    def load_employees(self):
        try:
            session = Connect.create_connection()
            users = session.query(User).filter_by(is_confirmed=True).all()
            self.employees_list.clear()
            for user in users:
                completed_tasks = session.query(TaskLog).filter_by(user_id=user.id).count()
                item = QListWidgetItem()
                item.setData(Qt.UserRole, user.id)
                widget = EmployeeWidget(user, completed_tasks)
                item.setSizeHint(QSize(900, 168))
                self.employees_list.addItem(item)
                self.employees_list.setItemWidget(item, widget)
            session.close()
        except Exception as e:
            print(f"Ошибка загрузки сотрудников: {e}")

    def load_unconfirmed_employees(self):
        try:
            session = Connect.create_connection()
            users = session.query(User).filter_by(is_confirmed=False).all()
            self.unconfirmed_list.clear()
            for user in users:
                item = QListWidgetItem()
                item.setData(Qt.UserRole, user.id)
                widget = UnconfirmedEmployeeWidget(user, self.confirm_employee, self.delete_employee)
                item.setSizeHint(QSize(900, 168))
                self.unconfirmed_list.addItem(item)
                self.unconfirmed_list.setItemWidget(item, widget)
            session.close()
        except Exception as e:
            print(f"Ошибка загрузки неподтверждённых сотрудников: {e}")

    def get_unconfirmed_count(self):
        try:
            session = Connect.create_connection()
            count = session.query(User).filter_by(is_confirmed=False).count()
            session.close()
            return count
        except Exception as e:
            print(f"Ошибка получения количества неподтверждённых: {e}")
            return 0

    def check_new_users(self):
        current_unconfirmed_count = self.get_unconfirmed_count()
        if current_unconfirmed_count > self.last_unconfirmed_count:
            new_users_count = current_unconfirmed_count - self.last_unconfirmed_count
            notification = NotificationWidget(
                f"Новый человек хочет зарегистрироваться!\n"
                f"Количество новых запросов: {new_users_count}\n"
                f"Проверьте вкладку 'Подтверждение'.",
                self
            )
            notification.move(self.width(), 20)
            notification.show_notification()
            self.last_unconfirmed_count = current_unconfirmed_count
        self.load_employees()
        self.load_unconfirmed_employees()

    def add_task(self):
        new_task = Task(title="Новая задача", priority=PriorityLevel.Low)
        dialog = TaskEditDialog(new_task, self)
        if dialog.exec():
            self.load_tasks()

    def open_task_edit_dialog(self, item):
        task_id = item.data(Qt.UserRole)
        if not task_id:
            return
        try:
            session = Connect.create_connection()
            task = session.query(Task).filter_by(id=task_id).first()
            if task:
                dialog = TaskEditDialog(task, self)
                if dialog.exec():
                    self.load_tasks()
            session.close()
        except Exception as e:
            print(f"Ошибка редактирования задачи: {e}")

    def open_employee_edit_dialog(self, item):
        user_id = item.data(Qt.UserRole)
        if not user_id:
            return
        try:
            session = Connect.create_connection()
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                dialog = EmployeeEditDialog(user, self)
                if dialog.exec():
                    self.load_employees()
            session.close()
        except Exception as e:
            print(f"Ошибка редактирования сотрудника: {e}")

    def confirm_employee(self, user_id):
        try:
            session = Connect.create_connection()
            user = session.query(User).filter_by(id=user_id).first()
            if user and not user.is_confirmed:
                user.is_confirmed = True
                session.commit()
                save_user_profile_photo(user_id)
                notify_and_show_menu(user_id)
            session.close()
            self.load_unconfirmed_employees()
            self.load_employees()
            self.last_unconfirmed_count = self.get_unconfirmed_count()
        except Exception as e:
            print(f"Ошибка подтверждения сотрудника: {e}")

    def delete_employee(self, user_id):
        try:
            session = Connect.create_connection()
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                session.delete(user)
                session.commit()
            session.close()
            self.load_unconfirmed_employees()
            self.load_employees()
            self.last_unconfirmed_count = self.get_unconfirmed_count()
        except Exception as e:
            print(f"Ошибка удаления сотрудника: {e}")

    def logout(self):
        self.timer.stop()
        self.hide()
        self.login_window = LoginWindow()
        self.login_window.show()