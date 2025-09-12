class SKU:
    def __init__(self, sales_attributes, original_price, stock_infos, seller_sku):
        self.sales_attributes = (
            [SalesAttribute(**attr) for attr in sales_attributes] if sales_attributes else []
        )
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


class SalesAttribute:
    def __init__(self, attribute_name, custom_value, sku_img=None):
        self.attribute_name = attribute_name
        self.custom_value = custom_value
        # Set sku_img to an empty string if not provided
        self.sku_img = sku_img if sku_img is not None else {}

    def to_json(self):
        return {
            "attribute_name": self.attribute_name,
            "custom_value": self.custom_value,
            "sku_img": str(self.sku_img)
        }


class StockInfo:
    def __init__(self, warehouse_id, available_stock):
        self.warehouse_id = warehouse_id
        self.available_stock = available_stock

    def to_json(self):
        return {"warehouse_id": self.warehouse_id, "available_stock": self.available_stock}


class ProductCreateMultiObject:
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
        size_chart,
        attributes,
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
        self.size_chart = size_chart
        self.attributes = attributes
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
            "size_chart": self.size_chart,
            "attributes": self.attributes,
        }
