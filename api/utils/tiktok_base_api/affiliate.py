
import requests
import urllib.parse
import json

from api.utils.tiktok_base_api import (
    SIGN,
    TIKTOK_API_URL,

    logger,

)
from api.views import HttpResponse

def search_seller_creators(access_token: str, app_key: str, app_secret: str, shop_cipher: str, page_size: int = 20, page_token: str = ''):
    url = TIKTOK_API_URL["url_search_seller_creators"]
    headers = {
        "Content-Type": "application/json",
        "x-tts-access-token": access_token
    }
    query_params = {
        "app_key": app_key,
        "timestamp": SIGN.get_timestamp(),
        # "shop_cipher": shop_cipher,
        "page_size": 20,
        "page_token": ''
    }

    body = json.dumps({
        "search_key": "abc"
    })

    sign = SIGN.cal_sign(app_secret, urllib.parse.urlparse(url), query_params, body=body,)
    query_params["sign"] = sign

    response = requests.post(url, params=query_params, headers=headers, json=json.loads(body))
    print("response.json(): ", response.json())
    logger.info(f"Search seller creators response: {response.json()}")
    return HttpResponse(response)


