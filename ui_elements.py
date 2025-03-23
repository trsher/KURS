from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt, QSize, QUrl
from PySide6.QtGui import QFont, QPainter, QPen, QPixmap, QBrush, QColor, QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

# Кэш для аватаров
avatar_cache = {}

class CustomAddButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(100, 100)
        self.setStyleSheet("""
            QPushButton {
                border-radius: 40px;
                background-color: #0554F2;
                padding: 0;
                margin: 0;
            }
            QPushButton:hover {
                background-color: #0443C2;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(Qt.white, 10)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2
        line_length = 60
        half_length = line_length // 2
        painter.drawLine(center_x, center_y - half_length, center_x, center_y + half_length)
        painter.drawLine(center_x - half_length, center_y, center_x + half_length, center_y)

class RoundedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedSize(900, 100)
        font = QFont("Montserrat", 42)
        font.setWeight(QFont.Bold)
        self.setFont(font)
        self.normal_color = QColor("#3889F2")
        self.hover_color = QColor("#2A6FD6")
        self.text_color = QColor("#F2F2F2")
        self.radius = 60
        self.is_hovered = False

    def enterEvent(self, event):
        self.is_hovered = True
        self.update()

    def leaveEvent(self, event):
        self.is_hovered = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(self.hover_color if self.is_hovered else self.normal_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.radius, self.radius)
        painter.setPen(self.text_color)
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

class AvatarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(128, 128)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("border-radius: 64px; background: transparent; margin: 20px;")
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_avatar_downloaded)

    def load_avatar(self, photo_url):
        default_avatar_path = "icons/image.png"
        try:
            if not photo_url:
                self.load_default_avatar(default_avatar_path)
                return
            if photo_url in avatar_cache:
                self.avatar_label.setPixmap(self.round_pixmap(avatar_cache[photo_url]))
                return
            if not photo_url.startswith("http"):
                pixmap = QPixmap(photo_url)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(128, 128, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    avatar_cache[photo_url] = pixmap
                    self.avatar_label.setPixmap(self.round_pixmap(pixmap))
                else:
                    self.load_default_avatar(default_avatar_path)
                return
            self.manager.get(QNetworkRequest(QUrl(photo_url)))
        except Exception as e:
            print(f"Ошибка загрузки аватара: {e}")
            self.load_default_avatar(default_avatar_path)

    def on_avatar_downloaded(self, reply):
        default_avatar_path = "icons/image.png"
        try:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(128, 128, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                rounded_pixmap = self.round_pixmap(pixmap)
                avatar_cache[reply.url().toString()] = pixmap
                self.avatar_label.setPixmap(rounded_pixmap)
            else:
                self.load_default_avatar(default_avatar_path)
        except Exception as e:
            print(f"Ошибка обработки аватара: {e}")
            self.load_default_avatar(default_avatar_path)
        reply.deleteLater()

    def load_default_avatar(self, default_path):
        pixmap = QPixmap(default_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(128, 128, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(self.round_pixmap(pixmap))
        else:
            print(f"Стандартная аватарка не найдена: {default_path}")
            self.avatar_label.setText("Нет фото")

    def round_pixmap(self, pixmap):
        size = pixmap.size()
        rounded = QPixmap(size)
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(Qt.black))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size.width(), size.height())
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        pen = QPen(QColor("#0D0D0D"), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(1, 1, size.width() - 2, size.height() - 2)
        painter.end()
        return rounded

class EmployeeWidget(AvatarWidget):
    def __init__(self, user, completed_tasks, parent=None):
        super().__init__(parent)
        self.user = user
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.avatar_label)

        user_info = QVBoxLayout()
        username_label = QLabel(user.username or user.email or "No Name")
        username_label.setStyleSheet("color: #0D0D0D; font-size: 18px; font-weight: bold; background: transparent;")
        username_label.setWordWrap(True)
        username_label.setMaximumHeight(50)
        tasks_label = QLabel(f"Выполнено задач: {completed_tasks}")
        tasks_label.setStyleSheet("color: #0D0D0D; font-size: 16px; background: transparent;")
        tasks_label.setWordWrap(True)
        tasks_label.setMaximumHeight(40)
        user_info.addWidget(username_label)
        user_info.addStretch()
        user_info.addWidget(tasks_label)
        user_info_widget = QWidget()
        user_info_widget.setLayout(user_info)
        user_info_widget.setMaximumHeight(128)
        user_info_widget.setStyleSheet("background: transparent;")
        layout.addWidget(user_info_widget, stretch=1)

        self.setFixedHeight(168)
        self.setMaximumWidth(900)
        self.load_avatar(user.photo)

class UnconfirmedEmployeeWidget(AvatarWidget):
    def __init__(self, user, confirm_callback, delete_callback, parent=None):
        super().__init__(parent)
        self.user = user
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)
        layout.addWidget(self.avatar_label)

        user_info = QVBoxLayout()
        user_info.setContentsMargins(0, 0, 0, 0)
        user_info.setSpacing(0)
        username_label = QLabel(user.username or user.email or "No Name")
        username_label.setStyleSheet("color: #0D0D0D; font-size: 18px; font-weight: bold; background: transparent; margin: 0px;")
        username_label.setWordWrap(True)
        username_label.setMaximumHeight(50)
        status_label = QLabel("Ожидает подтверждения")
        status_label.setStyleSheet("color: #0D0D0D; font-size: 16px; background: transparent; margin: 0px;")
        status_label.setWordWrap(True)
        status_label.setMaximumHeight(40)
        user_info.addWidget(username_label)
        user_info.addWidget(status_label)
        user_info_widget = QWidget()
        user_info_widget.setLayout(user_info)
        user_info_widget.setMaximumHeight(128)
        user_info_widget.setStyleSheet("background: transparent; margin: 0px;")
        layout.addWidget(user_info_widget, stretch=5)

        buttons_layout = QVBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        confirm_btn = QPushButton("Подтвердить")
        confirm_btn.setFixedHeight(30)
        confirm_btn.setFixedWidth(100)
        confirm_btn.setStyleSheet("background-color: #44FF44; color: #0D0D0D; border-radius: 5px; padding: 5px; margin: 0px;")
        confirm_btn.clicked.connect(lambda: confirm_callback(self.user.id))
        delete_btn = QPushButton("Удалить")
        delete_btn.setFixedHeight(30)
        delete_btn.setFixedWidth(100)
        delete_btn.setStyleSheet("background-color: #FF4444; color: #0D0D0D; border-radius: 5px; padding: 5px; margin: 0px;")
        delete_btn.clicked.connect(lambda: delete_callback(self.user.id))
        buttons_layout.addWidget(confirm_btn)
        buttons_layout.addWidget(delete_btn)
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        buttons_widget.setStyleSheet("background: transparent; margin: 0px;")
        layout.addWidget(buttons_widget, stretch=1)

        self.setFixedHeight(168)
        self.setMaximumWidth(900)
        self.load_avatar(user.photo)