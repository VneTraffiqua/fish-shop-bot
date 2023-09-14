# Fish-shop bot
MVP version for demonstration to the customer. The bot is integrated with Strapi CMS.

![pic](https://dvmn.org/media/filer_public/0a/5b/0a5b562c-7cb4-43e3-b51b-1b61721200fb/fish-shop.gif)

### How to install
Python3 should be already installed. 
To get started, you need to install dependencies and libraries:
```shell
pip install -r requirements.txt
```

Then create a `.env` file with environment variables:
```
TG_TOKEN=<TELEGRAM_BOT_TOKEN>
REDIS_HOST=<REDIS_HOST>
REDIS_PORT=<REDIS_PORT>
REDIS_PASS=<REDIS_PASSWORD>
STRAPI_TOKEN=<STRAPI_TOKEN>
```

- To obtain and access the Redis database, refer to the official website of [Redis](https://redis.com/).

- To get and use Strapi, visit [Strapi github](https://github.com/strapi/strapi). 
