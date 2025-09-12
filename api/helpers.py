import base64
import hashlib
import hmac
import io
from datetime import datetime
from uuid import uuid4

from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from PIL import Image, WebPImagePlugin

from api.models import CustomUser
from tiktok.settings import EMAIL_HOST_USER

WebPImageFile = WebPImagePlugin.WebPImageFile


def check_token(user, token):
    return user.customuser.verify_token == token


def send_mail_verification(request, new_user):
    verify_token = uuid4()
    CustomUser.objects.create(user=new_user, verify_token=verify_token)
    mail_subject = "Activate your account."
    verify_url = reverse(
        "verify",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(new_user.pk)),
            "token": str(verify_token),
        },
    )
    mail_message = (
        f"Hi {new_user.username}, Please use this link to verify your account\n"
        f"{request.build_absolute_uri(verify_url)}"
    )
    from_email = EMAIL_HOST_USER
    send_mail(
        mail_subject,
        mail_message,
        from_email,
        [new_user.email],
        fail_silently=False,
    )


class GenerateSign:
    def obj_key_sort(self, obj):
        return {k: obj[k] for k in sorted(obj)}

    def get_timestamp(self):
        return int(datetime.now().timestamp())

    def cal_sign(self, secret, url, query_params, body):
        sorted_params = self.obj_key_sort(query_params)
        sorted_params.pop("sign", None)
        sorted_params.pop("access_token", None)
        sign_string = secret + url.path
        for key, value in sorted_params.items():
            sign_string += key + str(value)
        sign_string += body + secret
        signature = hmac.new(secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
        return signature


class GenerateSignNoBody:
    def obj_key_sort(self, obj):
        return {k: obj[k] for k in sorted(obj)}

    def get_timestamp(self):
        return int(datetime.now().timestamp())

    def cal_sign(self, secret, url, query_params):
        sorted_params = self.obj_key_sort(query_params)
        sorted_params.pop("sign", None)
        sorted_params.pop("access_token", None)
        sign_string = secret + url.path
        for key, value in sorted_params.items():
            sign_string += key + str(value)
        sign_string += secret
        signature = hmac.new(secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
        return signature


class AttributeValue:
    def __init__(self, value_id, value_name):
        self.value_id = value_id
        self.value_name = value_name

    def to_json(self):
        return {"value_id": self.value_id, "value_name": self.value_name}


class ProductAttribute:
    def __init__(self, attribute_id, attribute_values):
        self.attribute_id = attribute_id
        self.attribute_values = [AttributeValue(**value) for value in attribute_values]

    def to_json(self):
        values_json = [value.to_json() for value in self.attribute_values]
        return {"attribute_id": self.attribute_id, "attribute_values": values_json}


class ProductObject:
    def __init__(
        self,
        product_id,
        product_name,
        images,
        price,
        is_cod_open,
        package_dimension_unit,
        package_height,
        package_length,
        package_weight,
        package_width,
        category_id,
        brand_id,
        description,
        skus,
        product_attributes,
        size_chart,
    ):
        self.product_id = product_id
        self.product_name = product_name
        self.images = images
        self.price = price
        self.is_cod_open = is_cod_open
        self.package_dimension_unit = package_dimension_unit
        self.package_height = package_height
        self.package_length = package_length
        self.package_weight = package_weight
        self.package_width = package_width
        self.category_id = category_id
        self.brand_id = brand_id
        self.description = description
        self.skus = [SKU(**sku_data) for sku_data in skus]
        self.product_attributes = [ProductAttribute(**attr) for attr in product_attributes]
        self.size_chart = size_chart

    def to_json(self):
        skus_json = [sku.to_json() for sku in self.skus]
        attributes_json = [attr.to_json() for attr in self.product_attributes]
        return {
            "product_id": self.product_id,
            "product_name": self.product_name,
            "images": [{"id": image["id"]} for image in self.images],
            "price": self.price,
            "is_cod_open": self.is_cod_open,
            "package_dimension_unit": self.package_dimension_unit,
            "package_height": self.package_height,
            "package_length": self.package_length,
            "package_weight": self.package_weight,
            "package_width": self.package_width,
            "category_id": self.category_id,
            "brand_id": self.brand_id,
            "description": self.description,
            "skus": skus_json,
            "product_attributes": attributes_json,
            "size_chart": self.size_chart,
        }


class SKU:
    def __init__(self, sales_attributes, original_price, stock_infos, seller_sku):
        self.sales_attributes = [SalesAttribute(**attr) for attr in sales_attributes]
        self.original_price = original_price
        self.stock_infos = [StockInfo(**stock_info) for stock_info in stock_infos]
        self.seller_sku = seller_sku

    def to_json(self):
        sales_attributes_json = [attr.to_json() for attr in self.sales_attributes]
        stock_infos_json = [info.to_json() for info in self.stock_infos]
        return {
            "sales_attributes": sales_attributes_json,
            "original_price": self.original_price,
            "stock_infos": stock_infos_json,
            "seller_sku": self.seller_sku,
        }


class SalesAttribute:
    def __init__(self, attribute_id, attribute_name, value_id, value_name):
        self.attribute_id = attribute_id
        self.attribute_name = attribute_name
        self.value_id = value_id
        self.value_name = value_name

    def to_json(self):
        return {
            "attribute_id": self.attribute_id,
            "attribute_name": self.attribute_name,
            "value_id": self.value_id,
            "value_name": self.value_name,
        }


class StockInfo:
    def __init__(self, warehouse_id, available_stock):
        self.warehouse_id = warehouse_id
        self.available_stock = available_stock

    def to_json(self):
        return {"warehouse_id": self.warehouse_id, "available_stock": self.available_stock}


def count_bits(img_data):
    image = Image.open(io.BytesIO(base64.b64decode(img_data)))
    mode_to_bpp = {"1": 1, "L": 8, "P": 8, "RGB": 24, "RGBA": 32, "CMYK": 32, "YCbCr": 24, "I": 32, "F": 32}
    data = mode_to_bpp[image.mode]
    return data


def convert_to_rgb(img_data):
    try:
        image = Image.open(io.BytesIO(base64.b64decode(img_data)))
        rgb_image = Image.new("RGB", image.size)
        rgb_image.paste(image)
        buffered = io.BytesIO()
        rgb_image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception:
        return None
