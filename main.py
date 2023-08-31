import requests
from environs import Env


if __name__ == '__main__':
    env = Env()
    env.read_env()
    strapi_token = env.str('STRAPI_TOKEN')

    url = 'http://localhost:1337/api/products'
    header = {
        'Authorization': f'bearer {strapi_token}'
    }
    response = requests.get(url, headers=header)
    response.raise_for_status()
    print(response.json())
