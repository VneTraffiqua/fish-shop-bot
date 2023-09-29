import requests
from environs import Env

env = Env()
env.read_env()
strapi_token = env.str('STRAPI_TOKEN')


def get_cart_items(update, context):
    query = update.callback_query
    query.answer()
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id,
                               )
    url = f'http://localhost:1337/api/carts/{query.message.chat_id}'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    params = {
        'populate': ['cart_products', 'cart_products.product']
    }
    try:
        response = requests.get(url, headers=header, params=params)
        response.raise_for_status()
        cart_items = response.json()
    except requests.exceptions.HTTPError:
        create_cart(strapi_token, query.message.chat_id)
    finally:
        return cart_items


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


def create_cart(strapi_token, tg_user_id):
    url = f'http://localhost:1337/api/carts'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    data = {
        'data': {"id": tg_user_id}
    }
    response = requests.post(url, headers=header)
    response.raise_for_status()
    return


def checkout(chat_id, user_reply):
    try:
        url = f'http://localhost:1337/api/tg-users/'
        header = {
            'Authorization': f'bearer {strapi_token}'
        }
        data = {
            'data': {"id": chat_id, "email": user_reply, "cart": chat_id}
        }
        response = requests.post(url, headers=header, json=data)
        response.raise_for_status()
        delete_cart_products(strapi_token, chat_id)
        return
    except requests.exceptions.HTTPError:
        return


def add_item_in_cart(strapi_token, tg_user_id, item_id):
    url = f'http://localhost:1337/api/cart-products'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    data = {
        'data': {
            "cart": [tg_user_id],
            'product': [item_id]
        }
    }
    try:
        response = requests.post(url, headers=header, json=data)
        response.raise_for_status()
        return
    except requests.exceptions.HTTPError:
        create_cart(strapi_token, tg_user_id)


def delete_cart_products(strapi_token, tg_user_id):
    url = f'http://localhost:1337/api/carts/{tg_user_id}'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    params = {
        'populate': ['cart_products']
    }
    response = requests.get(url, headers=header, params=params)
    response.raise_for_status()
    cart_products = response.json()['data']['attributes']['cart_products'][
        'data'
    ]
    for product in cart_products:
        url = f'http://localhost:1337/api/cart-products/{product["id"]}'
        header = {
            'Authorization': f'bearer {strapi_token}'
        }
        data = {
            'data': {'id': product['id']}
        }
        response = requests.delete(url, headers=header, json=data)
        response.raise_for_status()


def checkout(chat_id, user_reply):
    try:
        url = f'http://localhost:1337/api/tg-users/'
        header = {
            'Authorization': f'bearer {strapi_token}'
        }
        data = {
            'data': {"id": chat_id, "email": user_reply, "cart": chat_id}
        }
        response = requests.post(url, headers=header, json=data)
        response.raise_for_status()
        delete_cart_products(strapi_token, chat_id)
        return
    except requests.exceptions.HTTPError:
        return
