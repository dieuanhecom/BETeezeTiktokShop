import asyncio
import json
import math
import random
import string
import urllib.parse
from datetime import datetime
from uuid import uuid4
from django.http import JsonResponse as JsonResponse
import requests
from rest_framework import status
from rest_framework.response import Response

from api.utils.tiktok_base_api import SIGN, TIKTOK_API_URL, app_key, logger, secret
from tiktok.middleware import BadRequestException

from .product import callProductList

PROMOTION_SKUS_LIMIT = 2999

semaphore = asyncio.Semaphore(10)


async def limiter(func):
    async with semaphore:
        return await func()


def get_active_products(access_token: str, page_number: int, page_size: int):
    """
    Get products
    """
    url = TIKTOK_API_URL["url_product_list"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body = json.dumps(
        {
            "page_size": page_size,
            "page_number": page_number,
            "search_status": 4,
        }
    )

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


async def get_all_no_promotion_products(access_token: str):
    """
    Get all no promotion products
    """
    start_page = 1
    end_page = 0
    page_size = 100

    first_page_data = await get_active_products(access_token, 1, 1)

    all_products = []
    total_count = first_page_data["total"]

    max_page = math.ceil(total_count / page_size)

    results = []
    if end_page <= 0:
        tasks = []
        for i in range(start_page, max_page + 1):
            tasks.append(limiter(lambda i=i: get_active_products(access_token, i, page_size)))

        results = await asyncio.gather(*tasks)

    else:
        tasks = []
        for i in range(start_page, end_page + 1):
            tasks.append(limiter(lambda i=i: get_active_products(access_token, i, page_size)))

        results = await asyncio.gather(*tasks)

    for result in results:
        all_products.extend(result["products"])

    # no_promotion_products = [product for product in all_products
    # if not (product.get("promotion_infos") and len(product["promotion_infos"]) > 0)]

    return all_products


async def get_promotions(access_token: str, status: int = None, title: str = None, page_number=1, page_size=100):
    """
    Get promotion campaigns
    """
    url = TIKTOK_API_URL["url_get_promotions"]

    if page_number is None:
        page_number = 1

    if page_size is None:
        page_size = 100

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "page_number": page_number,
        "page_size": page_size,
    }

    if title:
        body_json["title"] = title

    if status is not None:
        body_json["status"] = status

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


def get_promotion_detail(access_token: str, promotion_id: str):
    """
    Get promotion detail
    """
    url = TIKTOK_API_URL["url_get_promotion_detail"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}
    # query_params["shop_id"] = shop_id
    query_params["promotion_id"] = promotion_id

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params)

    query_params["sign"] = sign

    response = requests.get(url=url, params=query_params)

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data


async def create_simple_promotion(
    access_token: str, title: str, begin_time: int, end_time: int, type: str, product_type="SKU"
):
    """
    Create simple promotion - flash sale or product discount
    """
    url = TIKTOK_API_URL["url_create_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    now = datetime.now()

    formatted_date = (
        now.strftime("%y-%m-%d--%H-%M-%S")
        + "--"
        + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    )  # noqa: E501
    body_json = {
        "begin_time": begin_time,
        "end_time": end_time,
        "product_type": 2 if product_type == "SKU" else 1,  # SPU
        "promotion_type": 3 if type == "FlashSale" else 2 if type == "DirectDiscount" else 1,  # FixedPrice
        "request_serial_no": "create" + str(uuid4()),
        "title": title + "-" + formatted_date,
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


async def create_promotion_with_products(
    access_token: str,
    title: str,
    begin_time: int,
    end_time: str,
    type: str,
    discount: int,
    product_type: str,
    products=[],
):
    """
    Create promotion with products
    """
    new_promotion = await create_simple_promotion(
        access_token=access_token,
        title=title,
        begin_time=begin_time,
        end_time=end_time,
        type=type,
        product_type=product_type,
    )  # noqa: E501

    promotion_id = new_promotion["promotion_id"]
    logger.info("Promotion created successfully  - " + promotion_id)

    product_list = []
    for product in products:
        sku_list = []
        for sku in product["skus"]:
            skuData = {
                # "discount": discount,
                "num_limit": -1,
                "user_limit": -1,
                "product_id": product["id"],
                # "promotion_price": round(float(sku["price"]["original_price"]) * (100 - discount) / 100, 2),
                "sku_id": sku["id"],
            }
            if type == "FlashSale" or type == "FixedPrice":
                skuData["promotion_price"] = round(float(sku["price"]["original_price"]) * (100 - discount) / 100, 2)
            else:
                skuData["discount"] = discount

            sku_list.append(skuData)

        product_list.append(
            {
                # "discount": discount,
                # "promotion_price":round(float(product["skus"][0]["price"]["original_price"])\
                # * (100 - discount) / 100, 2),
                "num_limit": -1,
                "user_limit": -1,
                "product_id": product["id"],
                "sku_list": sku_list,
            }
        )

    await add_or_update_promotion_discount(access_token, promotion_id, product_list)

    return promotion_id


async def create_promotion(
    access_token: str, title: str, begin_time: int, end_time: int, type: str, discount: int, product_type="SKU"
):
    """
    Create advanced promotion - deactivated all promotions before and create new one
    """
    all_products = await get_all_no_promotion_products(access_token)

    # new_promotion = await create_simple_promotion(access_token=access_token, title=title, begin_time=begin_time, end_time=end_time, type=type, discount=discount, product_type=product_type)  # noqa: E501

    # Separate all_products into products_pack
    products_pack = []
    pack = []
    pack_sku_count = 0

    for product in all_products:
        sku_count = len(product["skus"])
        if pack_sku_count + sku_count <= PROMOTION_SKUS_LIMIT:
            pack.append(product)
            pack_sku_count += sku_count
        else:
            products_pack.append(pack)
            pack = [product]
            pack_sku_count = sku_count

    if pack:  # Add the last pack if any remaining
        products_pack.append(pack)

    # await deactivate_all_promotions(access_token)
    await asyncio.sleep(4)

    logger.info(
        f"Creating promotion with {len(all_products)} products - {len(products_pack)} packs of {PROMOTION_SKUS_LIMIT} skus"
    )

    promotion_ids = []
    for pack in products_pack:
        promotion_id = await create_promotion_with_products(
            access_token=access_token,
            title=title,
            begin_time=begin_time,
            end_time=end_time,
            type=type,
            discount=discount,
            product_type=product_type,
            products=pack,
        )  # noqa: E501

        await asyncio.sleep(6)
        promotion_ids.append(promotion_id)

    return {
        "data": {
            "promotion_ids": promotion_ids,
            "count": len(promotion_ids),
            "products_count": len(all_products),
            "skus_count": sum([len(product["skus"]) for product in all_products]),
        }
    }


def add_or_update_promotion_discount(access_token: str, promotion_id: int, product_list: list):
    """
    Add or update skus for promotion
    """
    url = TIKTOK_API_URL["url_add_or_update_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "product_list": product_list,
        "promotion_id": promotion_id,
        "request_serial_no": "update_promo" + str(uuid4()),
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


def add_or_update_promotion_flashdeal(access_token: str, promotion_id: int, product_list: list):
    """
    Add or update skus for promotion
    """
    url = TIKTOK_API_URL["url_add_or_update_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "product_list": product_list,
        "promotion_id": promotion_id,
        "request_serial_no": "update_promo" + str(uuid4()),
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


async def deactivate_promotion(access_token: str, promotion_id: int):
    """
    Deactivate promotion
    """
    url = TIKTOK_API_URL["url_deactivate_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "promotion_id": promotion_id,
        "request_serial_no": "deactivate_promo" + str(uuid4()),
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    logger.info("Promotion deactivated " + str(promotion_id))

    return data["data"]


async def deactivate_all_promotions(access_token: str):
    """
    Deactivate all promotions
    """
    active_promotions = (await get_promotions(access_token, 2))["promotion_list"]

    for promotion in active_promotions:
        await deactivate_promotion(access_token, promotion["promotion_id"])

    return True


def get_promotions_discount(access_token: str, status: int = 2, title: str = "Discount", page_number=1, page_size=100):
    """
    Get promotion campaigns
    """
    url = TIKTOK_API_URL["url_get_promotions"]

    if page_number is None:
        page_number = 1

    if page_size is None:
        page_size = 100

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}
    query_params_upcomming = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "page_number": page_number,
        "page_size": page_size,
    }
    body_upcomming = {"page_number": page_number, "page_size": page_size, "status": 1}

    if title:
        body_json["title"] = title
        body_upcomming["title"] = title

    if status is not None:
        body_json["status"] = status

    body = json.dumps(body_json)
    body_upcomming_json = json.dumps(body_upcomming)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign
    sign_upcomming = SIGN.cal_sign(
        secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body_upcomming_json
    )

    query_params_upcomming["sign"] = sign_upcomming

    response = requests.post(url=url, params=query_params, json=json.loads(body))
    response_upcomming = requests.post(url=url, params=query_params_upcomming, json=json.loads(body_upcomming_json))

    data = response.json()
    data_comming = response_upcomming.json()
    if data_comming["code"] == 0:
        for product in data_comming["data"]["promotion_list"]:
            data["data"]["promotion_list"].append(product)
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


def get_promotions_flashdeal(
    access_token: str, status: int = 2, title: str = "Flashdeal", page_number=1, page_size=100
):
    """
    Get promotion campaigns
    """
    url = TIKTOK_API_URL["url_get_promotions"]

    if page_number is None:
        page_number = 1

    if page_size is None:
        page_size = 100

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}
    query_params_upcomming = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "page_number": page_number,
        "page_size": page_size,
    }
    body_upcomming = {"page_number": page_number, "page_size": page_size, "status": 1}

    if title:
        body_json["title"] = title
        body_upcomming["title"] = title

    if status is not None:
        body_json["status"] = status

    body = json.dumps(body_json)
    body_upcomming_json = json.dumps(body_upcomming)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign
    sign_upcomming = SIGN.cal_sign(
        secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body_upcomming_json
    )

    query_params_upcomming["sign"] = sign_upcomming

    response = requests.post(url=url, params=query_params, json=json.loads(body))
    response_upcomming = requests.post(url=url, params=query_params_upcomming, json=json.loads(body_upcomming_json))

    data = response.json()
    data_comming = response_upcomming.json()
    if data_comming["code"] == 0:
        for product in data_comming["data"]["promotion_list"]:
            data["data"]["promotion_list"].append(product)
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


# hien tai dang lay 100 san pham dau tien
def get_unpromotion_products(access_token):
    """
    Get products
    """
    response = callProductList(access_token=access_token, page_number=1)
    response_page_2 = callProductList(access_token=access_token, page_number=2)
    data = response.json()
    product_active_ids = []
    data_loop = data["data"]["products"]
    if data["data"]["total"] > 100:
        data_page_2 = response_page_2.json()
        for product in data_page_2["data"]["products"]:
            data_loop.append(product)

    for product in data_loop:
        product_active_ids.append(product["id"])

    promoted_product_list = get_promotions_discount(access_token=access_token)

    product_promoted_ids = []
    for promotion in promoted_product_list.get("promotion_list"):
        promotion_id = promotion.get("promotion_id")
        promotion_detail = get_promotion_detail(access_token, promotion_id)
        for product in promotion_detail["data"]["product_list"]:
            product_promoted_ids.append(product["product_id"])
    active_set = set(product_active_ids)
    promoted_set = set(product_promoted_ids)
    unique_active = active_set.difference(promoted_set)
    new_product_list = []
    for product in data["data"]["products"]:
        if product["id"] in unique_active:
            new_product_list.append(product)

    new_data = data.copy()
    new_data["data"]["products"] = new_product_list

    return new_data


def create_promotion_form(access_token: str, title: str, begin_time: int, end_time: int, type: str, product_type):
    """
    Create simple promotion - flash sale or product discount
    """
    url = TIKTOK_API_URL["url_create_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    now = datetime.now()

    formatted_date = (
        now.strftime("%y-%m-%d--%H-%M-%S")
        + "--"
        + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
    )  # noqa: E501
    body_json = {
        "begin_time": begin_time,
        "end_time": end_time,
        "product_type": 2 if product_type == "SKU" else 1,  # SPU
        "promotion_type": 3 if type == "FlashSale" else 2 if type == "DirectDiscount" else 1,  # FixedPrice
        "request_serial_no": "create" + str(uuid4()),
        "title": "Flashdeal"+title+formatted_date if type == "FlashSale" else "Discount"+title+formatted_date,
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    return data["data"]


def add_update_discount(access_token, title, begin_time, end_time, type, product_type, product_list):
    promotion = create_promotion_form(
        access_token=access_token,
        title=title,
        begin_time=begin_time,
        end_time=end_time,
        type=type,
        product_type=product_type,
    )
    promotion_id = promotion.get("promotion_id")

    response = add_or_update_promotion_discount(
        access_token=access_token, promotion_id=promotion_id, product_list=product_list
    )

    return Response(response, status=status.HTTP_200_OK)


from concurrent.futures import ThreadPoolExecutor, as_completed
from django.http import JsonResponse
import time  # Dùng để tạo khoảng trễ khi thử lại

MAX_RETRIES = 3  # Số lần thử lại tối đa
RETRY_DELAY = 2  # Khoảng thời gian chờ giữa các lần thử lại (tính bằng giây)

def create_promotion_task(access_token, title, begin_time, end_time, type, product_type, sublist, i):
    unique_title = f"{title} #{(i // 1) + 1}"
    retries = 0
    
    while retries < MAX_RETRIES:
        try:
            # Tạo promotion
            promotion = create_promotion_form(
                access_token=access_token,
                title=unique_title,
                begin_time=begin_time,
                end_time=end_time,
                type=type,
                product_type=product_type,
            )
            promotion_id = promotion.get("promotion_id")
            
            # Cập nhật flashdeal cho promotion
            response = add_or_update_promotion_flashdeal(
                access_token=access_token, promotion_id=promotion_id, product_list=sublist
            )
            print(f"Response for chunk {i}:", response)
            return {"status": "Success", "index": i, "response": response}

        except Exception as e:
            retries += 1
            print(f"Error processing chunk at index {i}, retry {retries}/{MAX_RETRIES}: {e}")
            
            if retries >= MAX_RETRIES:
                return {"status": "Failed", "index": i, "error": str(e)}
            
            time.sleep(RETRY_DELAY)  # Chờ một khoảng thời gian trước khi thử lại

def add_update_flashdeal(access_token, title, begin_time, end_time, type, product_type, product_list):
    results = []
    
    if len(product_list) > 1:
        with ThreadPoolExecutor(max_workers=10) as executor:  # Giới hạn số luồng song song là 6
            futures = []
            for i in range(0, len(product_list), 1):
                sublist = product_list[i:i+1]
                print(f"Processing chunk starting at index {i}")
                futures.append(executor.submit(create_promotion_task, access_token, title, begin_time, end_time, type, product_type, sublist, i))

            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                print(f"Task result: {result}")
        
        data = {"status": "Success", "results": results}
    else:
        # Nếu product_list có chiều dài <= 1, tạo 1 promotion duy nhất
        retries = 0
        while retries < MAX_RETRIES:
            try:
                promotion = create_promotion_form(
                    access_token=access_token,
                    title=title,
                    begin_time=begin_time,
                    end_time=end_time,
                    type=type,
                    product_type=product_type,
                )
                
                promotion_id = promotion.get("promotion_id")
                
                response = add_or_update_promotion_flashdeal(
                    access_token=access_token, promotion_id=promotion_id, product_list=product_list
                )
                print("Response for single promotion:", response)
                data = {"status": "Success", "response": response}
                break  # Thoát khỏi vòng lặp khi thành công
            except Exception as e:
                retries += 1
                print(f"Error processing single promotion, retry {retries}/{MAX_RETRIES}: {e}")
                
                if retries >= MAX_RETRIES:
                    data = {"status": "Failed", "error": str(e)}
                
                time.sleep(RETRY_DELAY)  # Chờ một khoảng thời gian trước khi thử lại
    
    return JsonResponse(data)




def get_unpromotion_sku(access_token):
    """
    Get products 
    """
    response = callProductList(access_token=access_token, page_number=1)
    response_page_2 = callProductList(access_token=access_token, page_number=2)
    data = response.json()
    product_active_ids = []
    data_loop = data["data"]["products"]
    if data["data"]["total"] > 100:
        data_page_2 = response_page_2.json()
        for product in data_page_2["data"]["products"]:
            data_loop.append(product)

    for product in data_loop:
        product_active_ids.append(product["id"])

    promoted_product_list = get_promotions_flashdeal(access_token=access_token)

    product_promoted_ids = []
    for promotion in promoted_product_list.get("promotion_list"):
        promotion_id = promotion.get("promotion_id")
        promotion_detail = get_promotion_detail(access_token, promotion_id)
        for product in promotion_detail["data"]["product_list"]:
            product_promoted_ids.append(product["product_id"])
    active_set = set(product_active_ids)
    promoted_set = set(product_promoted_ids)
    unique_active = active_set.difference(promoted_set)
    new_product_list = []
    for product in data["data"]["products"]:
        if product["id"] in unique_active:
            new_product_list.append(product)

    new_data = data.copy()
    new_data["data"]["products"] = new_product_list

    return new_data


def deactivate_promotion(access_token: str, promotion_id: int):
    """
    Deactivate promotion
    """
    url = TIKTOK_API_URL["url_deactivate_promotion"]

    query_params = {"app_key": app_key, "access_token": access_token, "timestamp": SIGN.get_timestamp()}

    body_json = {
        "promotion_id": promotion_id,
        "request_serial_no": "deactivate_promo" + str(uuid4()),
    }

    body = json.dumps(body_json)

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params, body=body)

    query_params["sign"] = sign

    response = requests.post(url=url, params=query_params, json=json.loads(body))

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    logger.info("Promotion deactivated " + str(promotion_id))

    return data["data"]


def detail_promotion(access_token: str, promotion_id: int):
    """
    Deactivate promotion
    """
    url = TIKTOK_API_URL["url_detail_promo"]

    query_params = {
        "app_key": app_key,
        "access_token": access_token,
        "timestamp": SIGN.get_timestamp(),
        "promotion_id": promotion_id,
    }

    sign = SIGN.cal_sign(secret=secret, url=urllib.parse.urlparse(url), query_params=query_params)

    query_params["sign"] = sign

    response = requests.get(url=url, params=query_params)

    data = response.json()
    if data["code"] != 0:
        raise BadRequestException(data["message"])

    logger.info("Promotion deactivated " + str(promotion_id))

    return data["data"]
