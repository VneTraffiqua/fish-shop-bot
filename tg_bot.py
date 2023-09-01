import os
import logging
import redis
import requests
from io import BytesIO
from environs import Env
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

_database = None


def start(update, context):
    shop_items = get_shop_items(strapi_token)

    """
    Хэндлер для состояния START.

    Бот отвечает пользователю фразой "Привет!" и переводит его в состояние ECHO.
    Теперь в ответ на его команды будет запускаеться хэндлер echo.
    """
    keyboard = [
        [InlineKeyboardButton(
            item['attributes']['title'], callback_data=item['id']
        )] for item in shop_items['data']
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.delete_message(chat_id=update.message.chat_id,
                               message_id=update.message.message_id,
                               )
    update.message.reply_text(
        text='Please, chooce:',
        reply_markup=reply_markup
    )
    return "HANDLE_MENU"


def handle_menu(update, context):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    query.answer()
    data_item = get_item_by_id(strapi_token=strapi_token, item_id=query.data)['data']
    img_url = data_item['attributes']['picture']['data'][0]['attributes']['url']
    response = requests.get(f"http://localhost:1337{img_url}")
    image_data = BytesIO(response.content)
    print(query.message)
    context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=image_data,
    )
    query.edit_message_text(
        text=f"{data_item['attributes']['title']} "
             f"({data_item['attributes']['price']} за 1 кг):\n\n"
             f"{data_item['attributes']['description']}",
    )

    return "HANDLE_MENU"


def handle_users_reply(update, context):
    """
    Функция, которая запускается при любом сообщении от пользователя и решает как его обработать.
    Эта функция запускается в ответ на эти действия пользователя:
        * Нажатие на inline-кнопку в боте
        * Отправка сообщения боту
        * Отправка команды боту
    Она получает стейт пользователя из базы данных и запускает соответствующую функцию-обработчик (хэндлер).
    Функция-обработчик возвращает следующее состояние, которое записывается в базу данных.
    Если пользователь только начал пользоваться ботом, Telegram форсит его написать "/start",
    поэтому по этой фразе выставляется стартовое состояние.
    Если пользователь захочет начать общение с ботом заново, он также может воспользоваться этой командой.
    """
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
    }
    state_handler = states_functions[user_state]
    # Если вы вдруг не заметите, что python-telegram-bot перехватывает ошибки.
    # Оставляю этот try...except, чтобы код не падал молча.
    # Этот фрагмент можно переписать.
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = env.str("REDIS_PASS")
        database_host = env.str("REDIS_HOST")
        database_port = env.str("REDIS_PORT")
        _database = redis.Redis(host=database_host, port=database_port,
                                password=database_password)
    return _database


def get_shop_items(strapi_token):
    url = 'http://localhost:1337/api/products'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    response = requests.get(url, headers=header)
    response.raise_for_status()
    return response.json()


def get_item_by_id(strapi_token, item_id):
    url = f'http://localhost:1337/api/products/{item_id}'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    params = {
        'populate': 'picture'
    }
    response = requests.get(url, headers=header, params=params)
    response.raise_for_status()
    return response.json()


if __name__ == '__main__':
    env = Env()
    env.read_env()
    tg_token = env.str("TG_TOKEN")
    strapi_token = env.str('STRAPI_TOKEN')

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
