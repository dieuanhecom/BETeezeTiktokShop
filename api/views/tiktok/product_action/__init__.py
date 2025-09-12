import base64
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import requests
import random
from api.utils.tiktok_base_api import token

from api import helpers, setup_logging
from api.utils import constant, objectcreate
from api.utils.tiktok_base_api import product
from api.views import (
    APIView,
    HttpResponse,
    JsonResponse,
    ObjectDoesNotExist,
    Response,
    View,
    csrf_exempt,
    get_object_or_404,
    method_decorator,
    status,
)

from ....models import Brand, Categories, ErrorCodes, Shop
from io import BytesIO
from PIL import Image
from io import BytesIO
from PIL import Image
logger = logging.getLogger("api.views.tiktok.product")
setup_logging(logger, is_root=False, level=logging.INFO)

"""Product"""


class ListProduct(APIView):
    def get(self, request, shop_id: str, page_number: str):
        shop = get_object_or_404(Shop, id=shop_id)

        try:
            response = product.callProductList(access_token=shop.access_token, page_number=page_number, app_key = shop.app_key, app_secret = shop.app_secret)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get list products in page_number {page_number}", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy danh sách sản phẩm từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            content = response.content
            return HttpResponse(content, content_type="application/json")


class ProductDetail(APIView):
    def get(self, request, shop_id, product_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token

        try:
            response = product.callProductDetail(access_token=access_token, product_id=product_id, app_key = shop.app_key, app_secret = shop.app_secret)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get product detail with product_id {product_id}", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy chi tiết sản phẩm từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            content = response.content
            return HttpResponse(content, content_type="application/json")


class CreateOneProduct(APIView):
    def upload_images(self, base64_images, access_token):
        images_ids = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(product.callUploadImage, access_token, img_data) for img_data in base64_images]

            for idx, future in enumerate(futures):
                logger.info(
                    f"User {self.request.user}: Upload image [{idx} | {len(futures)}] result: {future.result()}",
                    exc_info=True,
                )
                img_id = future.result()
                if img_id:
                    images_ids.append(img_id)

        return images_ids

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        product_data = json.loads(body_raw)
        base64_images = product_data.pop("images", [])
        base64_images_size_chart = product_data.get("size_chart")

        try:
            images_ids = self.upload_images(base64_images, access_token)
        except Exception as e:
            logger.error(f"User {request.user}: Error when upload images", exc_info=e)
        img_size_chart = base64_images_size_chart.get("img_id")
        if img_size_chart != "":
            images_id_size_chart = product.callUploadImage(access_token, img_size_chart)
        else:
            images_id_size_chart = None

        product_object = None
        try:
            product_object = constant.ProductCreateOneObject(
                product_name=product_data.get("product_name"),
                images=images_ids,
                is_cod_open=product_data.get("is_cod_open"),
                package_dimension_unit=product_data.get("package_dimension_unit"),
                package_height=product_data.get("package_height"),
                package_length=product_data.get("package_length"),
                package_weight=product_data.get("package_weight"),
                package_width=product_data.get("package_width"),
                category_id=product_data.get("category_id"),
                brand_id=product_data.get("brand_id"),
                description=product_data.get("description"),
                skus=product_data.get("skus"),
                product_attributes=product_data.get("product_attributes"),
                size_chart=images_id_size_chart,
            )
        except Exception as e:
            logger.error("Error when create product object from request body", exc_info=e)
            return JsonResponse(
                {"status": "error", "message": "Error occurred while creating product object"}, status=500
            )

        try:
            response = product.callCreateOneProduct(access_token, product_object)
            response_data = response.json()
            if response_data["data"] is None:
                error_message = response_data["message"]

                logger.error(f"User {request.user}: Error when create product: {error_message}")

                return JsonResponse({"message": error_message}, status=400)
            else:
                response_text = response.text
                return HttpResponse(response_text, content_type="text/plain", status=200)
        except Exception as e:
            logger.error(f"User {request.user}: Error when create product", exc_info=e)
            return JsonResponse({"message": "Error occurred while calling create product API"}, status=400)


class CreateOneProductDraf(APIView):
    def upload_images(self, base64_images, access_token):
        images_ids = []

        for img_data in base64_images:
            if img_data is not None:
                img_id = product.callUploadImage(access_token=access_token, img_data=img_data)
                if img_id != "":
                    images_ids.append(img_id)

        return images_ids

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        product_data = json.loads(body_raw)
        base64_images = product_data.get("images", [])

        images_ids = self.upload_images(base64_images=base64_images, access_token=access_token)

        product_object = constant.ProductCreateOneObject(
            product_name=product_data.get("product_name"),
            images=images_ids,
            is_cod_open=product_data.get("is_cod_open"),
            package_dimension_unit=product_data.get("package_dimension_unit"),
            package_height=product_data.get("package_height"),
            package_length=product_data.get("package_length"),
            package_weight=product_data.get("package_weight"),
            package_width=product_data.get("package_width"),
            category_id=product_data.get("category_id"),
            brand_id=product_data.get("brand_id"),
            description=product_data.get("description"),
            skus=product_data.get("skus"),
            product_attributes=product_data.get("product_attributes"),
        )

        product.callCreateOneProductDraf(access_token, product_object)

        return JsonResponse({"status": "success"}, status=201)

# @method_decorator(csrf_exempt, name="dispatch")
# class ProcessExcelDropShip(View):
#     def post(self, request, shop_id):
#         try:
#             self.request = request  # Set request to self to use in other functions
#             data = json.loads(self.request.body.decode("utf-8"))

#             # Parse data from request
#             excel_data = data.get("excel", [])
#             category_id = data.get("category_id", "")
#             warehouse_id = data.get("warehouse_id", "")
#             is_cod_open = data.get("is_cod_open", "")
#             package_height = data.get("package_height", 1)
#             package_length = data.get("package_length", 1)
#             package_weight = data.get("package_weight", "1")
#             package_width = data.get("package_width", 1)
#             description = data.get("description", "")
#             skus = data.get("skus", [])
#             size_chart = data.get("size_chart", "")
#             images_link_variant = data.get("images_link_variant",[])
#             images_link_variant_ids = []
#             self.shop = Shop.objects.get(id=shop_id)
#             print("get images_link_variant",images_link_variant)
           
#             if images_link_variant and images_link_variant != []:
#                 for image_url in images_link_variant:
#                     result_data_base64 = self._process_image_url(image_url)
                    
#                     response = product.callUploadImage(
#                         self.shop.access_token, img_data=result_data_base64["data"], return_id=False
#                     )
                    
#                     data = json.loads(response.text)
#                     img_id = data["data"]["img_id"]
#                     images_link_variant_ids.append(img_id)
                                            
                        
#             print("ids images_link_variant",images_link_variant_ids)
           
#             # Get shop object that user want to create product
            

#             # Process each item in excel file
#             processing_result = []  # Storing result of each item in excel file
#             with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
#                 futures = {}

#                 # Submit each item to process
#                 for order, item in enumerate(excel_data):
#                     future = executor.submit(
#                         self.process_item,
#                         item,
#                         category_id,
#                         warehouse_id,
#                         is_cod_open,
#                         package_height,
#                         package_length,
#                         package_weight,
#                         package_width,
#                         item.get("description", "") + description,
#                         skus,
#                         size_chart,
#                         images_link_variant_ids
#                     )
#                     futures[future] = (order, item)
                

#                 for idx, future in enumerate(list(futures.keys())):
#                     order_in_excel_file, item = futures[future]
#                     result = future.result()

#                     if result["status"] == "error":
#                         # Return error response
#                         error_response = {
#                             "order_in_excel": order_in_excel_file + 1,
#                             "title": item.get("title", ""),
#                             "status": "error",
#                             "detail": {
#                                 "message": result["message"],
#                                 "data": result["data"],
#                             },
#                         }
#                         processing_result.append(error_response)
#                     else:
#                         # Return success response
#                         success_response = {
#                             "order_in_excel": order_in_excel_file + 1,
#                             "title": item.get("title", ""),
#                             "status": "success",
#                             "detail": None,
#                         }
#                         processing_result.append(success_response)

#                     logger.info(f"Done item [{idx + 1} | {len(futures)}]")

#             return JsonResponse(processing_result, status=201, json_dumps_params={"ensure_ascii": False}, safe=False)

#         except ObjectDoesNotExist as e:
#             return HttpResponse({"error": str(e)}, status=404)
#         except Exception as e:
#             logger.error("Error when process excel file", exc_info=e)
#             return HttpResponse({"error": str(e)}, status=400)

#     """ Main function to process each item in excel file"""

#     def process_item(
#         self,
#         item,
#         category_id,
#         warehouse_id,
#         is_cod_open,
#         package_height,
#         package_length,
#         package_weight,
#         package_width,
#         description,
#         skus,
#         size_chart,
#         images_link_variant_ids
#     ) -> dict:
#         # ============ STEP 1: Download images and convert to base64 ============
#         logger.info(f"User {self.request.user} | Start download images and convert to base64: {item.get('title', '')}")
#         images = item.get("images", [])
#         base64_size_chart_images = []  # To store size chart images that are already in base64 format
#         success_images = []  # To store success images, each item would be (image_url: str, base64: str)
#         error_images = []  # To store error images, each item would be {"image_url": str, "response": dict}
#         print("image", images)
#         with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
#             futures = {}

#             for col, value in images.items():
#                 if value.startswith("https"):
#                     image_url = value
#                     future = executor.submit(self._process_image_url, image_url)
#                     futures[future] = (col, image_url)
#                 elif value.startswith("white"):
#                     value = value[len("white_") :]
#                     base64_size_chart_images.append({"column": col, "image_url": "", "base64": value, "main": True})
#                 else:
#                     # Size chart images are already in base64 format
#                     base64_size_chart_images.append({"column": col, "image_url": "", "base64": value, "main": False})

#             for future in list(futures.keys()):
#                 col, image_url = futures[future]
#                 result = future.result()
#                 if result["status"] == "success":
#                     success_images.append({"column": col, "image_url": image_url, "base64": result["data"]})
#                 else:
#                     error_images.append({"column": col, "image_url": image_url, "response": result})

#         # Checkpoint 1: If there is any error when download and convert images to
#         code = "E001"
#         message = ErrorCodes.objects.get(code=code).message
#         if len(error_images) == len(images):  # All images are error
#             logger.error(f"User {self.request.user} | message", exc_info=True)
#             return {
#                 "status": "error",
#                 "message": message,
#                 "data": error_images,
#             }

#         # ============ STEP 2: Upload images to TikTok and get images ids ============

#         logger.info(f"User {self.request.user} | Start upload images to TikTok")
#         for fix_image in base64_size_chart_images:
            
#             fix_image_dump = {
#                 "column": fix_image.get("column"),
#                 "image_url": fix_image.get("image_url"),
#                 "base64": fix_image.get("base64"),
#             }
#             if fix_image.get("main") == True:
#                 success_images = [fix_image_dump] + success_images

#             else:
#                 success_images.extend([fix_image_dump])

#         result = self._upload_images(success_images)

#         code = "E002"
#         message = ErrorCodes.objects.get(code=code).message
#         if result["status"] == "error":
#             logger.error(f"User {self.request.user} | {message}: {result['message']}")
#             return {
#                 "status": "error",
#                 "code": code,
#                 "message": message,
#                 "data": result["data"],
#             }

#         # Get images ids
#         images_ids = [x.get("img_id") for x in result["data"]]

#         # STEP 3: Create product with images ids and other data
#         result = self._call_create_product(
#             item,
#             category_id,
#             warehouse_id,
#             is_cod_open,
#             package_height,
#             package_length,
#             package_weight,
#             package_width,
#             images_ids,
#             description,
#             skus,
#             size_chart,
#             images_link_variant_ids
#         )

#         return result

#     """ Utils function for bigger function"""

#     def __convert_to_base64(self, image_url: str, image_data: str) -> dict:
#         try:
            
            
#             # Mã hóa dữ liệu ảnh thành chuỗi base64
#             base64_data = image_data
#             return {
#                 "status": "success",
#                 "message": None,
#                 "data": base64_data,
#             }
#         except Exception as e:
#             logger.error(f"User {self.request.user} | Failed when convert base64: {image_url}", exc_info=True)
#             return {
#                 "status": "error",
#                 "message": f"User {self.request.user} | Failed when convert base64 {image_url}: {str(e)}",
#                 "data": None,
#             }

#     def __upload_single_image(self, item: dict) -> dict:
#         """
#             This function will upload a single image to TikTok and return the image id
#         Args:
#             item (dict): The item contains column name, image url and base64 string

#         Returns:
#             dict:
#             ```
#             {
#                 "status": "success" or "error",
#                 "message": "Error message" | None,
#                 "data": "Image id" | None
#             }
#             ```
#         """
#         try:
#             response = product.callUploadImage(self.shop.access_token, img_data=item["base64"], return_id=False, app_key=self.shop.app_key, app_secret=self.shop.app_secret)

#             data = json.loads(response.text)

#             if data:
#                 if data.get("data") is None:
#                     code = "E002"
#                     message = ErrorCodes.objects.get(code=code).message
#                     return {
#                         "status": "error",
#                         "code": code,
#                         "message": message,
#                         "data": data,
#                     }
#                 else:
#                     img_id = data["data"]["img_id"]
#                     return {
#                         "status": "success",
#                         "message": None,
#                         "data": img_id,
#                     }
#             else:
#                 return {
#                     "status": "error",
#                     "message": f"Response status code: {response.status_code}\nResponse text: {response.text}",
#                     "data": None,
#                 }
#         except Exception as e:
#             logger.error(
#                 f"User {self.request.user} | Failed to upload image: {item['image_url']}",
#                 exc_info=True,
#             )
#             return {
#                 "status": "error",
#                 "message": str(e),
#                 "data": None,
#             }

#     """ Utils for main function"""

#     def _process_image_url(self, image_url: str) -> dict:
#         """
#             This function will convert from a valid image url to a base64 string
#         Args:
#             image_url (str): The url of the image

#         Returns:
#             dict:
#             ```
#             {
#                 "status": "success" or "error",
#                 "message": "Error message" | None,
#                 "data": "Base64 string" | None
#             }
#             ```
#         """
#         if image_url:
#             try:
#                 headers = {
#                     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#                 }
#                 response = requests.get(
#                     image_url, headers=headers, timeout=constant.REQUEST_TIMEOUT)
#             except Exception as e:
#                 logger.error(f"User {self.request.user} | Failed to download image: {image_url}", exc_info=True)
#                 return {
#                     "status": "error",
#                     "message": f"User {self.request.user} | Failed to download image: {image_url}: {str(e)}",
#                     "data": None,
#                 }

#             if response.status_code == 200:
#                 img = Image.open(BytesIO(response.content))
#                 if img.mode == 'RGBA':
#                     img = img.convert('RGB')
#                 buffered = BytesIO()
#                 img.save(buffered, format="JPEG")

#                 # Chuyển dữ liệu ảnh thành chuỗi base64
#                 img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
#                 convert_result = self.__convert_to_base64(image_url, img_base64)
#                 img = Image.open(BytesIO(response.content))
#                 if img.mode == 'RGBA':
#                     img = img.convert('RGB')
#                 buffered = BytesIO()
#                 img.save(buffered, format="JPEG")

#                 # Chuyển dữ liệu ảnh thành chuỗi base64
#                 img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
#                 convert_result = self.__convert_to_base64(image_url, img_base64)
#                 return convert_result
#             else:
#                 logger.error(
#                     f"User {self.request.user} | Failed to download image ({response.status_code}): {image_url}\nResponse:{response.text}",  # noqa: E501
#                 )
#                 return {
#                     "status": "error",
#                     "message": f"User {self.request.user} | Failed to download image ({response.status_code}): {image_url}",  # noqa: E501
#                     "data": None,
#                 }

#     def _upload_images(self, success_images: list[dict]) -> list:
#         images_ids = []
#         error_images = []

#         with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
#             futures = {}

#             for item in success_images:
#                 future = executor.submit(self.__upload_single_image, item)
#                 futures[future] = item

#             for future in list(futures.keys()):
#                 item = futures[future]
#                 result = future.result()

#                 if result["status"] == "success":
#                     images_ids.append(
#                         {"column": item["column"], "image_url": item["image_url"], "img_id": result["data"]}
#                     )
#                 else:
#                     error_images.append({"column": item["column"], "image_url": item["image_url"], "response": result})

#         if len(error_images) == len(success_images):  # All images are error
#             return {
#                 "status": "error",
#                 "message": "Error when upload images to TikTok",
#                 "data": error_images,
#             }

#         return {
#             "status": "success",
#             "message": None,
#             "data": images_ids,
#         }

#     def _call_create_product(
#         self,
#         item: dict,
#         category_id: str,
#         warehouse_id: str,
#         is_cod_open: bool,
#         package_height: float,
#         package_length: float,
#         package_weight: float,
#         package_width: float,
#         images_ids: list,
#         description: str,
#         skus: list,
#         size_chart: str,
#         images_link_variant_ids:list
#     ):
#         try:
#             title = item.get("title", "")
#             seller_sku = item.get("sku", "")

            

#             # if images_link_variant_ids and  images_link_variant_ids != []:
#             #     number_of_colors = len(images_link_variant_ids)
#             #     # Duyệt qua từng sku
#             #     for index, sku in enumerate(skus):
#             #         sales_attributes = sku.get("sales_attributes", [])
                    
#             #         # Tính chỉ số màu sắc cho SKU hiện tại
#             #         color_index = index % number_of_colors  # Lấy chỉ số màu theo số SKU

#             #         # Gán URI cho phần tử đầu tiên trong sales_attributes
#             #         if sales_attributes and len(sales_attributes) > 0:
#             #             # Kiểm tra và khởi tạo sku_img nếu chưa tồn tại
#             #             if "sku_img" not in sales_attributes[0]:
#             #                 sales_attributes[0]["sku_img"] = {}
#             #             sales_attributes[0]["sku_img"]["uri"] = images_link_variant_ids[color_index]
#             # if images_link_variant_ids and images_link_variant_ids != []:
#             #     number_of_colors = len(images_link_variant_ids)
#             #     color_uri_mapping = {}  # Tạo một dictionary để lưu trữ URI của từng màu

#             #     # Duyệt qua từng sku
#             #     for index, sku in enumerate(skus):
#             #         sales_attributes = sku.get("sales_attributes", [])

#             #         # Tìm thuộc tính "Color" trong sales_attributes
#             #         color_attribute = next((attr for attr in sales_attributes if attr["attribute_name"] == "Color"), None)
                    
#             #         if color_attribute:
#             #             color_value = color_attribute["custom_value"]
                        
#             #             # Nếu màu chưa có trong mapping, gán URI từ danh sách hình ảnh
#             #             if color_value not in color_uri_mapping:
#             #                 color_index = len(color_uri_mapping) % number_of_colors
#             #                 color_uri_mapping[color_value] = images_link_variant_ids[color_index]
                        
#             #             # Gán URI cho thuộc tính "sku_img" của màu đó
#             #             color_attribute["sku_img"] = {
#             #                 "uri": color_uri_mapping[color_value]
#             #             }

            
#             product_object = objectcreate.ProductCreateMultiObject(
#                 is_cod_open=is_cod_open,
#                 package_dimension_unit="metric",
#                 package_height=package_height,
#                 package_length=package_length,
#                 package_weight=package_weight,
#                 package_width=package_width,
#                 category_id=category_id,
#                 warehouse_id=warehouse_id,
#                 description=description,
#                 skus=skus,
#                 size_chart=size_chart,
#             )
#         except Exception as e:
#             message = f"Error occurred while creating product object: {str(e)}"
#             logger.error(f"User {self.request.user} | {message}", exc_info=True)
#             return {
#                 "status": "error",
#                 "message": message,
#                 "data": None,
#             }

#         # Call the create product API
#         for sku in skus:
#             try:
#                 response = product.createProduct(self.shop.access_token, self.shop.shop_cipher, title, images_ids, product_object, app_key= self.shop.app_key, app_secret = self.shop.app_secret)
#             except Exception as e:
#                 logger.error(
#                     f"User {self.request.user} | Error when call API create product: {title}",
#                     exc_info=True,
#                 )
#                 return {
#                     "status": "error",
#                     "message": f"User {self.request.user} | Error occurred while calling create product API: {str(e)}",
#                     "data": None,
#                 }
#         else:
#             # logger.info(
#             #     f"User {self.request.user} | Call create product API for item with title {title}'s response: \
#             #     \n{json.dumps(response.json(), indent=4)}\n"
#             # )

#             response_json: dict = json.loads(response.text)

#             if response_json.get("data") is None:
#                 code = "E003"
#                 message = ErrorCodes.objects.get(code=code).message
#                 return {
#                     "status": "error",
#                     "code": code,
#                     "message": message,
#                     "data": response_json,
#                 }

#             return {
#                 "status": "success",
#                 "message": None,
#                 "data": response_json,
#             }
@method_decorator(csrf_exempt, name="dispatch")
class ProcessExcel(View):
    def post(self, request, shop_id):
        try:
            self.request = request  # Set request to self to use in other functions
            data = json.loads(self.request.body.decode("utf-8"))

            # Parse data from request
            excel_data = data.get("excel", [])
            category_id = data.get("category_id", "")
            warehouse_id = data.get("warehouse_id", "")
            is_cod_open = data.get("is_cod_open", "")
            package_height = data.get("package_height", 1)
            package_length = data.get("package_length", 1)
            package_weight = data.get("package_weight", "1")
            package_width = data.get("package_width", 1)
            description = data.get("description", "")
            skus = data.get("skus", [])
            size_chart = data.get("size_chart", "")
            images_link_variant = data.get("images_link_variant",[])
            images_link_variant_ids = []
            fixed_image_ids=[]
            size_chart_id=""
            self.shop = Shop.objects.get(id=shop_id)
            # fixed_images = data.get("fixed_images", [])
            attributes = data.get("attributes", [])
            fixed_image_urls = data.get("fixed_image_urls", [])
            size_chart_url = data.get("size_chart_url", "")

            # print("get types skus",skus)
           
            if fixed_image_urls and fixed_image_urls != []:
                for image_base64 in fixed_image_urls:
                    result_data_base64 = self._process_image_url(image_base64)
                    
                    response = product.callUploadImage(
                        self.shop.access_token, img_data=result_data_base64["data"], app_key=self.shop.app_key, app_secret= self.shop.app_secret, return_id=True
                    )
                    
                    # data = json.loads(response.text)
                    img_id = response
                    fixed_image_ids.append(img_id)
            
                        
            if images_link_variant and images_link_variant != []:
                for image_url in images_link_variant:
                    result_data_base64 = self._process_image_url(image_url)
                    
                    response = product.callUploadImage(
                        self.shop.access_token, img_data=result_data_base64["data"], app_key=self.shop.app_key, app_secret= self.shop.app_secret, return_id=True
                    )
                    
                    # data = json.loads(response.text)
                    img_id = response
                    images_link_variant_ids.append(img_id)

            if size_chart_url != "" and size_chart_url != None and size_chart_url != "null":

                result_data_base64 = self._process_image_url(size_chart_url)

                response = product.callUploadImage(
                    self.shop.access_token, img_data=result_data_base64["data"], app_key=self.shop.app_key, app_secret= self.shop.app_secret, return_id=True
                )
                # data = json.loads(response.text)
                size_chart_id = response


            # Get shop object that user want to create product
            

            # Process each item in excel file
            processing_result = []  # Storing result of each item in excel file
            with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
                futures = {}

                # Submit each item to process
                if all(isinstance(item, list) for item in skus):
                    for order, item in enumerate(excel_data):
                        # Đảm bảo index không vượt quá chiều dài của skus
                            if order < len(skus):
                                future = executor.submit(
                                    self.process_item,
                                    item,
                                    category_id,
                                    warehouse_id,
                                    is_cod_open,
                                    package_height,
                                    package_length,
                                    package_weight,
                                    package_width,
                                    item.get("description", "") + description,
                                    skus[order],  # Sử dụng phần tử skus theo index của excel_data
                                    size_chart_id,
                                    images_link_variant_ids,
                                    fixed_image_ids,
                                    attributes
                                )
                                futures[future] = (order, item)
                            else:
                                logger.warning(f"Index {order} out of range for skus array.") 
                else:
                        for order, item in enumerate(excel_data):
                            future = executor.submit(
                                self.process_item,
                                item,
                                category_id,
                                warehouse_id,
                                is_cod_open,
                                package_height,
                                package_length,
                                package_weight,
                                package_width,
                                item.get("description", "") + description,
                                skus,
                                size_chart_id,
                                images_link_variant_ids,
                                fixed_image_ids,
                                attributes
                            )
                            futures[future] = (order, item)   
                            

                for idx, future in enumerate(list(futures.keys())):
                    order_in_excel_file, item = futures[future]
                    result = future.result()

                    if result["status"] == "error":
                        # Return error response
                        error_response = {
                            "order_in_excel": order_in_excel_file + 1,
                            "title": item.get("title", ""),
                            "status": "error",
                            "detail": {
                                "message": result["message"],
                                "data": result["data"],
                            },
                        }
                        processing_result.append(error_response)
                    else:
                        # Return success response
                        success_response = {
                            "order_in_excel": order_in_excel_file + 1,
                            "title": item.get("title", ""),
                            "status": "success",
                            "detail": None,
                        }
                        processing_result.append(success_response)

                    logger.info(f"Done item [{idx + 1} | {len(futures)}]")

            return JsonResponse(processing_result, status=201, json_dumps_params={"ensure_ascii": False}, safe=False)

        except ObjectDoesNotExist as e:
            return HttpResponse({"error": str(e)}, status=404)
        except Exception as e:
            logger.error("Error when process excel file", exc_info=e)
            return HttpResponse({"error": str(e)}, status=400)

    """ Main function to process each item in excel file"""

    def process_item(
        self,
        item,
        category_id,
        warehouse_id,
        is_cod_open,
        package_height,
        package_length,
        package_weight,
        package_width,
        description,
        skus,
        size_chart_id,
        images_link_variant_ids,
        fixed_image_ids,
        attributes
    ) -> dict:
        # ============ STEP 1: Download images and convert to base64 ============
        logger.info(f"User {self.request.user} | Start download images and convert to base64: {item.get('title', '')}")
        images = item.get("images", [])
        base64_size_chart_images = []  # To store size chart images that are already in base64 format
        success_images = []  # To store success images, each item would be (image_url: str, base64: str)
        error_images = []  # To store error images, each item would be {"image_url": str, "response": dict}
        # print("item imagesss", images)
        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = {}

            for col, value in images.items():
                if value.startswith("https"):
                    image_url = value
                    future = executor.submit(self._process_image_url, image_url)
                    futures[future] = (col, image_url)
                elif value.startswith("white"):
                    value = value[len("white_") :]
                    base64_size_chart_images.append({"column": col, "image_url": "", "base64": value, "main": True})
                else:
                    # Size chart images are already in base64 format
                    base64_size_chart_images.append({"column": col, "image_url": "", "base64": value, "main": False})

            for future in list(futures.keys()):
                col, image_url = futures[future]
                result = future.result()
                # print("result", result)
                if result["status"] == "success":
                    success_images.append({"column": col, "image_url": image_url, "base64": result["data"]})
                else:
                    error_images.append({"column": col, "image_url": image_url, "response": result})

        # Checkpoint 1: If there is any error when download and convert images to
        code = "E001"
        try:
            message = ErrorCodes.objects.get(code=code).message
        except Exception as e:
            message = "Error when upload images to TikTok"
        if len(error_images) == len(images):  # All images are error
            logger.error(f"User {self.request.user} | message", exc_info=True)
            return {
                "status": "error",
                "message": message,
                "data": error_images,
            }

        # ============ STEP 2: Upload images to TikTok and get images ids ============

        logger.info(f"User {self.request.user} | Start upload images to TikTok")
        for fix_image in base64_size_chart_images:
            
            fix_image_dump = {
                "column": fix_image.get("column"),
                "image_url": fix_image.get("image_url"),
                "base64": fix_image.get("base64"),
            }
            if fix_image.get("main") == True:
                success_images = [fix_image_dump] + success_images

            else:
                success_images.extend([fix_image_dump])

        result = self._upload_images(success_images)

        code = "E002"
        try:
            message = ErrorCodes.objects.get(code=code).message
        except Exception as e:
            message = "Error when upload images to TikTok"
        if result["status"] == "error":
            logger.error(f"User {self.request.user} | {message}: {result['message']}")
            return {
                "status": "error",
                "code": code,
                "message": message,
                "data": result["data"],
            }

        # Get images ids
        images_ids = [x.get("img_id") for x in result["data"]]
        # nối fixed_image_ids vào images_ids
        images_ids = images_ids + fixed_image_ids

        # STEP 3: Create product with images ids and other data
        result = self._call_create_product(
            item,
            category_id,
            warehouse_id,
            is_cod_open,
            package_height,
            package_length,
            package_weight,
            package_width,
            images_ids,
            description,
            skus,
            size_chart_id,
            images_link_variant_ids,
            attributes
        )

        return result

    """ Utils function for bigger function"""

    def __convert_to_base64(self, image_url: str, image_data: str) -> dict:
        try:
            
            
            # Mã hóa dữ liệu ảnh thành chuỗi base64
            base64_data = image_data
            return {
                "status": "success",
                "message": None,
                "data": base64_data,
            }
        except Exception as e:
            logger.error(f"User {self.request.user} | Failed when convert base64: {image_url}", exc_info=True)
            return {
                "status": "error",
                "message": f"User {self.request.user} | Failed when convert base64 {image_url}: {str(e)}",
                "data": None,
            }

    def __upload_single_image(self, item: dict) -> dict:
        """
            This function will upload a single image to TikTok and return the image id
        Args:
            item (dict): The item contains column name, image url and base64 string

        Returns:
            dict:
            ```
            {
                "status": "success" or "error",
                "message": "Error message" | None,
                "data": "Image id" | None
            }
            ```
        """
     
        try:
            response = product.callUploadImage(self.shop.access_token, img_data=item["base64"], return_id=False, app_key=self.shop.app_key, app_secret=self.shop.app_secret)

            data = json.loads(response.text)

            if data:
                if data.get("data") is None:
                    code = "E002"
                    try:
                        message = ErrorCodes.objects.get(code=code).message
                    except Exception as e:
                        message = "Error when upload images to TikTok"
                    return {
                        "status": "error",
                        "code": code,
                        "message": message,
                        "data": data,
                    }
                else:
                    img_id = data["data"]["img_id"]
                    return {
                        "status": "success",
                        "message": None,
                        "data": img_id,
                    }
            else:
                return {
                    "status": "error",
                    "message": f"Response status code: {response.status_code}\nResponse text: {response.text}",
                    "data": None,
                }
        except Exception as e:
            logger.error(
                f"User {self.request.user} | Failed to upload image: {item['image_url']}",
                exc_info=True,
            )
            return {
                "status": "error",
                "message": str(e),
                "data": None,
            }

    """ Utils for main function"""

    def _process_image_url(self, image_url: str) -> dict:
        """
            This function will convert from a valid image url to a base64 string
        Args:
            image_url (str): The url of the image

        Returns:
            dict:
            ```
            {
                "status": "success" or "error",
                "message": "Error message" | None,
                "data": "Base64 string" | None
            }
            ```
        """
        if image_url:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = requests.get(
                    image_url, headers=headers, timeout=constant.REQUEST_TIMEOUT)
            except Exception as e:
                logger.error(f"User {self.request.user} | Failed to download image: {image_url}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"User {self.request.user} | Failed to download image: {image_url}: {str(e)}",
                    "data": None,
                }

            if response.status_code == 200:
                img = Image.open(BytesIO(response.content))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                buffered = BytesIO()
                img.save(buffered, format="JPEG")

                # Chuyển dữ liệu ảnh thành chuỗi base64
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                convert_result = self.__convert_to_base64(image_url, img_base64)
                img = Image.open(BytesIO(response.content))
                if img.mode == 'RGBA':
                    img = img.convert('RGB')
                buffered = BytesIO()
                img.save(buffered, format="JPEG")

                # Chuyển dữ liệu ảnh thành chuỗi base64
                img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                convert_result = self.__convert_to_base64(image_url, img_base64)
                return convert_result
            else:
                logger.error(
                    f"User {self.request.user} | Failed to download image ({response.status_code}): {image_url}\nResponse:{response.text}",  # noqa: E501
                )
                return {
                    "status": "error",
                    "message": f"User {self.request.user} | Failed to download image ({response.status_code}): {image_url}",  # noqa: E501
                    "data": None,
                }

    def _upload_images(self, success_images: list[dict]) -> list:
        images_ids = []
        error_images = []
        # print("success image", success_images)
        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = {}

            for item in success_images:
                future = executor.submit(self.__upload_single_image, item)
                futures[future] = item

            for future in list(futures.keys()):
                item = futures[future]
                result = future.result()

                if result["status"] == "success":
                    images_ids.append(
                        {"column": item["column"], "image_url": item["image_url"], "img_id": result["data"]}
                    )
                else:
                    error_images.append({"column": item["column"], "image_url": item["image_url"], "response": result})

        if len(error_images) == len(success_images):  # All images are error
            return {
                "status": "error",
                "message": "Error when upload images to TikTok",
                "data": error_images,
            }

        return {
            "status": "success",
            "message": None,
            "data": images_ids,
        }

    def _call_create_product(
        self,
        item: dict,
        category_id: str,
        warehouse_id: str,
        is_cod_open: bool,
        package_height: float,
        package_length: float,
        package_weight: float,
        package_width: float,
        images_ids: list,
        description: str,
        skus: list,
        size_chart_id: str,
        images_link_variant_ids:list,
        attributes: list
    ):
        try:
            title = item.get("title", "")
            seller_sku = item.get("sku", "")

            

            # if images_link_variant_ids and  images_link_variant_ids != []:
            #     number_of_colors = len(images_link_variant_ids)
            #     # Duyệt qua từng sku
            #     for index, sku in enumerate(skus):
            #         sales_attributes = sku.get("sales_attributes", [])
                    
            #         # Tính chỉ số màu sắc cho SKU hiện tại
            #         color_index = index % number_of_colors  # Lấy chỉ số màu theo số SKU

            #         # Gán URI cho phần tử đầu tiên trong sales_attributes
            #         if sales_attributes and len(sales_attributes) > 0:
            #             # Kiểm tra và khởi tạo sku_img nếu chưa tồn tại
            #             if "sku_img" not in sales_attributes[0]:
            #                 sales_attributes[0]["sku_img"] = {}
            #             sales_attributes[0]["sku_img"]["uri"] = images_link_variant_ids[color_index]
            if images_link_variant_ids and images_link_variant_ids != []:
                number_of_colors = len(images_link_variant_ids)
                color_uri_mapping = {}  # Tạo một dictionary để lưu trữ URI của từng màu

                # Duyệt qua từng sku
                for index, sku in enumerate(skus):
                    sales_attributes = sku.get("sales_attributes", [])

                    # Tìm thuộc tính "Color" trong sales_attributes
                    color_attribute = next((attr for attr in sales_attributes if attr["attribute_name"] == "Color"), None)
                    
                    if color_attribute:
                        color_value = color_attribute["custom_value"]
                        
                        # Nếu màu chưa có trong mapping, gán URI từ danh sách hình ảnh
                        if color_value not in color_uri_mapping:
                            color_index = len(color_uri_mapping) % number_of_colors
                            color_uri_mapping[color_value] = images_link_variant_ids[color_index]
                        
                        # Gán URI cho thuộc tính "sku_img" của màu đó
                        color_attribute["sku_img"] = {
                            "uri": color_uri_mapping[color_value]
                        }

            
            product_object = objectcreate.ProductCreateMultiObject(
                is_cod_open=is_cod_open,
                package_dimension_unit="metric",
                package_height=package_height,
                package_length=package_length,
                package_weight=package_weight,
                package_width=package_width,
                category_id=category_id,
                warehouse_id=warehouse_id,
                description=description,
                skus=skus,
                size_chart=size_chart_id,
                attributes=attributes,
            )
        except Exception as e:
            message = f"Error occurred while creating product object: {str(e)}"
            logger.error(f"User {self.request.user} | {message}", exc_info=True)
            return {
                "status": "error",
                "message": message,
                "data": None,
            }

        # Call the create product API
        try:
            response = product.createProduct(self.shop.access_token, self.shop.shop_cipher, title, images_ids, product_object, app_key=self.shop.app_key, app_secret=self.shop.app_secret)
        except Exception as e:
            logger.error(
                f"User {self.request.user} | Error when call API create product: {title}",
                exc_info=True,
            )
            return {
                "status": "error",
                "message": f"User {self.request.user} | Error occurred while calling create product API: {str(e)}",
                "data": None,
            }
        else:
            # logger.info(
            #     f"User {self.request.user} | Call create product API for item with title {title}'s response: \
            #     \n{json.dumps(response.json(), indent=4)}\n"
            # )

            response_json: dict = json.loads(response.text)

            if response_json.get("data") is None:
                code = "E003"
                try:
                    message = ErrorCodes.objects.get(code=code).message
                except Exception as e:
                    message = "Error when upload images to TikTok"
                return {
                    "status": "error",
                    "code": code,
                    "message": message,
                    "data": response_json,
                }

            return {
                "status": "success",
                "message": None,
                "data": response_json,
            }


class EditProduct(APIView):
    def put(self, request, shop_id, product_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        product_data = json.loads(body_raw)

        # Tạo một bản sao của product_data để loại bỏ imgBase64
        product_data_without_img = product_data.copy()
        img_base64 = product_data_without_img.pop("imgBase64", [])

        # Tạo một đối tượng ProductObject không chứa imgBase64
        product_object_data = {key: value for key, value in product_data.items() if key != "imgBase64"}
        try:
            print("hello", product_object_data["skus"][0]["stock_infos"])
            product_object = helpers.ProductObject(**product_object_data)

        except Exception as e:
            logger.error(f"User {request.user}: Error when create product object from request body", exc_info=e)
            return JsonResponse({"message": "Error occurred while creating product object"}, status=500)

        try:
            response = product.callEditProduct(access_token, product_object, img_base64, app_key = shop.app_key, app_secret=shop.app_secret)

            return HttpResponse(response, content_type="text/plain", status=200)

        except Exception as e:
            logger.error(f"User {request.user}: Error when edit product with product_id {product_id}", exc_info=e)
            return JsonResponse({"message": "Error occurred while calling edit product API"}, status=400)


"""Category"""


class CategoryRecommend(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")

        product_title_json = json.loads(body_raw)
        data = product_title_json.get("product_name", "")

        response = product.categoryRecommend(access_token, data)
        response_data = {
            "category": json.loads(response.content.decode("utf-8")),
            "message": "Success",
        }
        return JsonResponse(response_data, status=200)


class GlobalCategory(APIView):
    def get(self, request):
        categories = Categories.objects.get(id=1)
        return Response(categories.data, status=status.HTTP_200_OK)


class CategoriesByShopId(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        try:
            response = product.getCategories(access_token=access_token, app_key = shop.app_key, app_secret = shop.app_secret)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get categories from TikTok", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy categories từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if response.status_code == 200:
            json_data = response.json
            categories = json_data.get("data", {}).get("category_list", [])

            data = {"code": 0, "data": {"category_list": categories}}

            return JsonResponse(data, status=status.HTTP_200_OK)

        return HttpResponse(response.content, content_type="application/json", status=response.status_code)


class CategoriesIsLeaf(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token

        try:
            response = product.getCategories(access_token=access_token, app_key = shop.app_key, app_secret = shop.app_secret)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get categories from TikTok", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy categories từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if response.status_code == 200:
            json_data = response.json
            categories = json_data.get("data", {}).get("category_list", [])

            filtered_categories = [category for category in categories if category.get("is_leaf", False)]

            data = {"code": 0, "data": {"category_list": filtered_categories}}

            return JsonResponse(data, status=status.HTTP_200_OK)

        return HttpResponse(response.content, content_type="application/json", status=response.status_code)


"""Brand"""


class GlobalBrand(APIView):
    def get(self, request):
        categories = Brand.objects.get(id=1)
        return Response(categories.data, status=status.HTTP_200_OK)


class GetAllBrands(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        response = product.getBrands(access_token=shop.access_token, app_key=shop.app_key, app_secret=shop.app_secret)

        return HttpResponse(response.content, content_type="application/json", status=response.status_code)


"""Warehouse"""


class WareHouse(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token

        try:
            response = product.getWareHouseList(shop=shop)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get warehouse list from TikTok", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy warehouse list từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return HttpResponse(response.content, content_type="application/json", status=response.status_code)


"""Attribute"""


class Attributes(APIView):
    def get(self, request, shop_id):
        category_id = request.query_params.get("category_id")
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token

        try:
            response = product.getAttributes(access_token=access_token, category_id=category_id, app_key=shop.app_key, app_secret=shop.app_secret)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get attributes from TikTok", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy attributes từ TikTok", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return HttpResponse(response.content, content_type="application/json", status=response.status_code)


class GetProductAttribute(APIView):
    def get(self, request, shop_id, category_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        data = product.callGetAttribute(access_token, category_id, app_key=shop.app_key, app_secret=shop.app_secret)
        return JsonResponse(data, status=200)


"""Image"""


class UploadImage(APIView):
    def post(self, request, shop_id):
        image_data = request.data.get("img_data")
        shop = get_object_or_404(Shop, id=shop_id)

        if image_data:
            try:
                image_base64 = base64.b64encode(image_data.read()).decode("utf-8")

                response = product.callUploadImage(access_token=shop.access_token, img_data=image_base64, app_key=shop.app_key, app_secret=shop.app_secret)

                return HttpResponse(response.content, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"User {request.user}: Error when encode image to base64", exc_info=e)
                return Response(
                    {"status": "error", "message": "Có lỗi xảy ra encode base64 ảnh", "data": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return Response({"status": "error", "message": "Không có dữ liệu ảnh"}, status=status.HTTP_400_BAD_REQUEST)


class uploadImageToTiktok(APIView):
    def post(self, request, shop_id=None):
        if shop_id: 
            store = get_object_or_404(Shop, id=shop_id)
        else: 
            # lấy random 1 store của user đang request
            user_shops = Shop.objects.filter()
            print('user_shops: ', user_shops);
            store_count = user_shops.count()
            if store_count > 0:
                # Lấy một index ngẫu nhiên từ 0 đến tổng số stores - 1
                random_index = random.randint(0, store_count - 1)
                # Lấy store tại index ngẫu nhiên đó
                store = user_shops[random_index]
            else:
                store = None
        
        if not store:
            return JsonResponse({"message": "Không tìm thấy cửa hàng"}, status=404)
        
        image_data = request.data.get("img_data")
        if image_data:
            try:
                image_base64 = image_data

                response = product.callUploadImage(access_token=store.access_token, img_data=image_base64, app_key=store.app_key, app_secret=store.app_secret, return_id=False)
                json_resonse = response.json()
                if json_resonse['code'] == 105002:
                    try:
                        response = token.refreshToken(refresh_token=store.refresh_token, app_key = store.app_key, app_secret = store.app_secret)
                        json_data = response.json()
                        data = json_data.get("data", {})

                        # Lấy ra refresh token mới
                        access_token = data.get("access_token", None)
                        refresh_token = data.get("refresh_token", None)

                        store.access_token = access_token
                        store.refresh_token = refresh_token
                        store.save()

                        try:
                            image_base64 = image_data

                            response = product.callUploadImage(access_token=store.access_token, img_data=image_base64, app_key=store.app_key, app_secret=store.app_secret, return_id=False)
                            print('response: 11111', response);

                            return HttpResponse(response.content, status=status.HTTP_201_CREATED)
                        except Exception as e:
                            logger.error(f"User {request.user}: Error when encode image to base64 2", exc_info=e)
                            return Response(
                                {"status": "error", "message": "Có lỗi xảy ra encode base64 ảnh 2", "data": str(e)},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            )
                    except Exception as e:
                        logger.error(f"User {request.user}: Error when refresh token", exc_info=e)
                        return Response(
                            {"status": "error", "message": "Có lỗi xảy ra encode base64 ảnh", "data": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                return HttpResponse(response.content, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"User {request.user}: Error when encode image to base64", exc_info=e)
        else:
            return Response({"status": "error", "message": "Không có dữ liệu ảnh"}, status=status.HTTP_400_BAD_REQUEST)

class DeleteProduct(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        data = json.loads(body_raw)
        product_ids = data.get("product_ids", [])
        response = product.delete_product(access_token=access_token, product_ids=product_ids, app_key=shop.app_key, app_secret=shop.app_secret)
        response_data = {
            "data": json.loads(response.content.decode("utf-8")),
            "message": "Success",
        }
        return JsonResponse(response_data, status=200)
