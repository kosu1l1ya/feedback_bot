from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📝 Оставить отзыв", callback_data="start_feedback")
    builder.button(text="📊 Статистика", callback_data="show_stats")
    builder.button(text="ℹ️ О проекте", callback_data="about")
    
    builder.adjust(1)
    return builder.as_markup()


def get_rating_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для оценки."""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("1 ⭐", "rate_1"),
        ("2 ⭐⭐", "rate_2"),
        ("3 ⭐⭐⭐", "rate_3"),
        ("4 ⭐⭐⭐⭐", "rate_4"),
        ("5 ⭐⭐⭐⭐⭐", "rate_5"),
        ("🔙 Назад", "cancel")
    ]
    
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(3, 2, 1)
    return builder.as_markup()


def get_feedback_type_keyboard() -> InlineKeyboardMarkup:
    """Выбор типа фидбека."""
    builder = InlineKeyboardBuilder()
    
    types = [
        ("🎯 Предложение", "type_suggestion"),
        ("🐛 Ошибка", "type_bug"),
        ("💡 Идея", "type_idea"),
        ("❤️ Благодарность", "type_thanks"),
        ("🔙 Назад", "cancel")
    ]
    
    for text, callback_data in types:
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение отправки."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="✅ Отправить", callback_data="submit")
    builder.button(text="✏️ Изменить", callback_data="edit")
    builder.button(text="❌ Отменить", callback_data="cancel")
    
    builder.adjust(2, 1)
    return builder.as_markup()