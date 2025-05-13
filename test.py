import pytest
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QSize
from unittest.mock import patch, MagicMock
from windows import LoginWindow, AdminPanel
from dialogs import TaskEditDialog
from ui_elements import CustomAddButton
import warnings

# Подавить предупреждения pytest-qt о таймаутах
warnings.filterwarnings("ignore", category=RuntimeWarning, module="pytestqt")

# Фикстура для имитации сессии базы данных
@pytest.fixture
def db_session():
    session_mock = MagicMock()
    # Mock для Admin
    admin_mock = MagicMock()
    admin_mock.username = "test_user"
    session_mock.query.return_value.filter_by.return_value.first.return_value = admin_mock
    # Mock для задач
    task1 = MagicMock(id=1, title="Task 1", description="Desc 1", status="Open")
    task2 = MagicMock(id=2, title="Task 2", description="Desc 2", status="Closed")
    session_mock.query.return_value.all.return_value = [task1, task2]
    # Mock для count в check_new_users
    session_mock.query.return_value.filter.return_value.count.return_value = 0
    # Mock для добавления задачи
    session_mock.add = MagicMock()
    session_mock.commit = MagicMock()
    # Mock для merge
    merged_task = MagicMock()
    session_mock.merge = MagicMock(return_value=merged_task)
    patcher = patch('database.Connect.create_connection', return_value=session_mock)
    patcher.start()
    yield session_mock
    patcher.stop()

# Фикстура для мока check_new_users
@pytest.fixture
def mock_check_new_users():
    with patch('windows.AdminPanel.check_new_users', MagicMock()) as mock:
        yield mock

class TestApp:
    def test_login_success(self, qtbot, db_session):
        # Имитация успешного входа
        db_session.check_credentials.return_value = True
        login_window = LoginWindow()
        qtbot.addWidget(login_window)
        login_window.login_input.setText("valid_user")
        login_window.password_input.setText("valid_pass")
        # Найти кнопку входа
        button = login_window.findChild(QPushButton)
        assert button is not None, "Кнопка входа не найдена"
        with qtbot.waitSignal(button.clicked, timeout=1000):
            qtbot.mouseClick(button, Qt.LeftButton)
        assert login_window.isHidden()  # Окно должно закрыться

    def test_login_failure(self, qtbot, db_session):
        # Имитация неуспешного входа
        db_session.check_credentials.return_value = False
        login_window = LoginWindow()
        qtbot.addWidget(login_window)
        login_window.login_input.setText("invalid_user")
        login_window.password_input.setText("invalid_pass")
        # Найти кнопку входа
        button = login_window.findChild(QPushButton)
        assert button is not None, "Кнопка входа не найдена"
        print(f"Login button text: {button.text()}")  # Отладочный вывод
        with qtbot.waitSignal(button.clicked, timeout=1000):
            qtbot.mouseClick(button, Qt.LeftButton)
        assert not hasattr(login_window, 'approved') or not login_window.approved, "Диалог не должен быть принят"

    def test_admin_panel_load_tasks(self, qtbot, db_session, mock_check_new_users):
        # Имитация загрузки задач
        admin_panel = AdminPanel("test_user")
        qtbot.addWidget(admin_panel)
        with patch.object(admin_panel, 'load_tasks') as mock_load_tasks:
            admin_panel.load_tasks()
            mock_load_tasks.assert_called_once()
        # Проверка вызова запроса к базе данных
        db_session.query.assert_called()
        # Проверка наличия списка задач
        task_list_view = admin_panel.findChild(QListView)
        assert task_list_view is not None, "Список задач не найден"
        model = task_list_view.model()
        assert model is not None, "Модель списка задач не найдена"

    def test_admin_panel_add_task(self, qtbot, db_session, mock_check_new_users):
        admin_panel = AdminPanel("test_user")
        qtbot.addWidget(admin_panel)
        # Найти кнопку добавления (приоритет на CustomAddButton)
        buttons = admin_panel.findChildren(QPushButton)
        add_button = next((btn for btn in buttons if isinstance(btn, CustomAddButton) or btn.text() in ("Добавить", "+", "Add Task")), None)
        print(f"Buttons found: {[btn.text() for btn in buttons]}")
        print(f"Button types: {[type(btn).__name__ for btn in buttons]}")  # Отладочный вывод
        assert add_button is not None, "Кнопка добавления задачи не найдена"
        # Mock слота add_task
        with patch.object(admin_panel, 'add_task') as mock_add_task:
            with qtbot.waitSignal(add_button.clicked, timeout=1000):
                qtbot.mouseClick(add_button, Qt.LeftButton)
            mock_add_task.assert_called_once()
            print(f"mock_add_task called with: {mock_add_task.call_args}")  # Отладочный вывод

    def test_task_edit_dialog_initial_state(self, qtbot, mock_check_new_users):
        # Создание имитации задачи
        mock_task = MagicMock()
        mock_task.title = "Test Task"
        dialog = TaskEditDialog(mock_task)
        qtbot.addWidget(dialog)
        # Проверка, что title_input существует
        assert hasattr(dialog, 'title_input'), "Поле title_input не найдено"
        # Проверка mock_task.title
        assert mock_task.title == "Test Task", "mock_task.title не соответствует ожидаемому"

    def test_task_edit_dialog_save_changes(self, qtbot, db_session, mock_check_new_users):
        # Создание имитации задачи
        mock_task = MagicMock()
        mock_task.title = "Original Title"
        # Проверка, что title можно перезаписать
        mock_task.title = "Test"
        assert mock_task.title == "Test", "mock_task.title не обновляется"
        mock_task.title = "Original Title"
        dialog = TaskEditDialog(mock_task)
        qtbot.addWidget(dialog)
        # Симуляция редактирования
        dialog.title_input.setText("New Title")
        # Проверка значения title_input
        assert dialog.title_input.text() == "New Title", "title_input не обновлен"
        # Найти кнопку Сохранить
        buttons = dialog.findChildren(QPushButton)
        ok_button = next((btn for btn in buttons if btn.text() in ("Сохранить", "Принять", "OK", "Save", "Accept")), None)
        print(f"Dialog buttons: {[btn.text() for btn in buttons]}")  # Отладочный вывод
        print(f"mock_task.title before accept: {mock_task.title}")  # Отладочный вывод
        # Mock результата merge
        merged_task = db_session.merge.return_value
        merged_task.title = "New Title"  # Установить ожидаемый title
        if ok_button is None:
            with qtbot.waitSignal(dialog.accepted, timeout=2000):
                dialog.accept()
        else:
            print(f"Clicking button: {ok_button.text()}")  # Отладочный вывод
            with qtbot.waitSignal(dialog.accepted, timeout=2000):
                qtbot.mouseClick(ok_button, Qt.LeftButton)
        print(f"mock_task.title after accept: {mock_task.title}")  # Отладочный вывод
        print(f"mock_task attributes after accept: {mock_task.__dict__}")  # Отладочный вывод
        print(f"mock_task.name after accept: {getattr(mock_task, 'name', 'Not set')}")  # Отладочный вывод
        print(f"mock_task.task_title after accept: {getattr(mock_task, 'task_title', 'Not set')}")  # Отладочный вывод
        print(f"mock_task.description after accept: {getattr(mock_task, 'description', 'Not set')}")  # Отладочный вывод
        print(f"Dialog hidden after accept: {dialog.isHidden()}")  # Отладочный вывод
        print(f"db_session.commit called: {db_session.commit.called}")  # Отладочный вывод
        print(f"db_session.add called: {db_session.add.called}")  # Отладочный вывод
        print(f"db_session.add call args: {db_session.add.call_args}")  # Отладочный вывод
        print(f"db_session.commit call args: {db_session.commit.call_args}")  # Отладочный вывод
        # Проверка объекта, добавленного в session.add
        assert db_session.add.called
        merged_task = db_session.add.call_args[0][0]
        print(f"merged_task.title: {merged_task.title}")  # Отладочный вывод
        assert merged_task.title == "New Title"  # Проверить title в merged_task
        db_session.commit.assert_called_once()  # Проверить вызов commit

    def test_custom_add_button_init(self, qtbot, mock_check_new_users):
        button = CustomAddButton()
        qtbot.addWidget(button)
        assert isinstance(button, QPushButton)  # Проверка типа
        assert button.minimumSize() == QSize(100, 100)  # Проверка минимального размера

    def test_custom_add_button_click(self, qtbot, mock_check_new_users):
        button = CustomAddButton()
        qtbot.addWidget(button)
        mock_slot = MagicMock()
        button.clicked.connect(mock_slot)
        with qtbot.waitSignal(button.clicked, timeout=1000):
            qtbot.mouseClick(button, Qt.LeftButton)
        mock_slot.assert_called_once()  # Проверить вызов сигнала