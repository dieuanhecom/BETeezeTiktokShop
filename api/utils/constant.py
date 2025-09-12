import os

from dotenv import load_dotenv

load_dotenv(override=True)

secret = os.getenv("SECRET")
app_key = os.getenv("APP_KEY")

TIKTOK_API_URL = {
    "url_product_list": "https://open-api.tiktokglobalshop.com/api/products/search",
    "url_get_access_token": "https://auth.tiktok-shops.com/api/token/getAccessToken",
    "url_get_author_shop": "https://open-api.tiktokglobalshop.com/api/shop/get_authorized_shop",
    "url_refresh_token": "https://auth.tiktok-shops.com/api/token/refreshToken",
    "url_detail_product": "https://open-api.tiktokglobalshop.com/api/products/details",
    "url_get_active_shop": "https://open-api.tiktokglobalshop.com/api/seller/global/active_shops",
    "url_create_product": "https://open-api.tiktokglobalshop.com/product/202309/products",
    "url_get_categories": "https://open-api.tiktokglobalshop.com/api/products/categories",
    "url_get_warehouse": "https://open-api.tiktokglobalshop.com/logistics/202309/warehouses",
    "url_upload_image": "https://open-api.tiktokglobalshop.com/api/products/upload_imgs",
    "url_get_brands": "https://open-api.tiktokglobalshop.com/api/products/brands",
    "url_edit_product": "https://open-api.tiktokglobalshop.com/api/products",
    "url_get_orders": "https://open-api.tiktokglobalshop.com/order/202309/orders/search",
    "url_get_order_detail": "https://open-api.tiktokglobalshop.com/order/202309/orders",
    "url_get_attributes": "https://open-api.tiktokglobalshop.com/api/products/attributes",
    "url_get_globle_categories": "https://open-api.tiktokglobalshop.com/api/product/global_products/categories",
    "url_get_shipping_document": "https://open-api.tiktokglobalshop.com/fulfillment/202309/packages/{package_id}/shipping_documents",
    "url_get_product_attritrute": "https://open-api.tiktokglobalshop.com/api/products/attributes",
    "url_create_draf_product": "https://open-api.tiktokglobalshop.com/api/products/save_draft",
    "url_pre_combine_package": "https://open-api.tiktokglobalshop.com/api/fulfillment/pre_combine_pkg/list",
    "url_confirm_combine_package": "https://open-api.tiktokglobalshop.com/api/fulfillment/pre_combine_pkg/confirm",
    "url_create_label": "https://open-api.tiktokglobalshop.com/fulfillment/202309/packages",
    "url_search_package": "https://open-api.tiktokglobalshop.com/api/fulfillment/search",
    "url_get_shipping_service": "https://open-api.tiktokglobalshop.com/logistics/202309/delivery_options/{delivery_option_id}/shipping_providers",
    "url_create_packages": "https://open-api.tiktokglobalshop.com/api/fulfillment/detail",
    "url_get_category_recommend": "https://open-api.tiktokglobalshop.com/api/product/category_recommend",
    "url_get_shipping_doc": "https://open-api.tiktokglobalshop.com/fulfillment/202309/packages/{package_id}/shipping_documents",
    "url_delete_product": "https://open-api.tiktokglobalshop.com/api/products",
    # promotion
    "url_get_promotions": "https://open-api.tiktokglobalshop.com/api/promotion/activity/list",
    "url_get_promotion_detail": "https://open-api.tiktokglobalshop.com/api/promotion/activity/get",
    "url_create_promotion": "https://open-api.tiktokglobalshop.com/api/promotion/activity/create",
    "url_add_or_update_promotion": "https://open-api.tiktokglobalshop.com/api/promotion/activity/items/addorupdate",
    "url_deactivate_promotion": "https://open-api.tiktokglobalshop.com/api/promotion/activity/deactivate",
    "url_cancel_order": "https://open-api.tiktokglobalshop.com/api/reverse/order/cancel",
    "url_detail_promo": "https://open-api.tiktokglobalshop.com/api/promotion/activity/get",
    "url_get_order_list_new": "https://open-api.tiktokglobalshop.com/order/202309/orders/search",
    "url_get_order_detail_new": "https://open-api.tiktokglobalshop.com/order/202309/orders",
    # finance
    "url_get_statements": "https://open-api.tiktokglobalshop.com/finance/202309/statements",
    "url_get_statement_transactions": "https://open-api.tiktokglobalshop.com/finance/202309/statements/{"
                                      "statement_id}/statement_transactions",
    # tracking
    "url_update_tracking": "https://open-api.tiktokglobalshop.com/fulfillment/202309/orders/{order_id}/shipping_info/update",

    # affiliate
    "url_search_seller_creators": "https://open-api.tiktokglobalshop.com/affiliate_seller/202406/marketplace_creators/search",
    # "url_search_seller_creators" : "https://open-api.tiktokglobalshop.com/affiliate_creator/202410/orders/search",

}


class ProductCreateObject:
    def __init__(
        self,
        is_cod_open,
        package_dimension_unit,
        package_height,
        package_length,
        package_weight,
        package_width,
        category_id,
        warehouse_id,
        description,
        skus,
    ):
        self.is_cod_open = is_cod_open
        self.package_dimension_unit = package_dimension_unit
        self.package_height = package_height
        self.package_length = package_length
        self.package_weight = package_weight
        self.package_width = package_width
        self.category_id = category_id

        self.warehouse_id = warehouse_id
        self.description = description
        self.skus = [SKU(**sku_data) for sku_data in skus]

    def to_json(self):
        skus_json = [sku.to_json() for sku in self.skus]
        return {
            "is_cod_open": self.is_cod_open,
            "package_dimension_unit": self.package_dimension_unit,
            "package_height": self.package_height,
            "package_length": self.package_length,
            "package_weight": self.package_weight,
            "package_width": self.package_width,
            "category_id": self.category_id,
            "warehouse_id": self.warehouse_id,
            "description": self.description,
            "skus": skus_json,
        }


class SKU:
    def __init__(self, sales_attributes, original_price, stock_infos, seller_sku):
        self.sales_attributes = [SalesAttribute(
            **attr) for attr in sales_attributes]
        self.original_price = original_price
        self.stock_infos = [StockInfo(**stock_info)
                            for stock_info in stock_infos]
        self.seller_sku = seller_sku

    def to_json(self):
        sales_attributes_json = [attr.to_json()
                                 for attr in self.sales_attributes]
        stock_infos_json = [info.to_json() for info in self.stock_infos]
        return {
            "sales_attributes": sales_attributes_json,
            "original_price": self.original_price,
            "stock_infos": stock_infos_json,
            "seller_sku": self.seller_sku,
        }


class AttributeValue:
    def __init__(self, value_id, value_name):
        self.value_id = value_id
        self.value_name = value_name

    def to_json(self):
        return {"value_id": self.value_id, "value_name": self.value_name}


class ProductAttribute:
    def __init__(self, attribute_id, attribute_values):
        self.attribute_id = attribute_id
        self.attribute_values = [AttributeValue(
            **value) for value in attribute_values]

    def to_json(self):
        values_json = [value.to_json() for value in self.attribute_values]
        return {"attribute_id": self.attribute_id, "attribute_values": values_json}


class SalesAttribute:
    def __init__(self, attribute_id, attribute_name, custom_value):
        self.attribute_id = attribute_id
        self.attribute_name = attribute_name
        self.custom_value = custom_value

    def to_json(self):
        return {
            "attribute_id": self.attribute_id,
            "attribute_name": self.attribute_name,
            "custom_value": self.custom_value,
        }


class StockInfo:
    def __init__(self, warehouse_id, available_stock):
        self.warehouse_id = warehouse_id
        self.available_stock = available_stock

    def to_json(self):
        return {
            "warehouse_id": self.warehouse_id,
            "available_stock": self.available_stock,
        }


class ProductCreateOneObject:
    def __init__(
        self,
        product_name,
        images,
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
        self.product_name = product_name
        self.images = images
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
        self.product_attributes = [
            ProductAttribute(**attr) for attr in product_attributes
        ]
        self.size_chart = size_chart

    def to_json(self):
        skus_json = [sku.to_json() for sku in self.skus]
        attributes_json = [attr.to_json() for attr in self.product_attributes]
        return {
            "product_name": self.product_name,
            "images": self.images,
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


ROLE_USERGROUP_CHOICES = (
    (0, "Admin"),
    (1, "Manager"),
    (2, "Seller"),
    (3, "Fulfillment Staff"),
)
ROLE_USERGROUP_DEFAULT = 2
MAX_WORKER = 10
REQUEST_TIMEOUT = 300  # 5 minutes for long-running tasks

DOWNLOAD_IMAGES_DIR_WINDOW = "C:/workspace/anhtiktok"
DOWNLOAD_IMAGES_DIR_UNIX = "~/workspace/anhtiktok"
PDF_DIRECTORY_WINDOW = "C:/workspace/pdf"
PDF_DIRECTORY_UNIX = "~/workspace/pdf"
webhook_url = "https://117a-42-114-151-247.ngrok-free.app"
