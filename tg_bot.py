import redis
import requests
from io import BytesIO
from environs import Env
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from strapi_commands import (get_item_by_id, delete_cart_products,
                             get_shop_items, add_item_in_cart,
                             get_or_create_cart, checkout)

_database = None


def start(update, context):
    if update.callback_query:
        context.bot.delete_message(
            chat_id=update.callback_query.message.chat_id,
            message_id=update.callback_query.message.message_id,
        )
    shop_items = get_shop_items(strapi_token)
    keyboard = [
        *[[InlineKeyboardButton(
            item['attributes']['title'], callback_data=item['id']
        )] for item in shop_items['data']],
        [InlineKeyboardButton('Моя корзина', callback_data='get_cart')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text='Please choose:',
        reply_markup=reply_markup,
    )
    return 'HANDLE_MENU_BUTTON'


def handle_menu_button(update, context):
    query = update.callback_query
    query.answer()
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id,
                               )
    if query.data.isnumeric():
        data_item = get_item_by_id(
            strapi_token=strapi_token,
            item_id=query.data
        )['data']
        img_url = data_item[
            'attributes'
        ]['picture']['data'][0]['attributes']['url']
        response = requests.get(f"{strapi_url}{img_url}")
        image_data = BytesIO(response.content)
        keyboard = [
            [
                InlineKeyboardButton(
                    'В корзину', callback_data=f'cart {query.data}'
                )
            ],
            [
                InlineKeyboardButton('Назад', callback_data='/start'),
                InlineKeyboardButton('Моя корзина', callback_data='get_cart'),
             ],
            ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=image_data,
            caption=f"{data_item['attributes']['title']} "
                    f"({data_item['attributes']['price']} за 1 кг):\n\n"
                    f"{data_item['attributes']['description']}",
            reply_markup=reply_markup
        )
        return 'HANDLE_DESCRIPTION_BUTTON'
    else:
        cart_items = get_or_create_cart(strapi_token, query.message.chat_id)
        keyboard = [[
            InlineKeyboardButton('Меню', callback_data='start'),
            InlineKeyboardButton('Очистить корзину',
                                 callback_data='delete_cart'),
        ], [InlineKeyboardButton('Оплатить',
                                 callback_data='waiting_email')]]
        cart_items = [
            item['attributes']['product']['data']['attributes']['title']
            for
            item in
            cart_items['data']['attributes']['cart_products']['data']]
        text = f'Корзина:\n{[item for item in cart_items]}'
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
        return 'HANDLE_CART_BUTTON'


def handle_description_button(update, context):
    query = update.callback_query
    query.answer()
    if query.data == 'get_cart':
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id,
                                   )
        cart_items = get_or_create_cart(strapi_token, query.message.chat_id)
        keyboard = [[
            InlineKeyboardButton('Меню', callback_data='start'),
            InlineKeyboardButton('Очистить корзину',
                                 callback_data='delete_cart'),
        ], [InlineKeyboardButton('Оплатить',
                                 callback_data='waiting_email')]]
        cart_items = [
            item['attributes']['product']['data']['attributes']['title']
            for
            item in
            cart_items['data']['attributes']['cart_products']['data']]
        text = f'Корзина:\n{[item for item in cart_items]}'
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
        return 'HANDLE_CART_BUTTON'
    elif query.data == 'menu':
        start(update, context)
        return 'START'
    else:
        item_id = query.data.split(' ')[1]
        add_item_in_cart(strapi_token, query.message.chat_id, item_id)
        return 'HANDLE_DESCRIPTION_BUTTON'


def handle_cart_button(update, context):
    query = update.callback_query
    query.answer()
    if query.data == 'start':
        start(update, context)
        return 'START'
    elif query.data == 'delete_cart':
        delete_cart_products(strapi_token, query.message.chat_id)
        start(update, context)
        return 'HANDLE_MENU_BUTTON'
    else:
        query = update.callback_query
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id,
                                   )
        query.message.reply_text(
            text='Введите e-mail, для оформления заказа'
        )
        return 'EMAIL'


def handle_email(update, context):
    user_email = update.message.text
    checkout(update.message.chat_id, user_email)
    start(update, context)
    return 'HANDLE_MENU_BUTTON'


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = env.str("REDIS_PASS")
        database_host = env.str("REDIS_HOST")
        database_port = env.str("REDIS_PORT")
        # _database = redis.Redis(
        #     host=database_host, port=database_port,
        #                         password=database_password)
        _database = redis.Redis(host='localhost', port=6379, db=0, )
    return _database


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = str(update.callback_query.message.chat_id)
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")
        print(user_state)
    states_functions = {
        'START': start,
        'HANDLE_MENU_BUTTON': handle_menu_button,
        'HANDLE_DESCRIPTION_BUTTON': handle_description_button,
        'HANDLE_CART_BUTTON': handle_cart_button,
        'EMAIL': handle_email,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


if __name__ == '__main__':
    env = Env()
    env.read_env()
    tg_token = env.str("TG_TOKEN")
    strapi_token = env.str('STRAPI_TOKEN')
    strapi_url = env.str('STRAPI_URL')

    updater = Updater(tg_token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
    updater.idle()
