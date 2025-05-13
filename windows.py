import os
import logging
from dotenv import load_dotenv
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
    QLineEdit, QLabel, QFrame, QStackedWidget, QListWidget, QListWidgetItem, QSizePolicy,
    QAbstractItemView, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QSize, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect, QAbstractAnimation
from PySide6.QtGui import QFont, QIcon, QPainter, QColor, QBrush, QPen, QPixmap
from ui_elements import CustomAddButton, RoundedButton, EmployeeWidget, UnconfirmedEmployeeWidget
from dialogs import EmployeeEditDialog, TaskEditDialog
from database import Connect, Admin, User, Task, TaskLog, PriorityLevel
from bot import notify_and_show_menu

# Настройка логирования для записи в файл
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загрузка переменных окружения из файла .env
load_dotenv()

# Виджет для отображения уведомлений
class NotificationWidget(QWidget):
    def __init__(self, message, theme=False, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.setFixedSize(400, 150)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.apply_styles()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        label = QLabel(message)
        label.setWordWrap(True)
        label.setFont(QFont("Montserrat", 12))
        label.setStyleSheet("color: #FFFFFF; background: transparent;")
        layout.addWidget(label)
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(500)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_notification)
        self.timer.start(5000)

    # Применение стилей для уведомления
    def apply_styles(self):
        bg_color = "#3889F2" if not self.theme else "#2A6FD6"
        self.setStyleSheet(f"""
            NotificationWidget {{
                background-color: {bg_color};
                border-radius: 25px;
                color: #FFFFFF;
                padding: 15px;
            }}
        """)

    # Показ уведомления с анимацией
    def show_notification(self):
        self.apply_styles()
        self.show()
        start_pos = self.pos()
        end_pos = QPoint(self.parent().width() - self.width() - 20, 20)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.start()

    # Скрытие уведомления с анимацией
    def hide_notification(self):
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(self.width(), 20))
        self.animation.finished.connect(self.deleteLater)
        self.animation.start()

    # Обновление темы уведомления
    def set_theme(self, theme):
        self.theme = theme
        self.apply_styles()
        for label in self.findChildren(QLabel):
            label.setStyleSheet("color: #FFFFFF; background: transparent;")

# Делегат для отрисовки задач в списке
class TaskItemDelegate(QStyledItemDelegate):
    def __init__(self, theme=False, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.margin_top = 30
        self.margin_bottom = 30

    # Определение размера элемента списка
    def sizeHint(self, option, index):
        return QSize(900, 100 + self.margin_top + self.margin_bottom)

    # Отрисовка элемента задачи
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        task = index.data(Qt.UserRole)
        if not task:
            painter.restore()
            return

        rect = option.rect.adjusted(0, self.margin_top, 0, -self.margin_bottom)
        card_rect = QRect(rect.x(), rect.y(), 900, 100)

        border_color = "#0D0D0D" if not self.theme else "#F2F2F2"
        bg_color = "#FFFFFF" if not self.theme else "#3D3D3D"
        text_color = "#0D0D0D" if not self.theme else "#FFFFFF"

        painter.setPen(QPen(QColor(border_color), 2))
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.drawRoundedRect(card_rect, 15, 15)

        font = QFont("Montserrat", 18)
        font.setWeight(QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor(text_color))
        text_rect = card_rect.adjusted(20, 0, -70, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, task.title)

        priority = task.priority
        indicator_rect = QRect(card_rect.right() - 70, card_rect.center().y() - 25, 50, 50)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self.get_priority_color(priority)))
        painter.drawEllipse(indicator_rect)

        painter.restore()

    # Определение цвета индикатора приоритета
    def get_priority_color(self, priority):
        if priority.value == "Низкий":
            return QColor("#47D155")
        elif priority.value == "Средний":
            return QColor("#F8E753")
        elif priority.value == "Высокий":
            return QColor("#EB3232")
        return QColor("#888")

    # Обновление темы делегата
    def set_theme(self, theme):
        self.theme = theme

# Делегат для отрисовки сотрудников
class EmployeeItemDelegate(QStyledItemDelegate):
    def __init__(self, theme=False, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.margin_top = 30
        self.margin_bottom = 30

    # Определение размера элемента списка
    def sizeHint(self, option, index):
        return QSize(900, 150 + self.margin_top + self.margin_bottom)

    # Отрисовка элемента сотрудника (обрабатывается в EmployeeWidget)
    def paint(self, painter, option, index):
        super().paint(painter, option, index)

    # Обновление темы делегата
    def set_theme(self, theme):
        self.theme = theme

# Делегат для отрисовки неподтвержденных сотрудников
class UnconfirmedEmployeeItemDelegate(QStyledItemDelegate):
    def __init__(self, theme=False, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.margin_top = 30
        self.margin_bottom = 30

    # Определение размера элемента списка
    def sizeHint(self, option, index):
        return QSize(option.rect.width() - 20, 150 + self.margin_top + self.margin_bottom)

    # Отрисовка элемента неподтвержденного сотрудника
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        employee = index.data(Qt.UserRole)
        if not employee:
            painter.restore()
            return

        rect = option.rect.adjusted(0, self.margin_top, 0, -self.margin_bottom)
        card_rect = QRect(rect.x(), rect.y(), 900, 150)

        border_color = "#0D0D0D" if not self.theme else "#F2F2F2"
        bg_color = "#FFFFFF" if not self.theme else "#3D3D3D"
        text_color = "#0D0D0D" if not self.theme else "#FFFFFF"

        painter.setPen(QPen(QColor(border_color), 2))
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.drawRoundedRect(card_rect, 15, 15)

        painter.setPen(QColor(text_color))
        painter.setFont(QFont("Montserrat", 18, QFont.Bold))
        text_rect = card_rect.adjusted(20, 0, -20, 0)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, employee.username or employee.email or str(employee.id))

        painter.restore()

    # Обновление темы делегата
    def set_theme(self, theme):
        self.theme = theme

# Окно авторизации
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(320, 180, 1280, 720)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.current_theme = False
        central_widget.setStyleSheet("background-color: #F2F2F2;")
        
        self.setWindowIcon(QIcon("icons/icon.ico"))
        
        self.welcome_label = QLabel("Добро пожаловать")
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        self.welcome_label.setFont(font)
        self.welcome_label.setStyleSheet("color: #0D0D0D;")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        main_layout.addSpacing(85)
        main_layout.addWidget(self.welcome_label)
        main_layout.addStretch()
        
        self.input_frame = QFrame()
        self.input_frame.setFixedSize(430, 263)
        self.input_frame.setStyleSheet("background-color: #FFFFFF; border-radius: 15px;")
        input_layout = QVBoxLayout(self.input_frame)
        input_layout.setContentsMargins(20, 20, 20, 20)
        input_layout.setSpacing(20)
        
        self.login_input = QLineEdit()
        self.login_input.setFixedWidth(300)
        self.login_input.setPlaceholderText("Логин")
        self.login_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 5px; background-color: #FFFFFF;")
        input_layout.addStretch()
        input_layout.addWidget(self.login_input, alignment=Qt.AlignCenter)
        
        self.password_input = QLineEdit()
        self.password_input.setFixedWidth(300)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 5px; background-color: #FFFFFF;")
        input_layout.addWidget(self.password_input, alignment=Qt.AlignCenter)
        input_layout.addStretch()
        
        main_layout.addWidget(self.input_frame, alignment=Qt.AlignCenter)
        main_layout.addSpacing(100)
        
        self.login_btn = QPushButton("Авторизоваться")
        self.login_btn.setFixedSize(348, 69)
        font = QFont("Montserrat", 24)
        font.setWeight(QFont.Medium)
        self.login_btn.setFont(font)
        self.login_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px;")
        self.login_btn.clicked.connect(self.authenticate)
        main_layout.addWidget(self.login_btn, alignment=Qt.AlignCenter)
        main_layout.addStretch()

    # Аутентификация администратора
    def authenticate(self):
        login = self.login_input.text()
        password = self.password_input.text()
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=login).first()
            if admin and admin.password == password:
                self.current_theme = admin.theme if admin.theme is not None else False
                self.hide()
                self.admin_panel = AdminPanel(login, self.current_theme)
                self.admin_panel.show()
            else:
                self.login_input.clear()
                self.password_input.clear()
                self.login_input.setPlaceholderText("Неверный логин или пароль")
                self.password_input.setPlaceholderText("Неверный логин или пароль")
            session.close()
        except Exception as e:
            logging.error(f"Ошибка авторизации: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось подключиться к базе данных.")

    # Применение темы для окна авторизации
    def set_theme(self, theme):
        self.current_theme = theme
        if not theme:
            self.centralWidget().setStyleSheet("background-color: #F2F2F2;")
            self.welcome_label.setStyleSheet("color: #0D0D0D;")
            self.input_frame.setStyleSheet("background-color: #FFFFFF; border-radius: 15px;")
            self.login_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 5px; background-color: #FFFFFF;")
            self.password_input.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 5px; background-color: #FFFFFF;")
            self.login_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px;")
        else:
            self.centralWidget().setStyleSheet("background-color: #2D2D2D;")
            self.welcome_label.setStyleSheet("color: #FFFFFF;")
            self.input_frame.setStyleSheet("background-color: #3D3D3D; border-radius: 15px;")
            self.login_input.setStyleSheet("color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 5px; background-color: #3D3D3D;")
            self.password_input.setStyleSheet("color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 5px; background-color: #3D3D3D;")
            self.login_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px;")

# Главная панель администратора
class AdminPanel(QMainWindow):
    def __init__(self, login, initial_theme=False):
        super().__init__()
        self.login = login
        self.setWindowTitle("Окно с задачами")
        self.setGeometry(320, 180, 1280, 720)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        self.setWindowIcon(QIcon("icons/icon.ico"))
        
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            self.current_theme = admin.theme if admin and admin.theme is not None else initial_theme
            self.user_notifications_enabled = admin.new_user_notifications if admin and admin.new_user_notifications is not None else True
            self.sound_notifications_enabled = admin.sound_notifications if admin and admin.sound_notifications is not None else True
            self.notification_interval = admin.notification_interval if admin and admin.notification_interval is not None else 5000
            session.close()
            logging.info("Настройки администратора успешно загружены")
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек администратора: {e}")
            self.current_theme = initial_theme
            self.user_notifications_enabled = True
            self.sound_notifications_enabled = True
            self.notification_interval = 5000
        
        central_widget.setStyleSheet(f"background-color: {'#F2F2F2' if not self.current_theme else '#2D2D2D'};")
        main_layout.addSpacing(40)

        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"background-color: {'#0554F2' if not self.current_theme else '#0445C0'}; border-radius: 60px;")
        nav_frame.setFixedSize(160, 640)
        nav_layout = QVBoxLayout(nav_frame)
        nav_layout.addSpacing(60)
        nav_layout.setSpacing(40)

        icon_path = "icons/"
        def create_placeholder_icon(text, color):
            pixmap = QPixmap(100, 100)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
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
            if not os.path.exists(path):
                logging.warning(f"Иконка не найдена: {path}. Используется placeholder.")
                return create_placeholder_icon(filename.split('.')[0], "#AAAAAA")
            icon = QIcon(path)
            if icon.isNull():
                logging.warning(f"Иконка не загружена: {path}. Используется placeholder.")
                return create_placeholder_icon(filename.split('.')[0], "#AAAAAA")
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
        self.employees_layout = QVBoxLayout(self.employees_page)
        self.setup_employees_page(self.employees_layout)
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

        self.load_employees()
        self.load_unconfirmed_employees()
        self.load_tasks()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_new_users)
        self.timer.start(self.notification_interval)
        logging.info(f"Таймер запущен с интервалом {self.notification_interval} мс")
        self.last_unconfirmed_count = self.get_unconfirmed_count()
        self.last_employee_count = self.get_employee_count()

        if self.current_theme:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    # Обновление подсветки кнопок навигации
    def update_button_highlight(self, index):
        icon_path = "icons/"
        def load_icon(filename):
            path = f"{icon_path}{filename}"
            if not os.path.exists(path):
                logging.warning(f"Иконка не найдена: {path}. Используется placeholder.")
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
                return QIcon(pixmap)
            icon = QIcon(path)
            if icon.isNull():
                logging.warning(f"Иконка не загружена: {path}. Используется placeholder.")
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
                return QIcon(pixmap)
            return icon
        self.tasks_btn.setIcon(load_icon("Taskg.PNG" if index == 0 else "Task.PNG"))
        self.employees_btn.setIcon(load_icon("Emploeg.PNG" if index == 1 else "Emploe.PNG"))
        self.settings_btn.setIcon(load_icon("Settingg.PNG" if index == 3 else "Setting.PNG"))

    # Плавная прокрутка списка
    def smooth_scroll(self, target_value, scrollbar):
        animation_attr = f"scroll_animation_{id(scrollbar)}"
        if hasattr(self, animation_attr) and getattr(self, animation_attr).state() == QAbstractAnimation.Running:
            getattr(self, animation_attr).stop()

        animation = QPropertyAnimation(scrollbar, b"value")
        animation.setDuration(300)
        animation.setStartValue(scrollbar.value())
        animation.setEndValue(target_value)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        setattr(self, animation_attr, animation)
        animation.start()

    # Настройка страницы задач
    def setup_tasks_page(self, layout):
        tasks_label = QLabel("Задачи")
        tasks_label.setObjectName("tasks_label")
        tasks_label.setProperty("isHeader", True)
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        tasks_label.setFont(font)
        tasks_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        tasks_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(tasks_label)
        layout.addSpacing(40)

        self.tasks_list = QListWidget()
        self.tasks_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tasks_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.update_tasks_list_style()
        
        scrollbar = self.tasks_list.verticalScrollBar()
        scrollbar.setSingleStep(10)
        scrollbar.valueChanged.connect(lambda value: self.smooth_scroll(value, scrollbar))

        self.tasks_list.setItemDelegate(TaskItemDelegate(theme=self.current_theme, parent=self.tasks_list))
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

    # Настройка страницы сотрудников
    def setup_employees_page(self, layout):
        employees_label = QLabel("Сотрудники")
        employees_label.setObjectName("employees_label")
        employees_label.setProperty("isHeader", True)
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        employees_label.setFont(font)
        employees_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        employees_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(employees_label)
        layout.addSpacing(40)
        
        confirm_btn = RoundedButton("Подтверждение входа")
        confirm_btn.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        layout.addWidget(confirm_btn, alignment=Qt.AlignHCenter)
        layout.addSpacing(40)
        
        self.employees_list = QListWidget()
        self.employees_list.setSelectionMode(QListWidget.SingleSelection)
        self.employees_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.employees_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.update_employees_list_style()

        scrollbar = self.employees_list.verticalScrollBar()
        scrollbar.setSingleStep(10)
        scrollbar.valueChanged.connect(lambda value: self.smooth_scroll(value, scrollbar))

        self.employees_list.setItemDelegate(EmployeeItemDelegate(theme=self.current_theme, parent=self.employees_list))
        self.employees_list.itemClicked.connect(self.debug_item_click)
        layout.addWidget(self.employees_list)

        self.no_employees_label = QLabel("Сотрудники отсутствуют")
        self.no_employees_label.setFont(QFont("Montserrat", 24))
        self.no_employees_label.setAlignment(Qt.AlignCenter)
        self.no_employees_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        self.no_employees_label.setVisible(False)
        layout.addWidget(self.no_employees_label)

        self.load_employees()

    # Настройка страницы подтверждения сотрудников
    def setup_confirmation_page(self, layout):
        confirmation_label = QLabel("Подтверждение")
        confirmation_label.setObjectName("confirmation_label")
        confirmation_label.setProperty("isHeader", True)
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        confirmation_label.setFont(font)
        confirmation_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        confirmation_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(confirmation_label)
        
        self.unconfirmed_list = QListWidget()
        self.unconfirmed_list.setSelectionMode(QListWidget.NoSelection)
        self.unconfirmed_list.setFocusPolicy(Qt.NoFocus)
        self.unconfirmed_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.update_unconfirmed_list_style()
        self.unconfirmed_list.setItemDelegate(UnconfirmedEmployeeItemDelegate(theme=self.current_theme, parent=self.unconfirmed_list))
        layout.addWidget(self.unconfirmed_list)
        self.load_unconfirmed_employees()

        test_btn = QPushButton("Обновить список")
        test_btn.clicked.connect(self.load_unconfirmed_employees)
        layout.addWidget(test_btn, alignment=Qt.AlignHCenter)

    # Настройка страницы настроек
    def setup_settings_page(self, layout):
        settings_label = QLabel("Настройки")
        settings_label.setObjectName("settings_label")
        settings_label.setProperty("isHeader", True)
        font = QFont("Montserrat", 64)
        font.setWeight(QFont.Bold)
        settings_label.setFont(font)
        settings_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        settings_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(settings_label)
        layout.addSpacing(40)
        
        self.settings_stack = QStackedWidget()
        
        profile_card = QWidget()
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(30, 30, 30, 30)
        profile_layout.setSpacing(30)
        
        card_title = QLabel("Настройки профиля")
        card_title.setObjectName("card_title")
        card_title.setFont(QFont("Montserrat", 28, QFont.Bold))
        card_title.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        card_title.setAlignment(Qt.AlignCenter)
        profile_layout.addWidget(card_title)
        profile_layout.addSpacing(20)
        
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            session.close()
        except Exception as e:
            logging.error(f"Ошибка загрузки настроек профиля: {e}")
            admin = None
        
        username_container = QWidget()
        username_layout = QHBoxLayout(username_container)
        username_layout.setContentsMargins(0, 0, 0, 0)
        
        username_label = QLabel("Имя пользователя:")
        username_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        username_label.setFixedWidth(200)
        username_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.username_input = QLineEdit(admin.username if admin else "")
        self.username_input.setFixedWidth(300)
        self.username_input.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border: 2px solid {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border-radius: 15px; padding: 10px; background-color: {'#FFFFFF' if not self.current_theme else '#3D3D3D'};")
        
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        username_layout.addStretch()
        profile_layout.addWidget(username_container)
        
        old_password_container = QWidget()
        old_password_layout = QHBoxLayout(old_password_container)
        old_password_layout.setContentsMargins(0, 0, 0, 0)
        
        old_password_label = QLabel("Старый пароль:")
        old_password_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        old_password_label.setFixedWidth(200)
        old_password_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.old_password_input.setFixedWidth(300)
        self.old_password_input.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border: 2px solid {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border-radius: 15px; padding: 10px; background-color: {'#FFFFFF' if not self.current_theme else '#3D3D3D'};")
        
        old_password_layout.addWidget(old_password_label)
        old_password_layout.addWidget(self.old_password_input)
        old_password_layout.addStretch()
        profile_layout.addWidget(old_password_container)
        
        new_password_container = QWidget()
        new_password_layout = QHBoxLayout(new_password_container)
        new_password_layout.setContentsMargins(0, 0, 0, 0)
        
        new_password_label = QLabel("Новый пароль:")
        new_password_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        new_password_label.setFixedWidth(200)
        new_password_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setFixedWidth(300)
        self.new_password_input.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border: 2px solid {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border-radius: 15px; padding: 10px; background-color: {'#FFFFFF' if not self.current_theme else '#3D3D3D'};")
        
        new_password_layout.addWidget(new_password_label)
        new_password_layout.addWidget(self.new_password_input)
        new_password_layout.addStretch()
        profile_layout.addWidget(new_password_container)
        
        save_btn = QPushButton("Сохранить изменения")
        save_btn.setFixedSize(300, 50)
        save_btn.setFont(QFont("Montserrat", 14))
        save_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")
        save_btn.clicked.connect(self.save_profile_settings)
        profile_layout.addWidget(save_btn, alignment=Qt.AlignCenter)
        profile_layout.addStretch()
        
        profile_frame = QFrame()
        profile_frame.setLayout(profile_layout)
        
        theme_card = QWidget()
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(30, 30, 30, 30)
        theme_layout.setSpacing(30)
        
        theme_title = QLabel("Настройки темы")
        theme_title.setObjectName("card_title")
        theme_title.setFont(QFont("Montserrat", 28, QFont.Bold))
        theme_title.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        theme_title.setAlignment(Qt.AlignCenter)
        theme_layout.addWidget(theme_title)
        theme_layout.addSpacing(20)
        
        themes_container = QWidget()
        themes_layout = QHBoxLayout(themes_container)
        themes_layout.setContentsMargins(0, 0, 0, 0)
        
        light_theme_container = QWidget()
        light_layout = QVBoxLayout(light_theme_container)
        light_layout.setContentsMargins(0, 0, 0, 0)
        light_layout.setSpacing(15)
        
        sun_icon = QLabel()
        sun_icon.setPixmap(QPixmap("icons/sun.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        sun_icon.setAlignment(Qt.AlignCenter)
        light_layout.addWidget(sun_icon)
        
        self.light_theme_btn = QPushButton("Светлая тема")
        self.light_theme_btn.setFixedSize(200, 40)
        self.light_theme_btn.setFont(QFont("Montserrat", 12))
        self.light_theme_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")
        self.light_theme_btn.clicked.connect(lambda: self.change_theme(False))
        light_layout.addWidget(self.light_theme_btn, alignment=Qt.AlignCenter)
        
        dark_theme_container = QWidget()
        dark_layout = QVBoxLayout(dark_theme_container)
        dark_layout.setContentsMargins(0, 0, 0, 0)
        dark_layout.setSpacing(15)
        
        moon_icon = QLabel()
        moon_icon.setPixmap(QPixmap("icons/moon.png").scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        moon_icon.setAlignment(Qt.AlignCenter)
        dark_layout.addWidget(moon_icon)
        
        self.dark_theme_btn = QPushButton("Тёмная тема")
        self.dark_theme_btn.setFixedSize(200, 40)
        self.dark_theme_btn.setFont(QFont("Montserrat", 12))
        self.dark_theme_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")
        self.dark_theme_btn.clicked.connect(lambda: self.change_theme(True))
        dark_layout.addWidget(self.dark_theme_btn, alignment=Qt.AlignCenter)
        
        themes_layout.addStretch()
        themes_layout.addWidget(light_theme_container)
        themes_layout.addSpacing(50)
        themes_layout.addWidget(dark_theme_container)
        themes_layout.addStretch()
        
        theme_layout.addWidget(themes_container)
        
        current_theme_label = QLabel(f"Текущая тема: {'Светлая' if not self.current_theme else 'Тёмная'}")
        current_theme_label.setFont(QFont("Montserrat", 14))
        current_theme_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        current_theme_label.setAlignment(Qt.AlignCenter)
        theme_layout.addWidget(current_theme_label)
        self.current_theme_label = current_theme_label
        
        theme_layout.addStretch()
        
        theme_frame = QFrame()
        theme_frame.setLayout(theme_layout)
        
        notif_card = QWidget()
        notif_layout = QVBoxLayout(notif_card)
        notif_layout.setContentsMargins(30, 30, 30, 30)
        notif_layout.setSpacing(30)
        
        notif_title = QLabel("Настройки уведомлений")
        notif_title.setObjectName("card_title")
        notif_title.setFont(QFont("Montserrat", 28, QFont.Bold))
        notif_title.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'};")
        notif_title.setAlignment(Qt.AlignCenter)
        notif_layout.addWidget(notif_title)
        notif_layout.addSpacing(20)
        
        user_notif_container = QWidget()
        user_notif_layout = QHBoxLayout(user_notif_container)
        user_notif_layout.setContentsMargins(0, 0, 0, 0)
        
        user_notif_label = QLabel("Уведомления о новых пользователях:")
        user_notif_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        user_notif_label.setFixedWidth(300)
        user_notif_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.user_notif_toggle = QPushButton("Включено" if self.user_notifications_enabled else "Выключено")
        self.user_notif_toggle.setObjectName("user_notif_toggle")
        self.user_notif_toggle.setFixedSize(150, 40)
        self.user_notif_toggle.setFont(QFont("Montserrat", 12))
        self.user_notif_toggle.setStyleSheet(f"background-color: {'#47D155' if self.user_notifications_enabled else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")
        self.user_notif_toggle.setCheckable(True)
        self.user_notif_toggle.setChecked(self.user_notifications_enabled)
        self.user_notif_toggle.clicked.connect(self.toggle_user_notifications)
        
        user_notif_layout.addWidget(user_notif_label)
        user_notif_layout.addWidget(self.user_notif_toggle)
        user_notif_layout.addStretch()
        notif_layout.addWidget(user_notif_container)
        
        sound_notif_container = QWidget()
        sound_notif_layout = QHBoxLayout(sound_notif_container)
        sound_notif_layout.setContentsMargins(0, 0, 0, 0)
        
        sound_notif_label = QLabel("Звуковые уведомления:")
        sound_notif_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        sound_notif_label.setFixedWidth(300)
        sound_notif_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.sound_notif_toggle = QPushButton("Включено" if self.sound_notifications_enabled else "Выключено")
        self.sound_notif_toggle.setObjectName("sound_notif_toggle")
        self.sound_notif_toggle.setFixedSize(150, 40)
        self.sound_notif_toggle.setFont(QFont("Montserrat", 12))
        self.sound_notif_toggle.setStyleSheet(f"background-color: {'#47D155' if self.sound_notifications_enabled else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")
        self.sound_notif_toggle.setCheckable(True)
        self.sound_notif_toggle.setChecked(self.sound_notifications_enabled)
        self.sound_notif_toggle.clicked.connect(self.toggle_sound_notifications)
        
        sound_notif_layout.addWidget(sound_notif_label)
        sound_notif_layout.addWidget(self.sound_notif_toggle)
        sound_notif_layout.addStretch()
        notif_layout.addWidget(sound_notif_container)
        
        interval_container = QWidget()
        interval_layout = QHBoxLayout(interval_container)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        
        interval_label = QLabel("Интервал проверки (секунды):")
        interval_label.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#CCCCCC'};")
        interval_label.setFixedWidth(300)
        interval_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.interval_input = QLineEdit(str(self.notification_interval // 1000))
        self.interval_input.setFixedWidth(150)
        self.interval_input.setStyleSheet(f"color: {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border: 2px solid {'#0D0D0D' if not self.current_theme else '#FFFFFF'}; border-radius: 15px; padding: 10px; background-color: {'#FFFFFF' if not self.current_theme else '#3D3D3D'};")
        self.interval_input.setAlignment(Qt.AlignCenter)
        
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_input)
        interval_layout.addStretch()
        notif_layout.addWidget(interval_container)
        
        save_notif_btn = QPushButton("Сохранить настройки")
        save_notif_btn.setFixedSize(300, 50)
        save_notif_btn.setFont(QFont("Montserrat", 14))
        save_notif_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")
        save_notif_btn.clicked.connect(self.save_notification_settings)
        notif_layout.addWidget(save_notif_btn, alignment=Qt.AlignCenter)
        
        notif_layout.addStretch()
        
        notif_frame = QFrame()
        notif_frame.setLayout(notif_layout)
        
        self.settings_stack.addWidget(profile_frame)
        self.settings_stack.addWidget(theme_frame)
        self.settings_stack.addWidget(notif_frame)
        
        nav_container = QWidget()
        nav_layout = QHBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 20, 0, 0)
        
        self.prev_btn = QPushButton("←")
        self.prev_btn.setFixedSize(60, 60)
        self.prev_btn.setFont(QFont("Montserrat", 24))
        self.prev_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")
        self.prev_btn.clicked.connect(self.prev_settings_card)
        
        self.next_btn = QPushButton("→")
        self.next_btn.setFixedSize(60, 60)
        self.next_btn.setFont(QFont("Montserrat", 24))
        self.next_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")
        self.next_btn.clicked.connect(self.next_settings_card)
        
        indicators_container = QWidget()
        indicators_container.setFixedHeight(60)
        indicators_layout = QHBoxLayout(indicators_container)
        indicators_layout.setAlignment(Qt.AlignCenter)
        indicators_layout.setSpacing(15)
        indicators_layout.setContentsMargins(0, 0, 0, 0)
        
        self.indicators = []
        for i in range(3):
            indicator = QFrame()
            indicator.setFixedSize(15, 15)
            indicator.setStyleSheet(f"background-color: {'#CCCCCC' if not self.current_theme else '#666666'}; border-radius: 7px;")
            indicators_layout.addWidget(indicator)
            self.indicators.append(indicator)
        
        self.indicators[0].setStyleSheet("background-color: #0554F2; border-radius: 7px;")
        
        nav_layout.addStretch(1)
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addStretch(2)
        nav_layout.addWidget(indicators_container)
        nav_layout.addStretch(2)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch(1)
        
        layout.addWidget(self.settings_stack)
        layout.addWidget(nav_container)

    # Переключение на предыдущую карточку настроек
    def prev_settings_card(self):
        current_index = self.settings_stack.currentIndex()
        if current_index > 0:
            self.settings_stack.setCurrentIndex(current_index - 1)
            self.update_indicators(current_index - 1)

    # Переключение на следующую карточку настроек
    def next_settings_card(self):
        current_index = self.settings_stack.currentIndex()
        if current_index < self.settings_stack.count() - 1:
            self.settings_stack.setCurrentIndex(current_index + 1)
            self.update_indicators(current_index + 1)

    # Обновление индикаторов активной карточки
    def update_indicators(self, active_index):
        for i, indicator in enumerate(self.indicators):
            if i == active_index:
                indicator.setStyleSheet("background-color: #0554F2; border-radius: 7px;")
            else:
                indicator.setStyleSheet(f"background-color: {'#CCCCCC' if not self.current_theme else '#666666'}; border-radius: 7px;")

    # Сохранение настроек профиля
    def save_profile_settings(self):
        new_username = self.username_input.text().strip()
        old_password = self.old_password_input.text().strip()
        new_password = self.new_password_input.text().strip()
        
        if not new_username:
            QMessageBox.warning(self, "Ошибка", "Имя пользователя не может быть пустым!")
            return
            
        try:
            session = Connect.create_connection()
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
            
            self.old_password_input.clear()
            self.new_password_input.clear()
            
            QMessageBox.information(self, "Успех", "Настройки профиля успешно сохранены!")
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек профиля: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить настройки профиля.")

    # Смена темы интерфейса
    def change_theme(self, theme):
        self.current_theme = theme
        if not theme:
            self.current_theme_label.setText("Текущая тема: Светлая")
            self.apply_light_theme()
        else:
            self.current_theme_label.setText("Текущая тема: Тёмная")
            self.apply_dark_theme()
        
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            if admin:
                admin.theme = self.current_theme
                session.commit()
            session.close()
            logging.info(f"Тема изменена на: {'Светлая' if not theme else 'Тёмная'}")
        except Exception as e:
            logging.error(f"Ошибка сохранения темы: {e}")

    # Обновление стилей списка задач в зависимости от темы
    def update_tasks_list_style(self):
        if not self.current_theme:
            # Светлая тема для списка задач
            self.tasks_list.setStyleSheet("""
                QListWidget {
                    background-color: #F2F2F2; /* Фон списка */
                    color: #0D0D0D; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #CCCCCC; /* Граница полосы прокрутки */
                    background: #E5E5E5; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)
        else:
            # Тёмная тема для списка задач
            self.tasks_list.setStyleSheet("""
                QListWidget {
                    background-color: #2D2D2D; /* Фон списка */
                    color: #FFFFFF; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #555555; /* Граница полосы прокрутки */
                    background: #3D3D3D; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)

    # Обновление стилей списка сотрудников в зависимости от темы
    def update_employees_list_style(self):
        if not self.current_theme:
            # Светлая тема для списка сотрудников
            self.employees_list.setStyleSheet("""
                QListWidget {
                    background-color: #F2F2F2; /* Фон списка */
                    color: #0D0D0D; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #CCCCCC; /* Граница полосы прокрутки */
                    background: #E5E5E5; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)
        else:
            # Тёмная тема для списка сотрудников
            self.employees_list.setStyleSheet("""
                QListWidget {
                    background-color: #2D2D2D; /* Фон списка */
                    color: #FFFFFF; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #555555; /* Граница полосы прокрутки */
                    background: #3D3D3D; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)
        self.employees_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Установка политики отображения полосы прокрутки

    # Обновление стилей списка неподтверждённых сотрудников в зависимости от темы
    def update_unconfirmed_list_style(self):
        if not self.current_theme:
            # Светлая тема для списка неподтверждённых сотрудников
            self.unconfirmed_list.setStyleSheet("""
                QListWidget {
                    background-color: #F2F2F2; /* Фон списка */
                    color: #0D0D0D; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #CCCCCC; /* Граница полосы прокрутки */
                    background: #E5E5E5; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #E5E5E5; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)
        else:
            # Тёмная тема для списка неподтверждённых сотрудников
            self.unconfirmed_list.setStyleSheet("""
                QListWidget {
                    background-color: #2D2D2D; /* Фон списка */
                    color: #FFFFFF; /* Цвет текста */
                    border: none; /* Без границы */
                    padding: 0px; /* Без отступов */
                    margin: 0px; /* Без внешних отступов */
                }
                QScrollBar:vertical {
                    border: 1px solid #555555; /* Граница полосы прокрутки */
                    background: #3D3D3D; /* Фон полосы прокрутки */
                    width: 14px; /* Ширина полосы */
                    margin: 22px 0 22px 0; /* Отступы сверху и снизу */
                    border-radius: 7px; /* Закругление углов */
                }
                QScrollBar::handle:vertical {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0554F2, stop:1 #0443C2); /* Градиент ручки */
                    min-height: 30px; /* Минимальная высота ручки */
                    border-radius: 5px; /* Закругление углов ручки */
                }
                QScrollBar::handle:vertical:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0443C2, stop:1 #0335A2); /* Градиент при наведении */
                }
                QScrollBar::handle:vertical:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0335A2, stop:1 #022582); /* Градиент при нажатии */
                }
                QScrollBar::add-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки добавления */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: bottom; /* Положение внизу */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-bottom-left-radius: 7px; /* Закругление нижнего левого угла */
                    border-bottom-right-radius: 7px; /* Закругление нижнего правого угла */
                }
                QScrollBar::sub-line:vertical {
                    border: none; /* Без границы */
                    background: #3D3D3D; /* Фон кнопки вычитания */
                    height: 20px; /* Высота кнопки */
                    subcontrol-position: top; /* Положение сверху */
                    subcontrol-origin: margin; /* Происхождение отступа */
                    border-top-left-radius: 7px; /* Закругление верхнего левого угла */
                    border-top-right-radius: 7px; /* Закругление верхнего правого угла */
                }
                QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                    background: none; /* Без фона для стрелок */
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none; /* Без фона для страниц */
                }
            """)

    # Применение светлой темы ко всем элементам интерфейса
    def apply_light_theme(self):
        self.current_theme = False
        self.centralWidget().setStyleSheet("background-color: #F2F2F2;")  # Фон главного виджета
        self.confirmation_page.setStyleSheet("background-color: #F2F2F2;")  # Фон страницы подтверждения
        nav_frame = self.findChild(QFrame, "", Qt.FindDirectChildrenOnly)
        if nav_frame:
            nav_frame.setStyleSheet("background-color: #0554F2; border-radius: 60px;")  # Стили панели навигации

        # Обновление стилей карточек настроек
        for i in range(self.settings_stack.count()):
            frame = self.settings_stack.widget(i)
            frame.setStyleSheet("background-color: #FFFFFF; border-radius: 20px;")  # Фон карточки
            for child in frame.findChildren(QWidget):
                if isinstance(child, QLabel) and child.objectName() == "card_title":
                    child.setStyleSheet("color: #0D0D0D;")  # Цвет заголовка карточки
                elif isinstance(child, QLabel) and child.objectName() != "card_title":
                    child.setStyleSheet("color: #0D0D0D;")  # Цвет остальных меток
                elif isinstance(child, QLineEdit):
                    child.setStyleSheet("color: #0D0D0D; border: 2px solid #0D0D0D; border-radius: 15px; padding: 10px; background-color: #FFFFFF;")  # Стили полей ввода
                elif isinstance(child, QPushButton) and child.objectName() in ["user_notif_toggle", "sound_notif_toggle"]:
                    child.setStyleSheet(f"background-color: {'#47D155' if child.isChecked() else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")  # Стили переключателей уведомлений
                elif isinstance(child, QPushButton):
                    child.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")  # Стили остальных кнопок

        # Обновление индикаторов активной карточки настроек
        active_index = self.settings_stack.currentIndex()
        for i, indicator in enumerate(self.indicators):
            if i == active_index:
                indicator.setStyleSheet("background-color: #0554F2; border-radius: 7px;")  # Активный индикатор
            else:
                indicator.setStyleSheet("background-color: #CCCCCC; border-radius: 7px;")  # Неактивные индикаторы

        self.prev_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")  # Кнопка "Назад"
        self.next_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")  # Кнопка "Вперёд"

        # Обновление стилей списка задач
        self.update_tasks_list_style()
        for delegate in self.tasks_list.findChildren(TaskItemDelegate):
            delegate.set_theme(False)  # Установка светлой темы для делегата
        self.tasks_list.viewport().update()  # Обновление области просмотра

        # Обновление стилей списка сотрудников
        self.update_employees_list_style()
        for delegate in self.employees_list.findChildren(EmployeeItemDelegate):
            delegate.set_theme(False)  # Установка светлой темы для делегата
        for i in range(self.employees_list.count()):
            item = self.employees_list.item(i)
            container = self.employees_list.itemWidget(item)
            widget = None
            for child in container.findChildren(EmployeeWidget):
                widget = child
                break
            if widget:
                widget.update_styles(False)  # Обновление стилей виджета сотрудника
                widget.setFixedSize(900, 150)  # Фиксированный размер виджета
                widget.update()
                widget.repaint()
                container.update()
                container.repaint()
        self.employees_list.updateGeometry()  # Обновление геометрии списка
        self.employees_list.viewport().update()  # Обновление области просмотра
        self.employees_list.repaint()  # Перерисовка списка

        # Обновление стилей списка неподтверждённых сотрудников
        self.update_unconfirmed_list_style()
        for delegate in self.unconfirmed_list.findChildren(UnconfirmedEmployeeItemDelegate):
            delegate.set_theme(False)  # Установка светлой темы для делегата
        for i in range(self.unconfirmed_list.count()):
            item = self.unconfirmed_list.item(i)
            container = self.unconfirmed_list.itemWidget(item)
            widget = None
            for child in container.findChildren(UnconfirmedEmployeeWidget):
                widget = child
                break
            if widget:
                widget.update_styles(False)  # Обновление стилей виджета
                widget.setMinimumSize(self.unconfirmed_list.width() - 10, 150)  # Минимальный размер виджета
                widget.update()
                widget.repaint()
                container.update()
                container.repaint()
        self.unconfirmed_list.updateGeometry()  # Обновление геометрии списка
        self.unconfirmed_list.viewport().update()  # Обновление области просмотра
        self.unconfirmed_list.repaint()  # Перерисовка списка

        self.update_header_styles(False)  # Обновление стилей заголовков
        self.no_employees_label.setStyleSheet("color: #0D0D0D;")  # Цвет метки отсутствия сотрудников
        logging.info("Светлая тема применена")  # Логирование применения темы

    # Применение тёмной темы ко всем элементам интерфейса
    def apply_dark_theme(self):
        self.current_theme = True
        self.centralWidget().setStyleSheet("background-color: #2D2D2D;")  # Фон главного виджета
        self.confirmation_page.setStyleSheet("background-color: #2D2D2D;")  # Фон страницы подтверждения
        nav_frame = self.findChild(QFrame, "", Qt.FindDirectChildrenOnly)
        if nav_frame:
            nav_frame.setStyleSheet("background-color: #0445C0; border-radius: 60px;")  # Стили панели навигации

        # Обновление стилей карточек настроек
        for i in range(self.settings_stack.count()):
            frame = self.settings_stack.widget(i)
            frame.setStyleSheet("background-color: #3D3D3D; border-radius: 20px;")  # Фон карточки
            for child in frame.findChildren(QWidget):
                if isinstance(child, QLabel) and child.objectName() == "card_title":
                    child.setStyleSheet("color: #FFFFFF;")  # Цвет заголовка карточки
                elif isinstance(child, QLabel) and child.objectName() != "card_title":
                    child.setStyleSheet("color: #CCCCCC;")  # Цвет остальных меток
                elif isinstance(child, QLineEdit):
                    child.setStyleSheet("color: #FFFFFF; border: 2px solid #FFFFFF; border-radius: 15px; padding: 10px; background-color: #3D3D3D;")  # Стили полей ввода
                elif isinstance(child, QPushButton) and child.objectName() in ["user_notif_toggle", "sound_notif_toggle"]:
                    child.setStyleSheet(f"background-color: {'#47D155' if child.isChecked() else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")  # Стили переключателей уведомлений
                elif isinstance(child, QPushButton):
                    child.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 15px; border: none;")  # Стили остальных кнопок

        # Обновление индикаторов активной карточки настроек
        active_index = self.settings_stack.currentIndex()
        for i, indicator in enumerate(self.indicators):
            if i == active_index:
                indicator.setStyleSheet("background-color: #0554F2; border-radius: 7px;")  # Активный индикатор
            else:
                indicator.setStyleSheet("background-color: #666666; border-radius: 7px;")  # Неактивные индикаторы

        self.prev_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")  # Кнопка "Назад"
        self.next_btn.setStyleSheet("background-color: #0554F2; color: #F2F2F2; border-radius: 30px; border: none;")  # Кнопка "Вперёд"

        # Обновление стилей списка задач
        self.update_tasks_list_style()
        for delegate in self.tasks_list.findChildren(TaskItemDelegate):
            delegate.set_theme(True)  # Установка тёмной темы для делегата
        self.tasks_list.viewport().update()  # Обновление области просмотра

        # Обновление стилей списка сотрудников
        self.update_employees_list_style()
        for delegate in self.employees_list.findChildren(EmployeeItemDelegate):
            delegate.set_theme(True)  # Установка тёмной темы для делегата
        for i in range(self.employees_list.count()):
            item = self.employees_list.item(i)
            container = self.employees_list.itemWidget(item)
            widget = None
            for child in container.findChildren(EmployeeWidget):
                widget = child
                break
            if widget:
                widget.update_styles(True)  # Обновление стилей виджета сотрудника
                widget.setFixedSize(900, 150)  # Фиксированный размер виджета
                widget.update()
                widget.repaint()
                container.update()
                container.repaint()
        self.employees_list.updateGeometry()  # Обновление геометрии списка
        self.employees_list.viewport().update()  # Обновление области просмотра
        self.employees_list.repaint()  # Перерисовка списка

        # Обновление стилей списка неподтверждённых сотрудников
        self.update_unconfirmed_list_style()
        for delegate in self.unconfirmed_list.findChildren(UnconfirmedEmployeeItemDelegate):
            delegate.set_theme(True)  # Установка тёмной темы для делегата
        for i in range(self.unconfirmed_list.count()):
            item = self.unconfirmed_list.item(i)
            container = self.unconfirmed_list.itemWidget(item)
            widget = None
            for child in container.findChildren(UnconfirmedEmployeeWidget):
                widget = child
                break
            if widget:
                widget.update_styles(True)  # Обновление стилей виджета
                widget.setMinimumSize(self.unconfirmed_list.width() - 10, 150)  # Минимальный размер виджета
                widget.update()
                widget.repaint()
                container.update()
                container.repaint()
        self.unconfirmed_list.updateGeometry()  # Обновление геометрии списка
        self.unconfirmed_list.viewport().update()  # Обновление области просмотра
        self.unconfirmed_list.repaint()  # Перерисовка списка

        self.update_header_styles(True)  # Обновление стилей заголовков
        self.no_employees_label.setStyleSheet("color: #FFFFFF;")  # Цвет метки отсутствия сотрудников
        logging.info("Тёмная тема применена")  # Логирование применения темы

    # Обновление стилей заголовков страниц
    def update_header_styles(self, dark_theme):
        text_color = "#0D0D0D" if not dark_theme else "#FFFFFF"  # Выбор цвета текста
        for label in [self.findChild(QLabel, "tasks_label"), self.findChild(QLabel, "employees_label"), 
                      self.findChild(QLabel, "confirmation_label"), self.findChild(QLabel, "settings_label")]:
            if label:
                label.setStyleSheet(f"color: {text_color}; background: transparent;")  # Применение стилей к заголовкам

    # Загрузка списка сотрудников из базы данных
    def load_employees(self):
        try:
            session = Connect.create_connection()
            employees = session.query(User).filter_by(is_confirmed=True).all()
            self.employees_list.clear()  # Очистка списка
            logging.debug(f"Ширина employees_list: {self.employees_list.width()}")
            if not employees:
                self.no_employees_label.setVisible(True)  # Показ метки при отсутствии сотрудников
            else:
                self.no_employees_label.setVisible(False)  # Скрытие метки
                for employee in employees:
                    task_count = session.query(TaskLog).filter_by(user_id=employee.id).count()  # Подсчёт задач сотрудника
                    widget = EmployeeWidget(employee, task_count)  # Создание виджета сотрудника
                    widget.update_styles(self.current_theme)  # Обновление стилей виджета
                    widget.setFixedSize(900, 150)  # Фиксированный размер виджета
                    logging.debug(f"Размер карточки: {widget.size()}")
                    container = QWidget()
                    container_layout = QVBoxLayout(container)
                    container_layout.setContentsMargins(10, 30, 10, 30)  # Отступы контейнера
                    container_layout.addWidget(widget)
                    container.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Включение обработки событий мыши
                    item = QListWidgetItem(self.employees_list)
                    item.setData(Qt.UserRole, employee)  # Сохранение данных сотрудника
                    item.setSizeHint(QSize(900, 150 + 30 + 30))  # Установка размера элемента
                    self.employees_list.addItem(item)
                    self.employees_list.setItemWidget(item, container)  # Установка виджета в элемент списка
            session.close()
            self.employees_list.updateGeometry()  # Обновление геометрии списка
            self.employees_list.viewport().update()  # Обновление области просмотра
            self.employees_list.repaint()  # Перерисовка списка
            self.employees_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)  # Полоса прокрутки всегда видна
        except Exception as e:
            logging.error(f"Ошибка загрузки сотрудников: {e}")
            self.no_employees_label.setVisible(True)  # Показ метки при ошибке
            session.close()

    # Загрузка списка неподтверждённых сотрудников
    def load_unconfirmed_employees(self):
        try:
            session = Connect.create_connection()
            unconfirmed_users = session.query(User).filter_by(is_confirmed=False).all()
            self.unconfirmed_list.clear()  # Очистка списка
            for user in unconfirmed_users:
                widget = UnconfirmedEmployeeWidget(
                    user,
                    lambda u=user: self.confirm_user(u),  # Функция подтверждения
                    lambda u=user: self.delete_user(u)  # Функция удаления
                )
                widget.update_styles(self.current_theme)  # Обновление стилей виджета
                widget.setMinimumSize(self.unconfirmed_list.width() - 10, 150)  # Минимальный размер виджета
                container = QWidget()
                container_layout = QVBoxLayout(container)
                container_layout.setContentsMargins(0, 30, 0, 30)  # Отступы контейнера
                container_layout.addWidget(widget)
                item = QListWidgetItem(self.unconfirmed_list)
                item.setData(Qt.UserRole, user)  # Сохранение данных пользователя
                item.setSizeHint(QSize(self.unconfirmed_list.width() - 20, 150 + 30 + 30))  # Установка размера элемента
                self.unconfirmed_list.addItem(item)
                self.unconfirmed_list.setItemWidget(item, container)  # Установка виджета в элемент списка
            session.close()
            self.unconfirmed_list.updateGeometry()  # Обновление геометрии списка
            self.unconfirmed_list.viewport().update()  # Обновление области просмотра
            self.unconfirmed_list.repaint()  # Перерисовка списка
        except Exception as e:
            logging.error(f"Ошибка загрузки неподтверждённых пользователей: {e}")
            session.close()

    # Загрузка списка задач
    def load_tasks(self):
        try:
            session = Connect.create_connection()
            tasks = session.query(Task).all()
            self.tasks_list.clear()  # Очистка списка
            for task in tasks:
                item = QListWidgetItem(self.tasks_list)
                item.setData(Qt.UserRole, task)  # Сохранение данных задачи
                item.setSizeHint(QSize(900, 160))  # Установка размера элемента
                self.tasks_list.addItem(item)
            session.close()
            self.tasks_list.viewport().update()  # Обновление области просмотра
        except Exception as e:
            logging.error(f"Ошибка загрузки задач: {e}")
            session.close()

    # Добавление новой задачи
    def add_task(self):
        dialog = TaskEditDialog(self.current_theme, parent=self)  # Открытие диалога редактирования задачи
        if dialog.exec():
            new_task = dialog.get_task_data()  # Получение данных задачи (title, priority, description)
            try:
                session = Connect.create_connection()
                task = Task(
                    title=new_task[0],
                    priority=new_task[1],  # Приоритет как строка
                    description=new_task[2]
                )
                session.add(task)
                session.commit()
                self.load_tasks()  # Обновление списка задач
                session.close()
                logging.info(f"Задача добавлена: {new_task[0]}")
            except Exception as e:
                logging.error(f"Ошибка добавления задачи: {e}")
                session.rollback()
                session.close()
                QMessageBox.critical(self, "Ошибка", "Не удалось добавить задачу.")  # Сообщение об ошибке

    # Открытие диалога редактирования задачи
    def open_task_edit_dialog(self, item):
        task = item.data(Qt.UserRole)
        dialog = TaskEditDialog(self.current_theme, task, parent=self)  # Диалог редактирования
        if dialog.exec():
            updated_task = dialog.get_task_data()  # Получение обновлённых данных
            try:
                session = Connect.create_connection()
                task = session.query(Task).filter_by(id=task.id).first()
                task.title = updated_task[0]
                task.priority = updated_task[1]  # Приоритет как строка
                task.description = updated_task[2]
                session.commit()
                self.load_tasks()  # Обновление списка задач
                session.close()
                logging.info(f"Задача обновлена: {task.title}")
            except Exception as e:
                logging.error(f"Ошибка обновления задачи: {e}")
                session.rollback()
                session.close()

    # Отладочная функция для клика по сотруднику
    def debug_item_click(self, item):
        employee = item.data(Qt.UserRole)
        logging.debug(f"Clicked employee: {employee.username or employee.email or str(employee.id)}")
        dialog = EmployeeEditDialog(employee, self.current_theme, parent=self)  # Диалог редактирования сотрудника
        if dialog.exec():
            self.load_employees()  # Обновление списка сотрудников

    # Подтверждение пользователя
    def confirm_user(self, user):
        try:
            session = Connect.create_connection()
            user = session.query(User).filter_by(id=user.id).first()
            if user:
                user.is_confirmed = True
                session.commit()
                self.load_unconfirmed_employees()  # Обновление списка неподтверждённых
                self.load_employees()  # Обновление списка сотрудников
                session.close()
                if self.user_notifications_enabled:
                    notify_and_show_menu(user.id, self.sound_notifications_enabled)  # Уведомление
                logging.info(f"Пользователь подтверждён: {user.login}")
            else:
                logging.warning(f"Пользователь не найден: {user.id}")
        except Exception as e:
            logging.error(f"Ошибка подтверждения пользователя: {e}")
            session.rollback()
            session.close()

    # Удаление пользователя
    def delete_user(self, user):
        try:
            session = Connect.create_connection()
            user = session.query(User).filter_by(id=user.id).first()
            if user:
                session.delete(user)
                session.commit()
                self.load_unconfirmed_employees()  # Обновление списка неподтверждённых
                self.load_employees()  # Обновление списка сотрудников
                logging.info(f"Пользователь удалён: {user.login}")
            else:
                logging.warning(f"Пользователь не найден: {user.id}")
            session.close()
        except Exception as e:
            logging.error(f"Ошибка удаления пользователя: {e}")
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Ошибка", "Не удалось удалить пользователя.")  # Сообщение об ошибке

    # Переключение уведомлений о новых пользователях
    def toggle_user_notifications(self):
        self.user_notifications_enabled = not self.user_notifications_enabled
        self.user_notif_toggle.setText("Включено" if self.user_notifications_enabled else "Выключено")  # Обновление текста
        self.user_notif_toggle.setStyleSheet(f"background-color: {'#47D155' if self.user_notifications_enabled else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")  # Обновление стиля
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            if admin:
                admin.new_user_notifications = self.user_notifications_enabled
                session.commit()
            session.close()
            logging.info(f"Уведомления о новых пользователях: {self.user_notifications_enabled}")
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек уведомлений: {e}")

    # Переключение звуковых уведомлений
    def toggle_sound_notifications(self):
        self.sound_notifications_enabled = not self.sound_notifications_enabled
        self.sound_notif_toggle.setText("Включено" if self.sound_notifications_enabled else "Выключено")  # Обновление текста
        self.sound_notif_toggle.setStyleSheet(f"background-color: {'#47D155' if self.sound_notifications_enabled else '#EB3232'}; color: #F2F2F2; border-radius: 15px; border: none;")  # Обновление стиля
        try:
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            if admin:
                admin.sound_notifications = self.sound_notifications_enabled
                session.commit()
            session.close()
            logging.info(f"Звуковые уведомления: {self.sound_notifications_enabled}")
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек звуковых уведомлений: {e}")

    # Сохранение настроек уведомлений
    def save_notification_settings(self):
        try:
            interval = int(self.interval_input.text()) * 1000  # Преобразование секунд в миллисекунды
            if interval < 1000:
                QMessageBox.warning(self, "Ошибка", "Интервал должен быть не менее 1 секунды!")
                return
            self.notification_interval = interval
            self.timer.stop()
            self.timer.start(self.notification_interval)  # Перезапуск таймера с новым интервалом
            session = Connect.create_connection()
            admin = session.query(Admin).filter_by(login=self.login).first()
            if admin:
                admin.notification_interval = self.notification_interval
                session.commit()
            session.close()
            logging.info(f"Интервал уведомлений изменён на: {self.notification_interval} мс")
            QMessageBox.information(self, "Успех", "Настройки уведомлений сохранены!")
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректное число для интервала!")  # Ошибка ввода
        except Exception as e:
            logging.error(f"Ошибка сохранения настроек уведомлений: {e}")
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить настройки уведомлений.")  # Общая ошибка

    # Получение количества неподтверждённых пользователей
    def get_unconfirmed_count(self):
        try:
            session = Connect.create_connection()
            count = session.query(User).filter_by(is_confirmed=False).count()
            session.close()
            return count
        except Exception as e:
            logging.error(f"Ошибка получения количества неподтверждённых пользователей: {e}")
            session.close()
            return 0

    # Получение количества подтверждённых сотрудников
    def get_employee_count(self):
        try:
            session = Connect.create_connection()
            count = session.query(User).filter_by(is_confirmed=True).count()
            session.close()
            return count
        except Exception as e:
            logging.error(f"Ошибка получения количества сотрудников: {e}")
            session.close()
            return 0

    # Проверка новых пользователей и показ уведомлений
    def check_new_users(self):
        current_unconfirmed_count = self.get_unconfirmed_count()
        current_employee_count = self.get_employee_count()

        if self.user_notifications_enabled:
            if current_unconfirmed_count > self.last_unconfirmed_count:
                diff = current_unconfirmed_count - self.last_unconfirmed_count
                notification = NotificationWidget(
                    f"Новые пользователи ({diff}) ожидают подтверждения.",
                    self.current_theme,
                    self
                )
                notification.show_notification()  # Показ уведомления
                logging.info(f"Уведомление: Новые пользователи ({diff})")
            elif current_employee_count > self.last_employee_count:
                diff = current_employee_count - self.last_employee_count
                notification = NotificationWidget(
                    f"Новые сотрудники ({diff}) добавлены.",
                    self.current_theme,
                    self
                )
                notification.show_notification()  # Показ уведомления
                logging.info(f"Уведомление: Новые сотрудники ({diff})")

        self.last_unconfirmed_count = current_unconfirmed_count
        self.last_employee_count = current_employee_count

    # Выход из системы
    def logout(self):
        self.hide()  # Скрытие текущего окна
        self.login_window = LoginWindow()  # Открытие окна авторизации
        self.login_window.show()
        logging.info("Выход из системы")  # Логирование выхода

    # Обработка изменения размера окна
    def resizeEvent(self, event):
        super().resizeEvent(event)
        for i in range(self.unconfirmed_list.count()):
            item = self.unconfirmed_list.item(i)
            widget = self.unconfirmed_list.itemWidget(item)
            if isinstance(widget, UnconfirmedEmployeeWidget):
                widget.setMinimumSize(self.unconfirmed_list.width() - 10, 150)  # Обновление минимального размера
                item.setSizeHint(QSize(self.unconfirmed_list.width() - 20, 150 + 30 + 30))  # Обновление размера элемента
        self.unconfirmed_list.viewport().update()  # Обновление области просмотра