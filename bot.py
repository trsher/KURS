import telebot
from telebot import types
from sqlalchemy.orm import Session
from database import Connect, User, Task, TaskLog
from datetime import datetime
import pytz

# Токен вашего Telegram-бота
BOT_TOKEN = "6159695820:AAEiZ7yqCwSiKTTGO-_Ny-ykWC9WBjnJs98"

# Создаём экземпляр бота
bot = telebot.TeleBot(BOT_TOKEN)

# Временная зона МСК
MOSCOW_TZ = pytz.timezone("Europe/Moscow")

# Количество задач на одной странице
TASKS_PER_PAGE = 5

# Функция для получения сессии базы данных
def get_session() -> Session:
    return Connect.create_connection()

# Функция для записи фото профиля в базу данных
def save_user_profile_photo(user_id: int) -> None:
    """Сохраняет фото профиля пользователя из Telegram в базу данных."""
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            try:
                user_photos = bot.get_user_profile_photos(user_id, limit=1)
                if user_photos.total_count > 0:
                    photo = user_photos.photos[0][-1]  # Самое большое разрешение
                    file_info = bot.get_file(photo.file_id)
                    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
                    if user.photo != file_url:  # Обновляем только если фото изменилось
                        user.photo = file_url
                        session.commit()
                        print(f"Фото профиля обновлено для пользователя {user_id}")
                else:
                    print(f"У пользователя {user_id} нет фото профиля")
            except Exception as e:
                print(f"Ошибка получения фото профиля для user_id {user_id}: {e}")
        else:
            print(f"Пользователь {user_id} не найден в базе")
    finally:
        session.close()

# Функция для уведомления пользователя о подтверждении и показа меню
def notify_and_show_menu(user_id: int) -> None:
    """Уведомляет пользователя о подтверждении и показывает главное меню."""
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if user and user.is_confirmed:
            bot.send_message(
                user_id,
                "✅ Ваш аккаунт подтверждён администратором! Теперь вы можете работать с задачами."
            )
            show_main_menu(user_id)
        else:
            print(f"Пользователь {user_id} не найден или не подтверждён")
    except Exception as e:
        print(f"Ошибка уведомления пользователя {user_id}: {e}")
    finally:
        session.close()

# Главное меню
def show_main_menu(user_id: int) -> None:
    """Показывает главное меню пользователю с его задачами."""
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user or not user.is_confirmed:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh"))
            bot.send_message(
                user_id,
                "❌ Ваш аккаунт ещё не подтверждён. Дождитесь подтверждения от администратора.",
                reply_markup=markup
            )
            return

        # Подсчёт активных задач пользователя
        active_tasks_count = (
            session.query(Task)
            .filter(Task.user_id == user.id)
            .filter(Task.is_completed == False)
            .count()
        )

        text = (
            f"👋 Привет, {user.username or 'Сотрудник'}!\n\n"
            f"📋 У вас {active_tasks_count} активных задач."
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📌 Мои задачи", callback_data="tasks_1"))
        markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh"))

        bot.send_message(user_id, text, reply_markup=markup)
    finally:
        session.close()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            user = User(
                id=user_id,
                username=message.from_user.username,
                email=None,
                phone=None,
                photo=None,
                is_confirmed=False
            )
            session.add(user)
            session.commit()
            save_user_profile_photo(user_id)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data="refresh"))
            bot.reply_to(
                message,
                "🎉 Вы зарегистрированы! Ожидайте подтверждения от администратора.",
                reply_markup=markup
            )
        else:
            save_user_profile_photo(user_id)  # Обновляем фото
            show_main_menu(user_id)
    except Exception as e:
        print(f"Ошибка при обработке /start для {user_id}: {e}")
        bot.reply_to(message, "Произошла ошибка. Попробуйте позже.")
    finally:
        session.close()

# Обработчик нажатий на кнопки
@bot.callback_query_handler(func=lambda call: True)
def button_handler(call):
    user_id = call.from_user.id
    session = get_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            bot.send_message(call.message.chat.id, "Пожалуйста, используйте /start для регистрации.")
            return

        data = call.data
        if data == "refresh":
            user.username = call.from_user.username
            save_user_profile_photo(user_id)
            session.commit()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="Данные обновлены!",
                reply_markup=None
            )
            show_main_menu(user_id)
        elif data.startswith("tasks_"):
            page = int(data.split("_")[-1])
            show_tasks(call.message, user, session, page)
        elif data.startswith("view_task_"):
            task_idx = int(data.split("_")[-1])
            page = int(data.split("_")[-2])
            show_task_details(call.message, user, session, task_idx, page)
        elif data.startswith("complete_"):
            task_id = int(data.split("_")[-1])
            complete_task(call.message, user, task_id, session)
        elif data == "main_menu":
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            show_main_menu(user_id)
    except Exception as e:
        print(f"Ошибка в button_handler для {user_id}: {e}")
        bot.send_message(call.message.chat.id, "Произошла ошибка. Попробуйте снова.")
    finally:
        session.close()

# Отображение списка задач пользователя
def show_tasks(message, user: User, session: Session, page: int = 1):
    """Показывает список активных задач пользователя."""
    if not user.is_confirmed:
        bot.send_message(message.chat.id, "❌ Ваш аккаунт не подтверждён.")
        return

    tasks = (
        session.query(Task)
        .filter(Task.user_id == user.id)
        .filter(Task.is_completed == False)
        .all()
    )

    if not tasks:
        bot.send_message(message.chat.id, "✅ У вас нет активных задач!")
        return

    total_tasks = len(tasks)
    total_pages = (total_tasks + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * TASKS_PER_PAGE
    end_idx = min(start_idx + TASKS_PER_PAGE, total_tasks)
    tasks_on_page = tasks[start_idx:end_idx]

    message_text = "📌 Ваши активные задачи:\n\n"
    for idx, task in enumerate(tasks_on_page, start=start_idx + 1):
        message_text += (
            f"{idx}. {task.title}\n"
            f"Приоритет: {task.priority.value}\n\n"
        )

    markup = types.InlineKeyboardMarkup()
    for idx, task in enumerate(tasks_on_page, start=start_idx + 1):
        markup.add(
            types.InlineKeyboardButton(f"{idx}. Подробности", callback_data=f"view_task_{page}_{idx}")
        )

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("⬅ Назад", callback_data=f"tasks_{page-1}"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("Вперёд ➡", callback_data=f"tasks_{page+1}"))
    if nav_buttons:
        markup.row(*nav_buttons)
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    bot.send_message(
        chat_id=message.chat.id,
        text=message_text,
        reply_markup=markup
    )

# Отображение деталей задачи
def show_task_details(message, user: User, session: Session, task_idx: int, page: int):
    """Показывает подробности задачи."""
    tasks = (
        session.query(Task)
        .filter(Task.user_id == user.id)
        .filter(Task.is_completed == False)
        .all()
    )

    start_idx = (page - 1) * TASKS_PER_PAGE
    tasks_on_page = tasks[start_idx:start_idx + TASKS_PER_PAGE]
    if not tasks_on_page or task_idx - 1 >= len(tasks):
        bot.send_message(message.chat.id, "Задача не найдена.")
        return

    task = tasks[task_idx - 1]

    message_text = (
        f"📌 Задача #{task.id}:\n\n"
        f"Название: {task.title}\n"
        f"Описание: {task.description or 'Нет описания'}\n"
        f"Приоритет: {task.priority.value}"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Выполнить", callback_data=f"complete_{task.id}")
    )
    markup.add(
        types.InlineKeyboardButton("⬅ К списку задач", callback_data=f"tasks_{page}")
    )
    markup.add(types.InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"))

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    bot.send_message(
        chat_id=message.chat.id,
        text=message_text,
        reply_markup=markup
    )

# Завершение задачи
def complete_task(message, user: User, task_id: int, session: Session):
    """Отмечает задачу как выполненную."""
    task = session.query(Task).filter_by(id=task_id, user_id=user.id).first()
    if not task:
        bot.send_message(message.chat.id, "Задача не найдена или не принадлежит вам.")
        return

    if task.is_completed:
        bot.send_message(message.chat.id, f"Задача #{task_id} уже выполнена.")
        return

    # Проверяем, есть ли запись в TaskLog
    existing_log = session.query(TaskLog).filter_by(task_id=task_id, user_id=user.id).first()
    if not existing_log:
        # Создаём запись о выполнении
        task_log = TaskLog(
            task_id=task_id,
            user_id=user.id,
            completed_at=datetime.now(MOSCOW_TZ)
        )
        session.add(task_log)

    # Помечаем задачу как выполненную
    task.is_completed = True
    session.commit()

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    bot.send_message(message.chat.id, f"✅ Задача #{task_id} выполнена!")
    show_main_menu(message.chat.id)

# Уведомление о новой задаче
def notify_user_of_specific_task(user: User, task: Task):
    """Уведомляет пользователя о новой задаче."""
    message_text = (
        f"📌 Новая задача назначена!\n\n"
        f"Задача #{task.id}: {task.title}\n"
        f"Описание: {task.description or 'Нет описания'}\n"
        f"Приоритет: {task.priority.value}"
    )
    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📋 К задачам", callback_data="tasks_1"))
        bot.send_message(user.id, message_text, reply_markup=markup)
    except Exception as e:
        print(f"Ошибка отправки уведомления пользователю {user.id}: {e}")

# Проверка и уведомление о новой задаче
def check_and_notify_specific_task(task_id: int):
    """Проверяет задачу и отправляет уведомление, если она новая."""
    session = get_session()
    try:
        task = session.query(Task).filter_by(id=task_id).first()
        if task and task.user_id and not task.is_completed:
            user = session.query(User).filter_by(id=task.user_id).first()
            if user:
                notify_user_of_specific_task(user, task)
    except Exception as e:
        print(f"Ошибка в check_and_notify_specific_task для task_id {task_id}: {e}")
    finally:
        session.close()

# Запуск бота
def main():
    print("Бот запущен...")
    bot.polling(none_stop=True)

if __name__ == "__main__":
    main()