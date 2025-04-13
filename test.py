import unittest
from unittest.mock import patch, MagicMock, Mock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from windows import LoginWindow, AdminPanel
from dialogs import TaskEditDialog
from ui_elements import CustomAddButton
from database import Connect, Task, User, PriorityLevel, TaskLog, Admin
from bot import check_and_notify_specific_task
from datetime import datetime
import sys

# Создаём приложение для тестов GUI
app = QApplication(sys.argv)

class TestApp(unittest.TestCase):
    def setUp(self):
        # Подготавливаем моки для базы данных
        self.session_mock = MagicMock()
        self.connect_patcher = patch('database.Connect.create_connection', return_value=self.session_mock)
        self.connect_patcher.start()

    def tearDown(self):
        # Останавливаем патчеры после каждого теста
        self.connect_patcher.stop()

    # Тесты для AuthWindow
    @patch('windows.QMessageBox')
    def test_auth_window_successful_login(self, mock_message_box):
        # Подготавливаем мок для успешной авторизации
        admin_mock = Admin(login="admin", password="password")
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = admin_mock

        # Создаём окно авторизации
        auth_window = LoginWindow()
        auth_window.login_input.setText("admin")
        auth_window.password_input.setText("password")

        # Мокаем AdminPanel, чтобы не открывать реальное окно
        with patch.object(auth_window, 'admin_panel', MagicMock()):
            auth_window.authenticate()

        # Проверяем, что окно авторизации закрылось
        self.assertFalse(auth_window.isVisible())
        # Проверяем, что AdminPanel был создан и показан
        auth_window.admin_panel.show.assert_called_once()

    @patch('windows.QMessageBox')
    def test_auth_window_failed_login(self, mock_message_box):
        # Подготавливаем мок для неудачной авторизации
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None

        # Создаём окно авторизации
        auth_window = LoginWindow()
        auth_window.login_input.setText("wrong")
        auth_window.password_input.setText("wrong")

        auth_window.authenticate()

        # Проверяем, что отобразилось сообщение об ошибке
        mock_message_box.warning.assert_called_once_with(auth_window, "Ошибка", "Неверный логин или пароль")
        # Проверяем, что окно не закрылось
        self.assertTrue(auth_window.isVisible())

    # Тесты для AdminPanel
    def test_admin_panel_load_tasks(self):
        # Подготавливаем моки для задач
        task1 = Task(id=1, title="Task 1", is_completed=False)
        task2 = Task(id=2, title="Task 2", is_completed=True)
        self.session_mock.query.return_value.all.return_value = [task1, task2]
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = None

        # Создаём AdminPanel
        admin_panel = AdminPanel()
        admin_panel.load_tasks()

        # Проверяем, что список задач заполнен
        self.assertEqual(admin_panel.task_list.count(), 2)
        self.assertEqual(admin_panel.task_list.item(0).text(), "Task 1 [Активна]")
        self.assertEqual(admin_panel.task_list.item(1).text(), "Task 2 [Завершена]")

    @patch('windows.TaskEditDialog')
    def test_admin_panel_add_new_task(self, mock_task_edit_dialog):
        # Подготавливаем мок для диалога
        mock_dialog_instance = MagicMock()
        mock_dialog_instance.exec.return_value = True  # Симулируем принятие диалога
        mock_task_edit_dialog.return_value = mock_dialog_instance

        # Создаём AdminPanel
        admin_panel = AdminPanel()
        admin_panel.add_new_task()

        # Проверяем, что диалог был создан с новой задачей
        mock_task_edit_dialog.assert_called_once()
        # Проверяем, что load_tasks был вызван после принятия диалога
        self.assertTrue(admin_panel.load_tasks.called)

    # Тесты для TaskEditDialog
    def test_task_edit_dialog_initial_state_view_mode(self):
        # Создаём задачу для редактирования
        task = Task(id=1, title="Test Task", description="Description", priority=PriorityLevel.Medium, is_completed=False)
        dialog = TaskEditDialog(task)

        # Проверяем начальное состояние (режим просмотра)
        self.assertFalse(dialog.is_new_task)
        self.assertFalse(dialog.is_editing)
        self.assertTrue(dialog.title_input.isReadOnly())
        self.assertTrue(dialog.description_input.isReadOnly())
        self.assertFalse(dialog.priority_combo.isEnabled())
        self.assertFalse(dialog.employee_combo.isEnabled())
        self.assertFalse(dialog.completed_check.isEnabled())
        self.assertEqual(dialog.edit_save_btn.text(), "Редактировать")

    def test_task_edit_dialog_initial_state_new_task(self):
        # Создаём новую задачу
        task = Task(title="New Task")
        dialog = TaskEditDialog(task)

        # Проверяем начальное состояние (режим редактирования для новой задачи)
        self.assertTrue(dialog.is_new_task)
        self.assertTrue(dialog.is_editing)
        self.assertFalse(dialog.title_input.isReadOnly())
        self.assertFalse(dialog.description_input.isReadOnly())
        self.assertTrue(dialog.priority_combo.isEnabled())
        self.assertTrue(dialog.employee_combo.isEnabled())
        self.assertTrue(dialog.completed_check.isEnabled())
        self.assertEqual(dialog.edit_save_btn.text(), "Сохранить")

    @patch('dialogs.check_and_notify_specific_task')
    def test_task_edit_dialog_save_existing_task(self, mock_notify):
        # Подготавливаем моки для базы данных
        task = Task(id=1, title="Test Task", description="Description", priority=PriorityLevel.Medium, is_completed=False)
        self.session_mock.query.return_value.filter_by.return_value.first.return_value = task

        # Создаём диалог
        dialog = TaskEditDialog(task)
        dialog.is_editing = True  # Симулируем режим редактирования
        dialog.title_input.setText("Updated Task")
        dialog.description_input.setText("Updated Description")
        dialog.priority_combo.setCurrentIndex(1)  # Medium
        dialog.employee_combo.addItem("User 1", 1)
        dialog.employee_combo.setCurrentIndex(1)  # Выбираем сотрудника
        dialog.completed_check.setCurrentText("Завершена")

        # Вызываем сохранение
        dialog.toggle_edit()

        # Проверяем, что данные задачи обновлены
        self.assertEqual(task.title, "Updated Task")
        self.assertEqual(task.description, "Updated Description")
        self.assertEqual(task.priority, PriorityLevel.Medium)
        self.assertEqual(task.user_id, 1)
        self.assertTrue(task.is_completed)
        # Проверяем, что создана запись в TaskLog
        self.session_mock.add.assert_called_once()
        # Проверяем, что уведомление отправлено
        mock_notify.assert_called_once_with(1)
        # Проверяем, что изменения зафиксированы
        self.session_mock.commit.assert_called_once()

    def test_task_edit_dialog_save_empty_title(self):
        # Создаём задачу
        task = Task(id=1, title="Test Task")
        dialog = TaskEditDialog(task)
        dialog.is_editing = True
        dialog.title_input.setText("")  # Пустое название

        # Вызываем сохранение
        dialog.toggle_edit()

        # Проверяем, что сохранение не произошло (название пустое)
        self.assertFalse(self.session_mock.commit.called)

    # Тесты для CustomAddButton
    def test_custom_add_button_initialization(self):
        # Создаём кнопку
        button = CustomAddButton()

        # Проверяем начальные параметры
        self.assertEqual(button.text(), "+")
        self.assertEqual(button.size().width(), 50)
        self.assertEqual(button.size().height(), 50)

    @patch('ui_elements.QPushButton.clicked', new_callable=MagicMock)
    def test_custom_add_button_click(self, mock_clicked):
        # Создаём кнопку и AdminPanel
        admin_panel = AdminPanel()
        button = CustomAddButton(admin_panel)
        button.clicked.connect(admin_panel.add_new_task)

        # Симулируем клик
        button.clicked.emit()

        # Проверяем, что сигнал clicked был вызван
        mock_clicked.emit.assert_called_once()
        # Проверяем, что add_new_task был вызван
        self.assertTrue(admin_panel.add_new_task.called)

if __name__ == '__main__':
    unittest.main()