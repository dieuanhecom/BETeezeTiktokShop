import json
import urllib.parse

import requests
from django.contrib.auth.models import User

from api.models import Shop
from api.utils.constants.order import order_status_list
from api.utils.tiktok_base_api import (
    SIGN,
    TIKTOK_API_URL,
    logger,
   
)
from api.views import HttpResponse
from concurrent.futures import ThreadPoolExecutor, as_completed


def callOrderList(shop, cursor):
    url = TIKTOK_API_URL["url_get_orders"]

    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "sort_order": "DESC",
        "shop_cipher": shop.shop_cipher,
        "page_size": 100,
        "page_token": cursor or "",
    }

    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign
    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.post(url, params=query_params, headers=headers)

    print("response order list", response.text)

    return response


def callOrderDetail(shop, orderIds):
    url = TIKTOK_API_URL["url_get_order_detail"]

    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop.shop_cipher,
        "ids": ",".join(orderIds),
    }

    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )

    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.get(url, params=query_params, headers=headers)

    return response


def callGetShippingDocument(shop, order_id):
    url = TIKTOK_API_URL["url_get_shipping_document"]

    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "order_id": order_id,
        "document_type": "SHIPPING_LABEL",
        "document_size": "A6",
        "shop_cipher": shop.shop_cipher,
    }

    # body = json.dumps({
    #     "order_id": order_id
    # })

    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )

    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.get(url, params=query_params, headers=headers)

    try:
        response_data = response.json()
        doc_url = response_data["data"]["doc_url"]

        if doc_url:
            return doc_url
        else:
            logger.warning(f"No shipping label for order {order_id}")
            return None
    except Exception as e:
        logger.error(
            f"Error when getting shipping label for order {order_id}",
        )
        return None


def callPreCombinePackage(access_token, app_key, app_secret):
    url = TIKTOK_API_URL["url_pre_combine_package"]
    query_params = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": SIGN.get_timestamp(),
        "page_size": 10,
    }
    sign = SIGN.cal_sign(
        secret=app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign

    response = requests.get(url, params=query_params)

    logger.info(f"PreCombinePackage response: {response.text}")

    return HttpResponse(response)


def callConFirmCombinePackage(access_token, body_raw_json, app_key:str, app_secret:str):
    url = TIKTOK_API_URL["url_confirm_combine_package"]
    query_params = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": SIGN.get_timestamp(),
    }

    bodyjson = body_raw_json
    body = json.dumps(bodyjson)

    sign = SIGN.cal_sign(app_secret, urllib.parse.urlparse(url), query_params, body)
    query_params["sign"] = sign

    response = requests.post(url, params=query_params, json=json.loads(body))

    logger.info(f"ConfirmCombinePackage response: {response.text}")

    return HttpResponse(response)


def callGetShippingService(shop, body_raw_json):
    url = TIKTOK_API_URL["url_get_shipping_service"]
    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop.shop_cipher,
    }

    bodyjson = body_raw_json
    body = json.dumps(bodyjson)

    sign = SIGN.cal_sign(shop.app_secret, urllib.parse.urlparse(url), query_params, body)
    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.post(url, params=query_params, json=json.loads(body), headers=headers)

    logger.info(f"GetShippingService response: {response.text}")

    return HttpResponse(response)


def callSearchPackage(shop):
    url = TIKTOK_API_URL["url_search_package"]
    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop.shop_cipher,
    }

    bodyjson = {"page_size": 10000}

    body = json.dumps(bodyjson)

    sign = SIGN.cal_sign(shop.app_secret, urllib.parse.urlparse(url), query_params, body)
    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.post(url, params=query_params, json=json.loads(body), headers=headers)

    logger.info(f"SearchPackage response: {response.text}")

    return HttpResponse(response)


def callCreatePackages(shop, package_id):
    url = TIKTOK_API_URL["url_create_packages"]
    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "package_id": package_id,
        "shop_cipher": shop.shop_cipher,
    }

    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.get(url, params=query_params, headers=headers)

    # logger.info(f'GetPackageDetail response: {response.text}')
    print("res package detail", response.text)
    return HttpResponse(response)


def callCreateLabel(shop, body_raw_json):
    url = TIKTOK_API_URL["url_create_label"]
    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop.shop_cipher,
    }

    bodyjson = body_raw_json
    body = json.dumps(bodyjson)

    sign = SIGN.cal_sign(shop.app_secret, urllib.parse.urlparse(url), query_params, body=body)
    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.post(url, params=query_params, json=json.loads(body), headers=headers)
    print("response create label", response.text)
    return HttpResponse(response)


def callGetShippingDoc(shop, package_id):
    url = TIKTOK_API_URL["url_get_shipping_doc"]
    url = url.format(package_id=package_id)

    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
        "document_type": "SHIPPING_LABEL",
        "document_size": "A6",
        "shop_cipher": shop.shop_cipher,
    }

    sign = SIGN.cal_sign(shop.app_secret, urllib.parse.urlparse(url), query_params)
    query_params["sign"] = sign

    for attempt in range(1, 11):  # Thử lại tối đa 10 lần
        headers = {
            'Content-Type': 'application/json',
            'x-tts-access-token': shop.access_token,
        }
        response = requests.get(url, params=query_params, headers=headers)

        try:
            response_data = response.json()
            doc_url = response_data["data"].get("doc_url")

            if doc_url:
                return doc_url
            else:
                logger.warning(f"Attempt {attempt}: No shipping label for package {package_id}")
        except Exception as e:
            logger.error(
                f"Attempt {attempt}: Error when getting shipping label for package {package_id}",
                exc_info=e,
            )


    logger.error(f"Failed to get shipping label for package {package_id} after 10 attempts")
    return None



def cancel_order(shop, cancel_reason_key, order_id):
    url = TIKTOK_API_URL["url_cancel_order"]
    query_params = {
        "app_key": shop.app_key,
        "access_token": shop.access_token,
        "timestamp": SIGN.get_timestamp(),
    }

    bodyjson = {"cancel_reason_key": cancel_reason_key, "order_id": order_id}

    body = json.dumps(bodyjson)

    sign = SIGN.cal_sign(shop.app_secret, urllib.parse.urlparse(url), query_params, body)
    query_params["sign"] = sign

    headers = {
        'Content-Type': 'application/json',
        'x-tts-access-token': shop.access_token,
    }
    response = requests.post(url, params=query_params, json=json.loads(body), headers=headers)

    logger.info(f"SearchPackage response: {response.text}")
    return response


def check_and_append_errors(errors, shop_id, shop_name):
    return not any(f"{shop_id} |" in error for error in errors)


def req_get_order_list_new(
    shop: Shop,
    user: User,
    create_time_ge: int,
    create_time_lt: int,
    order_status: tuple,
    buyer_user_id: str,
    errors: list,
    app_key:str, 
    app_secret:str
):
    url = TIKTOK_API_URL["url_get_order_list_new"]
    all_orders = []
    page_token = ""
    is_within_range = True
    error_occurred = False

    def fetch_orders_for_status(status: str):
        if status not in order_status_list:
            logger.error(f"Invalid order status: {status}")
            return []
        nonlocal page_token, is_within_range, error_occurred
        orders_for_status = []
        while is_within_range and not error_occurred:
            query_params = {
                "app_key": app_key,
                "access_token": shop.access_token,
                "timestamp": SIGN.get_timestamp(),
                "page_size": 100,
                "sort_order": "DESC",
                "page_token": page_token or "",
                "shop_cipher": shop.shop_cipher,
            }

            headers = {"x-tts-access-token": shop.access_token}
            body = {}
            if create_time_ge:
                body["create_time_ge"] = create_time_ge
            if create_time_lt:
                body["create_time_lt"] = create_time_lt
            if order_status:
                body["order_status"] = status
            if buyer_user_id:
                body["buyer_user_id"] = buyer_user_id

            sign = SIGN.cal_sign(
                secret=app_secret,
                url=urllib.parse.urlparse(url),
                query_params=query_params,
                body=json.dumps(body),
            )
            query_params["sign"] = sign

            response = requests.post(
                url, params=query_params, headers=headers, json=body or {}
            )
            if "access token is expired" in response.text:
                if check_and_append_errors(errors, shop.id, shop.shop_name):
                    errors.append(f"{shop.id} | {shop.shop_name} | token expired.")
                logger.error(
                    f"Access token for shop {shop.id}:{shop.shop_name} is expired."
                )
                break

            if response.status_code != 200:
                if check_and_append_errors(errors, shop.id, shop.shop_name):
                    errors.append(f"{shop.id} | {shop.shop_name} | wrong token.")
                logger.error(
                    f"Error fetching data for status {status}: {response.text}"
                )
                error_occurred = True
                break

            data = response.json()
            orders = data.get("data", {}).get("orders", [])
            for order in orders:
                order["shop_owner"] = {
                    "id": user.id,
                    "username": user.username,
                }
                order["shop"] = {
                    "id": shop.id,
                    "name": shop.shop_name,
                    "shop_cipher": shop.shop_cipher,
                    "access_token": shop.access_token,
                    "app_key":shop.app_key,
                    "app_secret":shop.app_secret
                }
            orders_for_status.extend(orders)
            page_token = data.get("data", {}).get("next_page_token", "")
            is_within_range = bool(page_token)
        return orders_for_status

    for status in order_status:
        all_orders.extend(fetch_orders_for_status(status))
        page_token = ""
        is_within_range = True
    return all_orders


def split_orders_by_shop_id(orders):
    orders_by_shop_id = {}
    for order in orders:
        shop_id = order["shop"]["id"]
        if shop_id not in orders_by_shop_id:
            orders_by_shop_id[shop_id] = {
                "orders": [],
                "shop_owner": order["shop_owner"],
                "shop": order["shop"],
            }
        orders_by_shop_id[shop_id]["orders"].append(order)
    # print("order by shop", orders_by_shop_id)
    return orders_by_shop_id


def split_into_chunks(lst, chunk_size=50):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def process_orders_chunk_by_shop_id(chunk):
    detailed_orders = []
    orders_by_shop_id = split_orders_by_shop_id(chunk)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for shop_id, shop_data in orders_by_shop_id.items():
            shop = shop_data["shop"]
            orders = shop_data["orders"]
            # print("sss", shop_data)
            for sub_chunk in split_into_chunks(orders, 50):
                ids = [order["id"] for order in sub_chunk]
                future = executor.submit(req_get_order_detail_old, ids, shop)
                # print("sssssdf", sub_chunk)
                futures.append((future, sub_chunk, shop))
        # print("fute", futures)
        for future, sub_chunk, shop in futures:
            detailed_chunk = future.result()
            detailed_dict = {order["id"]: order for order in detailed_chunk}
            for sub_order in sub_chunk:
                order_id = sub_order["id"]
                if order_id in detailed_dict:
                    detailed_order = detailed_dict[order_id]
                    package_list = detailed_order.get("packages", [])
                    packages = [
                        {"id": package["id"]} for package in package_list
                    ]
                    sub_order["packages"] = packages
                    sub_order["item_list"] = detailed_order.get("line_items", [])
                    sub_order["shop"] = {
                        key: value
                        for key, value in shop.items()
                        if key not in ["access_token", "shop_cipher"]
                    }
            detailed_orders.extend(sub_chunk)

    return detailed_orders


def req_get_order_detail_new(ids: list, shop, shop_owner):
    url = TIKTOK_API_URL["url_get_order_detail_new"]
    query_params = {
        "app_key": shop.app_key,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop["shop_cipher"],
        "ids": ",".join(ids),
    }
    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign
    headers = {"x-tts-access-token": shop["access_token"]}
    response = requests.get(url, params=query_params, headers=headers)
    orders = response.json().get("data", {}).get("orders", [])
    for order in orders:
        order["shop_owner"] = shop_owner
        order["shop"] = {
            key: value
            for key, value in shop.items()
            if key not in ["access_token", "shop_cipher"]
        }
    return orders


def req_get_order_detail_old(ids: list, shop):
    print("da vao day", ids)
    url = TIKTOK_API_URL["url_get_order_detail"]
    query_params = {
        "app_key": shop["app_key"],
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop["shop_cipher"],
        "access_token": shop["access_token"],
        "ids": ",".join(ids),
    }
    sign = SIGN.cal_sign(
        secret=shop["app_secret"],
        url=urllib.parse.urlparse(url),
        query_params=query_params,
    )
    query_params["sign"] = sign
    headers = {"x-tts-access-token": shop["access_token"]}
    response = requests.get(url, params=query_params, headers=headers)

    orders = response.json().get("data", {}).get("orders", [])
    # for order in orders:
    #     order["shop_owner"] = shop_owner
    #     order["shop"] = {
    #         key: value
    #         for key, value in shop.items()
    #         if key not in ["access_token", "shop_cipher"]
    #     }
    # print("order", orders)
    return orders

def update_tracking_infor(order_ids,shop,tracking_ids):
    pre_url = TIKTOK_API_URL["url_update_tracking_infor"]
    for index,order in enumerate(order_ids):
        url = pre_url.format(order_id=order)
        query_params = {
        "app_key": shop.app_key,
        "timestamp": SIGN.get_timestamp(),
        "shop_cipher": shop["shop_cipher"],
        "access_token": shop["access_token"],
    }
    body = json.dumps({"shipping_provider_id": "7117858858072016686","tracking_number":tracking_ids[index]})
    sign = SIGN.cal_sign(
        secret=shop.app_secret,
        url=urllib.parse.urlparse(url),
        query_params=query_params,
        body=body,
    )
    query_params["sign"] = sign
    response = requests.post(url, params=query_params, json=json.loads(body))
    return response