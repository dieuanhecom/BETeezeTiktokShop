import urllib.parse
import requests

from api.utils.constants.statement import payment_status_list
from api.utils.tiktok_base_api import (
    SIGN,
    TIKTOK_API_URL,
    app_key,
    logger,
    secret,
)


def get_statements_all(shop, user, query: dict, payment_status: tuple):
    all_statements = []
    for status in payment_status:
        if status not in payment_status_list:
            logger.error(f"Invalid payment status: {status}")
        else:
            all_statements.extend(
                get_statements_by_status(shop, user, query, payment_status=status)
            )
    return all_statements


def get_statements_by_status(shop, user, query: dict, payment_status: str):
    page_token = ""
    is_within_range = True
    all_statements = []
    while is_within_range:
        if page_token:
            query["page_token"] = page_token
        query["payment_status"] = payment_status
        response = get_statements(shop, user, query)
        if "access token is expired" in response.text:
            logger.error(
                f"Access token for shop {shop.id}:{shop.shop_name} is expired."
            )
            break

        if response.status_code != 200:
            logger.error(f"Error: {response.text}")
            break

        data = response.json().get("data", {})
        statements = data.get("statements", [])
        for statement in statements:
            statement["shop_owner"] = {
                "id": user.id,
                "username": user.username,
            }
            statement["shop"] = {
                "id": shop.id,
                "name": shop.shop_name,
                "shop_cipher": shop.shop_cipher,
                "access_token": shop.access_token,
            }
            all_statements.extend([statement])
        page_token = data.get("next_page_token", "")
        is_within_range = bool(page_token)

    return all_statements


def get_statements(shop, user, query: dict):
    url = TIKTOK_API_URL["url_get_statements"]
    query_params = {
        "app_key": app_key,
        "timestamp": SIGN.get_timestamp(),
    }
    query_params.update(query)
    sign = SIGN.cal_sign(
        secret=secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign
    headers = {"x-tts-access-token": shop.access_token}
    response = requests.get(url, params=query_params, headers=headers)
    return response


def get_statement_transactions(statement_id: str, shop: dict, query: dict):
    url = TIKTOK_API_URL["url_get_statement_transactions"].replace(
        "{statement_id}", statement_id
    )
    query_params = {
        "app_key": app_key,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop["shop_cipher"],
        "sort_field": "order_create_time",
        "page_size": 100,
    }
    query_params.update(query)
    sign = SIGN.cal_sign(
        secret=secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign
    headers = {"x-tts-access-token": shop["access_token"]}
    response = requests.get(url, params=query_params, headers=headers)
    data = response.json().get("data", {})
    return data
