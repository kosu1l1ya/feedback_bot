import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from keyboards import *
from google_sheets import sheets_manager


# Определяем состояния
class FeedbackState(StatesGroup):
    waiting_rating = State()
    waiting_type = State()
    waiting_comment = State()
    confirmation = State()


# Инициализация
bot = Bot(token=Config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ==================== КОМАНДЫ ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start."""
    welcome_text = """🌟 Добро пожаловать!

    🚀 Умный бот для сбора отзывов и обратной связи

    ✨ Что вы получите:
    • Быстрый сбор мнений от клиентов
    • Автоматическое сохранение в Google Таблицу
    • Мгновенные уведомления о новых отзывах
    • Аналитику и статистику в реальном времени

    💼 Для кого подходит:
    • Владельцы кафе и ресторанов
    • Студии красоты и магазины
    • Онлайн-специалисты и коучи
    • Любой бизнес, которому важны отзывы

    👇 Выберите действие:"""
    
    await message.answer(welcome_text, reply_markup=get_main_menu())


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика."""
    stats = sheets_manager.get_stats()
    
    stats_text = f"""📊 Статистика отзывов

            📈 Всего отзывов: {stats['total']}
            ⭐ Средний балл: {stats['average']}/5
            🕒 Последний отзыв: {stats['last_feedback']}

            🔗 Ссылка на таблицу:
            https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}

            Данные обновляются в реальном времени!"""
    
    await message.answer(stats_text, reply_markup=get_main_menu())


# ==================== ОБРАБОТКА КНОПОК ====================
@dp.callback_query(F.data == "start_feedback")
async def start_feedback(callback: CallbackQuery, state: FSMContext):
    """Начало сбора фидбека."""
    await state.set_state(FeedbackState.waiting_rating)
    
    text = """⭐ Оцените нашу работу

        По шкале от 1 до 5, где:
        1 — есть проблемы
        5 — всё отлично

        Ваша оценка поможет стать лучше!"""
    
    await callback.message.edit_text(text, reply_markup=get_rating_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext):
    """Обработка оценки."""
    # Фиксируем ошибку - проверяем, что это действительно оценка
    try:
        rating = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("Ошибка обработки оценки")
        return
    
    await state.update_data(rating=rating)
    await state.set_state(FeedbackState.waiting_type)
    
    text = f"""✅ Ваша оценка: {rating}/5

        📋 Укажите тип обратной связи:

        🎯 Предложение — как улучшить сервис
        🐛 Ошибка — что-то работает не так
        💡 Идея — новое предложение
        ❤️ Благодарность — хотите сказать спасибо"""
    
    await callback.message.edit_text(text, reply_markup=get_feedback_type_keyboard())
    await callback.answer()


@dp.callback_query(F.data.startswith("type_"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа фидбека."""
    fb_type = callback.data.split("_")[1]
    type_names = {
        "suggestion": "Предложение",
        "bug": "Ошибка",
        "idea": "Идея",
        "thanks": "Благодарность"
    }
    
    await state.update_data(type=type_names[fb_type])
    await state.set_state(FeedbackState.waiting_comment)
    
    text = """💬 Напишите ваш комментарий

        Опишите подробно вашу мысль, предложение или проблему.

        📝 Это поможет нам понять вас лучше!

        ❓ Можно пропустить, отправив команду /skip"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@dp.message(FeedbackState.waiting_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработка комментария."""
    comment = message.text
    
    if comment == "/skip":
        comment = ""
    
    await state.update_data(comment=comment)
    
    # Показываем подтверждение
    data = await state.get_data()
    
    preview = f"""📋 Проверьте данные перед отправкой:

        ⭐ Оценка: {data['rating']}/5
        📂 Тип: {data['type']}
        💬 Комментарий: {data.get('comment', 'Нет комментария')}

        ✅ Всё верно?"""
    
    await state.set_state(FeedbackState.confirmation)
    await message.answer(preview, reply_markup=get_confirmation_keyboard())


# ==================== ПОДТВЕРЖДЕНИЕ ====================
@dp.callback_query(F.data == "submit")
async def submit_feedback(callback: CallbackQuery, state: FSMContext):
    """Отправка фидбека."""
    data = await state.get_data()
    user = callback.from_user
    
    # Подготавливаем данные пользователя
    user_info = {
        "id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or ""
    }
    
    # Сохраняем в Google Sheets
    success = sheets_manager.save_feedback(user_info, data)
    
    if success:
        # Отправляем уведомление админу
        if Config.ADMIN_ID:
            admin_text = f"""🔔 Новый отзыв!

            👤 Пользователь: @{user.username or 'без username'}
            ⭐ Оценка: {data['rating']}/5
            📂 Тип: {data['type']}
            💬 Комментарий: {data.get('comment', 'Нет комментария')[:100]}"""
            try:
                await bot.send_message(Config.ADMIN_ID, admin_text)
            except:
                pass
        
        # Сообщение пользователю
        text = """🎉 Спасибо за ваш отзыв!

            Ваше мнение очень ценно для нас.
            Все данные сохранены в системе.

            🔗 Результаты доступны в Google Таблице:
            https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}

            Вы можете оставить ещё один отзыв или посмотреть статистику."""
        
        # Вставляем реальный ID таблицы
        text = text.replace("{Config.SPREADSHEET_ID}", Config.SPREADSHEET_ID)
        
    else:
        text = """⚠️ Ошибка сохранения

            Пожалуйста, попробуйте позже.
            Мы уже работаем над исправлением."""
    
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await state.clear()
    await callback.answer()


@dp.callback_query(F.data == "edit")
async def edit_feedback(callback: CallbackQuery, state: FSMContext):
    """Редактирование фидбека."""
    await state.set_state(FeedbackState.waiting_rating)
    
    text = "🔄 Начинаем заново. Выберите оценку:"
    await callback.message.edit_text(text, reply_markup=get_rating_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel_feedback(callback: CallbackQuery, state: FSMContext):
    """Отмена фидбека."""
    await state.clear()
    
    text = "❌ Сбор отзыва отменен.\n\nВы всегда можете начать заново."
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


# ==================== ДОПОЛНИТЕЛЬНЫЕ КНОПКИ ====================
@dp.callback_query(F.data == "show_stats")
async def show_stats(callback: CallbackQuery):
    """Показ статистики."""
    stats = sheets_manager.get_stats()
    
    text = f"""📊 Текущая статистика отзывов

            📈 Всего отзывов: {stats['total']}
            ⭐ Средняя оценка: {stats['average']}/5
            🕒 Последний отзыв: {stats['last_feedback']}

            🔗 Таблица с данными:
            https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}

            Данные обновляются автоматически при каждом новом отзыве!"""
    
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


@dp.callback_query(F.data == "about")
async def about_project(callback: CallbackQuery):
    """О проекте."""
    text = """ℹ️ О проекте

            🚀 Умный инструмент для сбора обратной связи

            ✨ Технологии:
            • Python и Aiogram 3.x
            • Google Sheets API
            • Асинхронная архитектура
            • Система состояний (FSM)

            🎯 Преимущества:
            • Повышение лояльности клиентов
            • Автоматизация сбора отзывов
            • Удобный интерфейс для клиентов
            • Интеграция с Google экосистемой

            📊 Все данные сохраняются в Google Таблицу в реальном времени!

            🔗 Ссылка на демо-таблицу:
            https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}"""
    
    # Вставляем реальный ID таблицы
    text = text.replace("{Config.SPREADSHEET_ID}", Config.SPREADSHEET_ID)
    
    await callback.message.edit_text(text, reply_markup=get_main_menu())
    await callback.answer()


# ==================== ЗАПУСК ====================
async def main():
    """Запуск бота."""
    print("🚀 Запуск Feedback Collector Bot...")
    print(f"👤 Администратор: {Config.ADMIN_ID}")
    print(f"📊 Таблица: https://docs.google.com/spreadsheets/d/{Config.SPREADSHEET_ID}")
    
    # Подключаемся к Google Sheets
    sheets_manager.connect()
    
    print("✅ Бот запущен и готов к работе!")
    print("➡️ Перейдите в Telegram и начните общение с ботом")
    
    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())