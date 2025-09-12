import json
import urllib.parse

import requests

from api.utils.tiktok_base_api import SIGN, TIKTOK_API_URL, logger


def getAccessToken(auth_code: str, app_key:str, app_secret:str) -> requests.Response:
    url = TIKTOK_API_URL["url_get_access_token"]

    body = json.dumps(
        {"app_key": app_key, "app_secret": app_secret, "auth_code": auth_code, "grant_type": "authorized_code"}
    )

    response = requests.post(url=url, json=json.loads(body))
    print("responsesss", response.text)
    logger.info(f"Get access token status code: {response.status_code}")

    return response


def refreshToken(refresh_token: str, app_key:str, app_secret:str) -> requests.Response:
    url = TIKTOK_API_URL["url_refresh_token"]

    body = json.dumps(
        {"app_key": app_key, "app_secret": app_secret, "refresh_token": refresh_token, "grant_type": "refresh_token"}
    )

    response = requests.post(url=url, json=json.loads(body))

    logger.info(f"Refresh token status code: {response.status_code}")

    return response


def get_author_shop(access_token: str, app_key:str, app_secret:str) -> requests.Response:
    url = TIKTOK_API_URL["url_get_author_shop"]
    query_params = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": SIGN.get_timestamp(),
    }

    sign = SIGN.cal_sign(app_secret, urllib.parse.urlparse(url), query_params)
    query_params["sign"] = sign

    response = requests.get(url, params=query_params)
    print("rssssss0", response.text)
    logger.info(f"Get brands status code: {response.status_code}")

    return response
