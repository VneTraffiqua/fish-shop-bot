import requests
from environs import Env

env = Env()
env.read_env()
strapi_token = env.str('STRAPI_TOKEN')
strapi_url = env.str('STRAPI_URL')


def get_cart_items(chat_id):
    url = f'{strapi_url}/api/carts/{chat_id}'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    params = {
        'populate': ['cart_products', 'cart_products.product']
    }
    response = requests.get(url, headers=header, params=params)
    response.raise_for_status()
    return response.json()


def get_or_create_cart(strapi_token, tg_user_id):
    try:
        cart_items = get_cart_items(tg_user_id)
        return cart_items
    except requests.exceptions.HTTPError:
        url = f'http://localhost:1337/api/carts'
        header = {
            'Authorization': f'bearer {strapi_token}'
        }
        data = {
            'data': {"id": tg_user_id}
        }
        response = requests.post(url, headers=header, json=data)
        response.raise_for_status()
        cart_items = get_cart_items(tg_user_id)
        return cart_items


def get_shop_items(strapi_token):
    url = f'{strapi_url}/api/products/'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    response = requests.get(url, headers=header)
    response.raise_for_status()
    return response.json()


def get_item_by_id(strapi_token, item_id):
    url = f'{strapi_url}/api/products/{item_id}'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    params = {
        'populate': 'picture'
    }
    response = requests.get(url, headers=header, params=params)
    response.raise_for_status()
    return response.json()


def add_item_in_cart(strapi_token, tg_user_id, item_id):
    url = f'{strapi_url}/api/cart-products/'
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
        get_or_create_cart(strapi_token, tg_user_id)
        response = requests.post(url, headers=header, json=data)
        response.raise_for_status()
        return


def delete_cart_products(strapi_token, tg_user_id):
    url = f'{strapi_url}/api/carts/{tg_user_id}'
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
        url = f'{strapi_url}/api/cart-products/{product["id"]}'
        header = {
            'Authorization': f'bearer {strapi_token}'
        }
        data = {
            'data': {'id': product['id']}
        }
        response = requests.delete(url, headers=header, json=data)
        response.raise_for_status()


def checkout(chat_id, user_reply):
    url = f'{strapi_url}/api/tg-users/'
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

