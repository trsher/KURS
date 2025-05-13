from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFileDialog
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
    def __init__(self, parent=None, clickable=False):
        super().__init__(parent)
        self.avatar_label = QLabel(self)
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setScaledContents(True)
        self.avatar_label.setStyleSheet("border-radius: 40px; background: transparent; margin: 10px;")
        print(f"AvatarWidget инициализирован, размер: {self.avatar_label.size()}")
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.on_avatar_downloaded)
        self.photo_path = None
        self.clickable = clickable
        if clickable:
            self.avatar_label.mousePressEvent = self.load_photo

    def load_avatar(self, photo_url):
        default_avatar_path = "icons/image.png"
        print(f"Загрузка аватара: photo_url={photo_url}")
        try:
            if not photo_url:
                print("Путь к фотографии пустой, загружаем стандартную аватарку")
                self.load_default_avatar(default_avatar_path)
                self.photo_path = None
                return
            if photo_url in avatar_cache:
                print(f"Фотография найдена в кэше: {photo_url}")
                self.avatar_label.setPixmap(self.round_pixmap(avatar_cache[photo_url]))
                self.photo_path = photo_url
                return
            if not photo_url.startswith("http"):
                print(f"Попытка загрузки локального файла: {photo_url}")
                pixmap = QPixmap(photo_url)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(120, 120, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                    avatar_cache[photo_url] = pixmap
                    self.avatar_label.setPixmap(self.round_pixmap(pixmap))
                    self.photo_path = photo_url
                    print("Локальный файл успешно загружен")
                else:
                    print(f"Не удалось загрузить локальный файл: {photo_url}")
                    self.load_default_avatar(default_avatar_path)
                    self.photo_path = None
                return
            print(f"Попытка загрузки фотографии по URL: {photo_url}")
            self.manager.get(QNetworkRequest(QUrl(photo_url)))
        except Exception as e:
            print(f"Ошибка загрузки аватара: {e}")
            self.load_default_avatar(default_avatar_path)
            self.photo_path = None

    def on_avatar_downloaded(self, reply):
        default_avatar_path = "icons/image.png"
        try:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                rounded_pixmap = self.round_pixmap(pixmap)
                avatar_cache[reply.url().toString()] = pixmap
                self.avatar_label.setPixmap(rounded_pixmap)
                self.photo_path = reply.url().toString()
                print(f"Фотография успешно загружена по URL: {self.photo_path}")
            else:
                print("Не удалось загрузить изображение по URL")
                self.load_default_avatar(default_avatar_path)
                self.photo_path = None
        except Exception as e:
            print(f"Ошибка обработки аватара: {e}")
            self.load_default_avatar(default_avatar_path)
            self.photo_path = None
        reply.deleteLater()

    def load_default_avatar(self, default_path):
        print(f"Загрузка стандартной аватарки: {default_path}")
        pixmap = QPixmap(default_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(120, 120, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.avatar_label.setPixmap(self.round_pixmap(pixmap))
            print("Стандартная аватарка успешно загружена")
        else:
            print(f"Стандартная аватарка не найдена: {default_path}")
            self.avatar_label.setText("Нет фото")
        self.photo_path = None

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

    def load_photo(self, event):
        print("Вызов метода load_photo: открытие диалога выбора файла")
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выбрать фотографию", "", "Изображения (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_name:
            pixmap = QPixmap(file_name)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(120, 120, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                avatar_cache[file_name] = pixmap
                self.avatar_label.setPixmap(self.round_pixmap(pixmap))
                self.photo_path = file_name
                print(f"Выбрана новая фотография: {file_name}")
            else:
                print(f"Не удалось загрузить изображение: {file_name}")
                self.load_default_avatar("icons/image.png")
        else:
            print("Выбор файла отменён пользователем")

class EmployeeWidget(AvatarWidget):
    def __init__(self, user, completed_tasks, parent=None):
        super().__init__(parent, clickable=False)
        self.user = user
        self.theme = False
        self.setMinimumSize(900, 150)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setAlignment(Qt.AlignLeft)
        
        self.avatar_label.setFixedSize(120, 120)
        self.avatar_label.setStyleSheet("border-radius: 60px; background: transparent; margin: 15px;")
        layout.addWidget(self.avatar_label)

        user_info = QHBoxLayout()
        self.username_label = QLabel(user.username or user.email or "No Name")
        self.username_label.setFont(QFont("Montserrat", 42, QFont.Bold))
        self.username_label.setStyleSheet("color: #0D0D0D; background: transparent;")
        self.username_label.setWordWrap(True)
        self.tasks_label = QLabel(f"{completed_tasks}")
        self.tasks_label.setFont(QFont("Montserrat", 42, QFont.Bold))
        self.tasks_label.setStyleSheet("color: #0D0D0D; background: transparent;")
        self.tasks_label.setWordWrap(True)
        user_info.addWidget(self.username_label)
        user_info.addStretch()
        user_info.addWidget(self.tasks_label)
        user_info_widget = QWidget()
        user_info_widget.setLayout(user_info)
        user_info_widget.setStyleSheet("background: transparent;")
        layout.addWidget(user_info_widget, stretch=1)

        self.load_avatar(user.photo)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        border_color = "#0D0D0D" if not self.theme else "#F2F2F2"
        bg_color = "#FFFFFF" if not self.theme else "#3D3D3D"
        painter.setPen(QPen(QColor(border_color), 2))
        painter.setBrush(QBrush(QColor(bg_color)))
        card_rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(card_rect, 15, 15)
        painter.end()
        super().paintEvent(event)

    def update_styles(self, theme=False):
        self.theme = theme
        text_color = "#0D0D0D" if not theme else "#FFFFFF"
        self.username_label.setStyleSheet(f"color: {text_color}; background: transparent; font-family: Montserrat; font-size: 42pt; font-weight: bold;")
        self.tasks_label.setStyleSheet(f"color: {text_color}; background: transparent; font-family: Montserrat; font-size: 42pt; font-weight: bold;")
        self.setStyleSheet("")
        self.update()
        self.repaint()

    def sizeHint(self):
        return QSize(900, 150)

class UnconfirmedEmployeeWidget(AvatarWidget):
    def __init__(self, user, confirm_callback, delete_callback, parent=None):
        super().__init__(parent, clickable=False)
        self.user = user
        self.theme = False
        self.setMinimumSize(900, 100)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.avatar_label)

        user_info = QHBoxLayout()
        user_info.setContentsMargins(0, 0, 0, 0)
        self.username_label = QLabel(user.username or user.email or "No Name")
        self.username_label.setFont(QFont("Montserrat", 18))
        self.username_label.setStyleSheet("color: #0D0D0D; font-weight: bold; background: transparent;")
        self.username_label.setWordWrap(True)
        user_info.addWidget(self.username_label)
        user_info.addStretch()
        user_info_widget = QWidget()
        user_info_widget.setLayout(user_info)
        user_info_widget.setStyleSheet("background: transparent; margin: 0px;")
        layout.addWidget(user_info_widget)

        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(10)
        self.confirm_btn = QPushButton("Подтвердить")
        self.confirm_btn.setFixedSize(150, 40)
        self.confirm_btn.setFont(QFont("Montserrat", 14))
        self.confirm_btn.setStyleSheet("background-color: #3889F2; color: #FFFFFF; border-radius: 10px; padding: 5px; margin: 0px; font-weight: bold;")
        self.confirm_btn.clicked.connect(lambda: confirm_callback(self.user))
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.setFixedSize(150, 40)
        self.delete_btn.setFont(QFont("Montserrat", 14))
        self.delete_btn.setStyleSheet("background-color: #FF4444; color: #FFFFFF; border-radius: 10px; padding: 5px; margin: 0px; font-weight: bold;")
        self.delete_btn.clicked.connect(lambda: delete_callback(self.user))
        buttons_layout.addWidget(self.confirm_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_widget = QWidget()
        buttons_widget.setLayout(buttons_layout)
        buttons_widget.setStyleSheet("background: transparent; margin: 0px;")
        layout.addWidget(buttons_widget)

        self.load_avatar(user.photo)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        border_color = "#0D0D0D" if not self.theme else "#F2F2F2"
        bg_color = "#FFFFFF" if not self.theme else "#3D3D3D"
        painter.setPen(QPen(QColor(border_color), 2))
        painter.setBrush(QBrush(QColor(bg_color)))
        card_rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRoundedRect(card_rect, 15, 15)
        painter.end()
        super().paintEvent(event)

    def update_styles(self, theme=False):
        self.theme = theme
        text_color = "#0D0D0D" if not theme else "#FFFFFF"
        confirm_bg = "#3889F2" if not theme else "#2A6FD6"
        delete_bg = "#FF4444" if not theme else "#CC0000"
        self.username_label.setStyleSheet(f"color: {text_color}; font-weight: bold; background: transparent;")
        self.confirm_btn.setStyleSheet(f"background-color: {confirm_bg}; color: #FFFFFF; border-radius: 10px; padding: 5px; margin: 0px; font-weight: bold; font-family: Montserrat; font-size: 14pt;")
        self.delete_btn.setStyleSheet(f"background-color: {delete_bg}; color: #FFFFFF; border-radius: 10px; padding: 5px; margin: 0px; font-weight: bold; font-family: Montserrat; font-size: 14pt;")

        self.update()
        self.repaint()

    def sizeHint(self):
        return QSize(self.width(), 100)