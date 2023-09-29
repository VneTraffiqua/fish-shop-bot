import redis
import requests
from io import BytesIO
from environs import Env
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ChatAction
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from strapi_commands import (get_item_by_id, delete_cart_products,
                             get_cart_items, get_shop_items,
                             add_item_in_cart, create_cart, checkout)

_database = None


def start(update, context):
    keyboard = [
        [InlineKeyboardButton('Вход', callback_data='start')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        text='Войдите в магазин',
        reply_markup=reply_markup
    )
    return 'HANDLE_MENU'


def handle_menu(update, context):
    shop_items = get_shop_items(strapi_token)
    query = update.callback_query
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id,
                               )
    keyboard = [
        *[[InlineKeyboardButton(
            item['attributes']['title'], callback_data=item['id']
        )] for item in shop_items['data']],
        [InlineKeyboardButton('Моя корзина', callback_data='my_cart')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.reply_text(
        text='Please, chooce:',
        reply_markup=reply_markup
    )
    return 'HANDLE_STATE_CHANGE'


def handle_description(update, context):
    query = update.callback_query
    context.bot.send_chat_action(chat_id=query.message.chat_id,
                                 action=ChatAction.TYPING)
    data_item = get_item_by_id(
        strapi_token=strapi_token,
        item_id=query.data
    )['data']
    img_url = data_item[
        'attributes'
    ]['picture']['data'][0]['attributes']['url']
    response = requests.get(f"http://localhost:1337{img_url}")
    image_data = BytesIO(response.content)
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id,
                               )
    keyboard = [
        [
            InlineKeyboardButton(
            'В корзину', callback_data=f'cart {query.data}'
            )
        ],
        [
            InlineKeyboardButton('Назад', callback_data='menu'),
            InlineKeyboardButton('Моя корзина', callback_data='my_cart'),
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
    return 'HANDLE_STATE_CHANGE'


def get_cart(update, context):
        cart_items = get_cart_items(update, context)
        keyboard = [[
            InlineKeyboardButton('Меню', callback_data='menu'),
            InlineKeyboardButton('Очистить корзину',
                                 callback_data='delete_cart'),
        ], [InlineKeyboardButton('Оплатить',
                                 callback_data='waiting_email')]]
        cart_items = [
            item['attributes']['product']['data']['attributes']['title'] for
            item in cart_items['data']['attributes']['cart_products']['data']]
        text = f'Корзина:\n{[item for item in cart_items]}'
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(
            text=text,
            reply_markup=reply_markup
        )
        return 'HANDLE_STATE_CHANGE'


def waiting_email(update, context):
    query = update.callback_query
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id,
                               )
    query.message.reply_text(
        text='Введите e-mail, для оформления заказа'
    )
    return 'START'


def handle_state_change(update, context):
    chat_id = update.effective_chat.id
    if update.callback_query:
        user_reply = update.callback_query.data
        update.callback_query.answer()
    else:
        user_reply = update.message.text
    if user_reply.split(' ')[0] == 'cart':
        try:
            create_cart(strapi_token, chat_id)
        except requests.exceptions.HTTPError as err:
            print(err)
        item_id = user_reply.split(' ')[1]
        add_item_in_cart(strapi_token, chat_id, item_id)
        return 'HANDLE_STATE_CHANGE'
    elif user_reply == 'my_cart':
        get_cart(update, context)
        return 'HANDLE_STATE_CHANGE'
    elif user_reply == 'menu':
        handle_menu(update, context)
        return 'HANDLE_STATE_CHANGE'
    elif user_reply == 'waiting_email':
        waiting_email(update, context)
        return 'HANDLE_STATE_CHANGE'
    elif user_reply == 'delete_cart':
        delete_cart_products(strapi_token, chat_id)
        handle_menu(update, context)
        return 'HANDLE_STATE_CHANGE'
    elif '@' in user_reply:
        checkout(chat_id, user_reply)
        return 'HANDLE_STATE_CHANGE'
    else:
        handle_description(update, context)
        return 'HANDLE_STATE_CHANGE'


def get_database_connection():
    """
    Возвращает конекшн с базой данных Redis, либо создаёт новый, если он ещё не создан.
    """
    global _database
    if _database is None:
        database_password = env.str("REDIS_PASS")
        database_host = env.str("REDIS_HOST")
        database_port = env.str("REDIS_PORT")
        _database = redis.Redis(host='localhost', port=6379, db=0,)
            # host=database_host, port=database_port,
            #                     password=database_password)
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
        'HANDLE_MENU': handle_menu,
        'HANDLE_STATE_CHANGE': handle_state_change,
        'HANDLE_DESCRIPTION': handle_description,
        'MY_CART': get_cart,
        'WAITING_EMAIL': waiting_email,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        print(f'next state:{next_state}')
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


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

