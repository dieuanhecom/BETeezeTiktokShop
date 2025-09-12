import json
import logging
import os
import platform
import pytz
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from django.db.models import OuterRef, Subquery

import requests
from django.db.models import Count

from api import setup_logging
from api.utils import constant
from api.utils.google.googleapi import search_file, upload_pdf
from api.utils.pdf.ocr_pdf import process_pdf_to_info
from api.utils.tiktok_base_api import order
from api.views import (
    APIView,
    FileResponse,
    HttpResponse,
    IntegrityError,
    IsAuthenticated,
    JsonResponse,
    PageNumberPagination,
    Q,
    Response,
    get_object_or_404,
    status,
)

from ....models import (
    BuyedPackage,
    DesignSku,
    DesignSkuChangeHistory,
    GroupCustom,
    Package,
    Shop,
    UserGroup,
    ProductPackage
)
from ....serializers import (
    BuyedPackageSeri,
    DesignSkuPutSerializer,
    DesignSkuSerializer,
    GroupCustomSerializer,
    PackageDeactiveSerializer,
    PackageSerializer,
    ProductPackageSerializer,
    PackageStatusUpdateSerializer,
    PackageFulfillmentNameUpdateSerializer
)

logger = logging.getLogger("views.tiktok.order_action")
setup_logging(logger, is_root=False, level=logging.INFO)

"""Orders"""

from .ListOrderAPI import *
from django.db.models import Max

class ListOrder(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)

        response = order.callOrderList(shop)
        content = response.content
        logger.info(f"ListOrder response: {content}")

        return HttpResponse(content, content_type="application/json")


class OrderDetail(APIView):
    def get(self, request, shop_id):
        try:
            # Lấy thông tin phân trang, lọc và sắp xếp từ request
            pagination, filters, sorts = get_pagination(
                request,
                ["create_time", "order_status", "buyer_user_id", "shop_id", "user_id"],
            )
            user = request.user
            shop = get_object_or_404(Shop, id=shop_id)

            # Gọi API lấy danh sách đơn hàng
            responseOrderList = order.callOrderList(shop, cursor="")
            return JsonResponse(responseOrderList.json(), safe=False)
            data = []
            errors = []

            # Kiểm tra nếu không có đơn hàng nào
            if responseOrderList.json()["data"]["total_count"] == 0:
                content = {
                    "status": "success",
                    "meta": {"total_items": 0, "total_pages": 0, "offset": 0, "limit": 0},
                    "data": {"orders": []},
                    "message": "Success",
                    "error": errors,
                }
                return JsonResponse(content, safe=False)

            # Lấy danh sách order_id và xử lý khi có nhiều đơn hàng
            orders = responseOrderList.json()["data"]["orders"]
            orderIds = [order["id"] for order in orders]

            while (
                responseOrderList.json()["data"]["more"]
                and "orders" in responseOrderList.json()["data"]
            ):
                next_cursor = responseOrderList.json()["data"]["next_page_token"]
                responseOrderList = order.callOrderList(
                    shop, cursor=next_cursor
                )
                try:
                    new_orders = responseOrderList.json()["data"]["orders"]
                except KeyError:
                    new_orders = []

                orderIds.extend([order["id"] for order in new_orders])

            # Gọi chi tiết đơn hàng theo từng nhóm 50 đơn hàng
            with ThreadPoolExecutor(max_workers=40) as executor:
                futures = []
                for i in range(0, len(orderIds), 50):
                    chunk_ids = orderIds[i: i + 50]
                    futures.append(
                        executor.submit(
                            order.callOrderDetail,
                            shop,
                            chunk_ids,
                        )
                    )

                # Lấy kết quả từ các futures
                for future in futures:
                    response = future.result()
                    data.extend(response.json()["data"]["orders"])

            # Xử lý sắp xếp và phân trang
            sorts.setdefault("create_time", "desc")
            sorted_orders = data
            limit = pagination.get("limit", 1000)
            offset = pagination.get("offset", 0)
            paginated_orders = sorted_orders[offset * limit: (offset + 50) * limit]

            total_items = len(data)
            total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)

            # Tạo response
            content = {
                "status": "success",
                "meta": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "offset": offset,
                    "limit": limit,
                },
                "data": paginated_orders,
                "error": errors,
            }

            return JsonResponse(content, safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

"""Labels"""


class ShippingLabel(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        data = json.loads(request.body.decode("utf-8"))
        doc_urls = []
        order_ids = data.get("order_ids", [])

        for order_id in order_ids:
            doc_url = order.callGetShippingDocument(
                shop, order_id
            )
            doc_urls.append(doc_url)
            logger.info(f"Call Shipping Label for Order ID {order_id} url: {doc_url}")

        response = {"code": 200, "data": {"doc_urls": doc_urls}}

        return JsonResponse(response, content_type="application/json")


class ShippingService(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token

        body_raw = request.body.decode("utf-8")
        service_info = json.loads(body_raw)

        # Function to call the shipping service and process data
        def get_shipping_service_data(service_info):
            response = order.callGetShippingService(shop, service_info)
            data_json_string = response.content.decode("utf-8")
            data = json.loads(data_json_string)
            data_inner = data.get("data", {})
            shipping_services = data_inner.get("shipping_service_info", [])
            return shipping_services

        # Using ThreadPoolExecutor to run the tasks in parallel
        shipping_services = []
        try:
            with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
                # Submitting the task to executor
                future = executor.submit(get_shipping_service_data, service_info)

                # Getting the result of the future
                shipping_services = future.result()

        except Exception as e:
            # Log the error for debugging purposes
            print(f"Error occurred: {e}")
            # Continue processing even if there's an error (fallback to empty list or default services)
            shipping_services = []

        # Simplify the shipping services data
        simplified_shipping_services = [
            {"id": service.get("id"), "name": service.get("name")}
            for service in shipping_services
        ]

        # Fallback if no services are found or in case of an error
        if not simplified_shipping_services:
            simplified_shipping_services = [
                {"id": "7208502187360519982", "name": "USPS Ground Advantage™"}
            ]

        response_data = {
            "data": simplified_shipping_services,
            "message": "Success",
        }

        return JsonResponse(response_data, status=200)

    def call_get_shipping_service(self, shop, service_info):
        return order.callGetShippingService(shop, service_info)





class CreateLabel(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        body_raw = request.body.decode("utf-8")
        label_datas = json.loads(body_raw)

        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = []
            for label_data in label_datas:
                futures.append(
                    executor.submit(self.call_create_label, shop, label_data)
                )

            datas = []
            for future in futures:
                datas.append(future.result())

        return Response(
            {"data": datas, "message": "Buy label successfully."}, status=201
        )

    def call_create_label(self, shop, label_data):
        respond = order.callCreateLabel(
            shop, label_data
        )
        data = json.loads(respond.content)

        # Check if package_id already exists
        try:
            buyedPkg, created = BuyedPackage.objects.get_or_create(
                package_id=data.get("data", {}).get("package_id") if data.get("data") and data["data"].get("package_id") else None
            )
            # If created is True, it means a new object was created
            if created:
                return json.loads(respond.content)
            else:
                return {"status": 404, "error": "Package is buyed label."}
        except IntegrityError:
            logger.error("Integrity error occurred when creating label", exc_info=True)
            return {"error": "Integrity error occurred"}


class PackageBought(APIView):
    def get(self, request):
        # Retrieve all instances of BuyedPackage
        buyed_packages = BuyedPackage.objects.all()

        # Serialize the queryset
        serializer = BuyedPackageSeri(buyed_packages, many=True)

        # Return serialized data as response
        return Response(serializer.data)


class PDFSearch(APIView):
    def get(self, request):
        PDF_DIRECTORY = (
            constant.PDF_DIRECTORY_WINDOW
            if platform.system() == "Windows"
            else constant.PDF_DIRECTORY_UNIX
        )
        os.makedirs(PDF_DIRECTORY, exist_ok=True)
        query = request.query_params.get("query", "")
        found_files = []

        for filename in os.listdir(PDF_DIRECTORY):
            if filename.endswith(".pdf") and query in filename:
                found_files.append(filename)

        return Response(found_files)


class PDFDownload(APIView):
    def get(self, request):
        PDF_DIRECTORY = (
            constant.PDF_DIRECTORY_WINDOW
            if platform.system() == "Windows"
            else constant.PDF_DIRECTORY_UNIX
        )
        filename = request.query_params.get("filename", "")
        file_path = os.path.join(PDF_DIRECTORY, filename)

        if os.path.exists(file_path):
            return FileResponse(open(file_path, "rb"), as_attachment=True)
        else:
            return Response({"message": "File not found"}, status=404)


"""Packages"""


class AllCombinePackage(APIView):
    # permission_classes =(IsAuthenticated,)

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        try:
            response = order.callPreCombinePackage(shop)

            data_json_string = response.content.decode("utf-8")
            data = json.loads(data_json_string)
            response_data = {
                "code": 0,
                "data": data,
                "message": "Success",
            }
            return JsonResponse(response_data, status=200)
        except Exception as e:
            logger.error("Error when getting all combine package", exc_info=e)
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class ConfirmCombinePackage(APIView):
    # permission_classes = (IsAuthenticated,)

    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        body_raw = request.body.decode("utf-8")
        body_raw_json = json.loads(body_raw)

        response = order.callConFirmCombinePackage(
            access_token=access_token, body_raw_json=body_raw_json, app_key=shop.app_key, app_secret= shop.app_secret
        )
        data_json_string = response.content.decode("utf-8")
        data = json.loads(data_json_string)

        logger.info(f"ConfirmCombinePackage response: {data}")

        response_data = {
            "code": 0,
            "data": data,
            "message": "Success",
        }
        return JsonResponse(response_data, status=200)


class SearchPackage(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        respond = order.callSearchPackage(access_token, shop.app_key, shop.app_secret)
        data_json_string = respond.content.decode("utf-8")
        data = json.loads(data_json_string)

        response_data = {
            "data": data,
            "message": "Success",
        }

        return JsonResponse(response_data, status=200)


class PackageDetail(APIView):
    def post(self, request, shop_id):
        package_ids = json.loads(request.body.decode("utf-8"))
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        data_main = []

        # Sử dụng ThreadPoolExecutor để thực hiện các cuộc gọi API đa luồng
        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = []
            for package_id in package_ids:
                futures.append(
                    executor.submit(
                        order.callCreatePackages, access_token, package_id, shop.app_key, shop.app_secret
                    )
                )

            # Thu thập kết quả từ các future và thêm vào danh sách data_main
            for future in futures:
                respond = future.result()
                data_json_string = respond.content.decode("utf-8")
                data = json.loads(data_json_string)
                print("11111111111111111111111111", data)
                if data.get("data") and data["data"].get("package_id"):
                    data["data"]["package_id"] = str(data["data"]["package_id"])
                data_main.append(data)

        response_data = {
            "data": data_main,
            "message": "Success",
        }
        return JsonResponse(response_data, status=200)


"""Design Skus"""


class CustomPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"

class DesignSkuListCreateAPIViewPage(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_user_group(self, user):
        user_group = UserGroup.objects.filter(user=user)
        if user_group.exists():
            return user_group[0].group_custom
        return None

    def get(self, request):
        group_custom = self.get_user_group(request.user)
        if group_custom:
            designskus = DesignSku.objects.filter(department=group_custom).order_by(
                "-id"
            )
            paginator = self.pagination_class()
            result_page = paginator.paginate_queryset(designskus, request)
            serializer = DesignSkuSerializer(result_page, many=True)
            return paginator.get_paginated_response(serializer.data)
        return Response(
            "Người dùng không thuộc bất kỳ nhóm nào.", status=status.HTTP_404_NOT_FOUND
        )
    
class DesignSkuListCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get_user_group(self, user):
        user_group = UserGroup.objects.filter(user=user)
        if user_group.exists():
            return user_group[0].group_custom
        return None

    def get(self, request):
        group_custom = self.get_user_group(request.user)
        if group_custom:
            # Lấy tất cả các kết quả mà không cần phân trang
            designskus = DesignSku.objects.filter(department=group_custom).order_by("-id")
            serializer = DesignSkuSerializer(designskus, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(
            "Người dùng không thuộc bất kỳ nhóm nào.", status=status.HTTP_404_NOT_FOUND
        )

    def post(self, request):
        group_custom = self.get_user_group(request.user)
        user = request.user
        if group_custom and user:
            data = request.data
            for item in data:
                item["department"] = group_custom.pk
                item["user"] = user.id
                item["created_by"] = user.id
            serializer = DesignSkuSerializer(data=data, many=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            "User does not belong to any group.", status=status.HTTP_404_NOT_FOUND
        )


class DesignSkuDetailAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return DesignSku.objects.get(pk=pk)
        except DesignSku.DoesNotExist:
            return None

    def get(self, request, pk):
        designsku = self.get_object(pk)
        if designsku:
            serializer = DesignSkuSerializer(designsku)
            return Response(serializer.data)
        return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        designsku_data = request.data
        designsku = self.get_object(pk)

        if designsku:
            old_data = DesignSkuPutSerializer(designsku).data
            serializer = DesignSkuPutSerializer(designsku, data=designsku_data)
            if serializer.is_valid():
                serializer.save()

                user = request.user if request.user.is_authenticated else None
                changed_at = datetime.now()

                DesignSkuChangeHistory.objects.create(
                    design_sku=designsku,
                    user=user,
                    change_data=old_data,
                    changed_at=changed_at,
                )
                return Response(
                    "DesignSku updated successfully.", status=status.HTTP_200_OK
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(
                f"DesignSku with ID {pk} does not exist.",
                status=status.HTTP_404_NOT_FOUND,
            )

    def delete(self, request, pk):
        designsku = self.get_object(pk)
        if designsku:
            designsku.delete()
            return Response(
                {"message": "DesignSku deleted successfully."},
                status=status.HTTP_204_NO_CONTENT,
            )
        return Response(
            {"error": f"DesignSku with ID {pk} does not exist."},
            status=status.HTTP_404_NOT_FOUND,
        )


class DesignSkuBySkuId(APIView):
    pagination_class = CustomPagination
    def get(self, request, sku_id):
        user = request.user
        print(user.username)  # In ra tên người dùng để kiểm tra
        user_group = UserGroup.objects.get(user=user)
        group_custom = user_group.group_custom
        design_skus = DesignSku.objects.filter(department=group_custom, sku_id=sku_id).order_by("-id")
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(design_skus, request)  # Changed from [design_skus] to design_skus
        serializer = DesignSkuSerializer(result_page, many=True)
        # design_skus = DesignSku.objects.get(sku_id=sku_id)
        # serializer = DesignSkuSerializer(design_skus)
        return paginator.get_paginated_response(serializer.data)


class DesignSkuDepartment(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get(self, request, group_id):
        user = request.user
        designskus = DesignSku.objects.filter(user_id=user.id, department=group_id).order_by("-id")
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(designskus, request)
        serializer = DesignSkuSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)

class DesignSkuAllDepartment(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def get(self, request):
        user = request.user
        designskus = DesignSku.objects.all()
        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(designskus, request)
        serializer = DesignSkuSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class DesignSkuSearch(APIView):
    permission_classes = (IsAuthenticated,)
    pagination_class = CustomPagination

    def post(self, request):
        data = json.loads(request.body.decode("utf-8"))
        search_query = data.get("search_query", None)
        group_id = data.get("group_id", None)

        designskus = DesignSku.objects.all()

        if group_id:
            try:
                group_id = int(group_id)
            except ValueError:
                return Response(
                    "Invalid group_id format", status=status.HTTP_400_BAD_REQUEST
                )
            designskus = designskus.filter(department_id=group_id)

        if search_query:
            designskus = designskus.filter(
                Q(sku_id__icontains=search_query)
                | Q(product_name__icontains=search_query)
                | Q(variation__icontains=search_query)
            )

        paginator = self.pagination_class()
        result_page = paginator.paginate_queryset(designskus, request)
        serializer = DesignSkuSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


class GroupCustomListAPIView(APIView):
    def get(self, request):
        group_customs = GroupCustom.objects.all().order_by("id")
        serializer = GroupCustomSerializer(group_customs, many=True)
        return Response(serializer.data)

class ShippingDoc(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        data = json.loads(request.body.decode("utf-8"))
        doc_urls = []
        package_ids = data.get("package_ids", [])
        max_retries = 10  # Số lần thử lại

        # Hàm thực hiện gọi API với retry
        def call_with_retry(package_id):
            retries = 0
            while retries < max_retries:
                try:
                    # Thực hiện gọi API
                    return order.callGetShippingDoc(
                        shop=shop,
                        package_id=package_id,
                    )
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        # Nếu đã thử đủ số lần, ghi log lỗi và trả về None
                        print(f"Failed to fetch doc for package_id {package_id}: {e}")
                        return None
                    # sleep(2)  # Thời gian chờ giữa các lần thử lại

        # Sử dụng ThreadPoolExecutor để thực hiện các cuộc gọi API đa luồng
        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = [
                executor.submit(call_with_retry, package_id) for package_id in package_ids
            ]

            # Thu thập kết quả từ các future và thêm vào danh sách doc_urls
            for future in futures:
                doc_url = future.result()
                if doc_url:  # Chỉ thêm URL nếu thành công
                    doc_urls.append(doc_url)

        # Tạo phản hồi JSON chứa danh sách các URL của shipping doc
        response_data = {"code": 0, "data": {"doc_urls": doc_urls}}
        return JsonResponse(response_data)


class UploadDriver(APIView):
    def download_and_upload(self, order_document):
        order_id = order_document.get("package_id")
        doc_url = order_document.get("doc_url")

        if order_id and doc_url:
            try:
                # Download the file from doc_url
                response = requests.get(doc_url)
                if response.status_code == 200:
                    # Save the file with order_id as the name
                    file_name = f"{order_id}.pdf"
                    file_path = os.path.join(constant.PDF_DIRECTORY_WINDOW, file_name)
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                        print(f"File saved: {file_path}")

            except Exception as e:
                print(f"Error downloading/uploading: {str(e)}")

    def post(self, request):
        try:
            data_post = json.loads(request.body.decode("utf-8"))
            order_documents = data_post.get("order_documents", [])

            with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
                # Sử dụng map để gọi download_and_upload cho mỗi order_document
                executor.map(self.download_and_upload, order_documents)

            return JsonResponse({"status": "success"}, status=201)

        except Exception as e:
            # Log the error
            print(f"Error in UploadDriver: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class ToShipOrderAPI(APIView):
    def get_order_detail(self, order_document) -> dict:
        order_list = order_document.get("order_list")
        doc_url = order_document.get("label")
        package_id = order_document.get("package_id")

        # Tải file PDF từ doc_url
        try:
            response = requests.get(doc_url)
        except Exception as e:
            logger.error("Error when downloading PDF file", exc_info=e)
            error_response = {
                "status": "error",
                "message": f"Có lỗi xảy ra khi tải file PDF label: {str(e)}",
                "data": None,
            }
            return error_response

        if response.status_code == 200:
            file_name = f"{package_id}.pdf"

            platform_name = platform.system()
            parent_dir = (
                constant.PDF_DIRECTORY_WINDOW
                if platform_name == "Windows"
                else constant.PDF_DIRECTORY_UNIX
            )
            os.makedirs(parent_dir, exist_ok=True)
            file_path = os.path.join(parent_dir, file_name)

            with open(file_path, "wb") as file:
                file.write(response.content)

            order_ids = (
                [item.get("id") for item in order_list] if order_list else []
            )

            # Call OrderDetail API
            try:
                order_details: dict = order.callOrderDetail(
                    shop=self.shop, orderIds=order_ids
                ).json()
            except Exception as e:
                logger.error("Error when calling OrderDetail API", exc_info=e)
                error_response = {
                    "status": "error",
                    "message": "Có lỗi xảy ra khi gọi API OrderDetail",
                    "data": None,
                }
                return error_response

            logger.info(f"OrderDetail response: {order_details}")

            # Check the response from TikTok API
            if order_details.get("data") is None:
                error_response = {
                    "status": "error",
                    "message": f'Có lỗi xảy ra khi gọi API OrderDetail: {order_details.get("message")}',
                    "data": None,
                }
                return error_response
            else:
                order_details["ocr_result"] = process_pdf_to_info(file_path)
                success_response = {
                    "status": "success",
                    "message": "Thành công",
                    "data": order_details,
                }

                return success_response
        else:
            error_response = {
                "status": "error",
                "message": "Có lỗi xảy ra khi tải file PDF",
                "data": response.text,
            }
            return error_response

    def post(self, request, shop_id):
        data = []
        self.shop = get_object_or_404(Shop, id=shop_id)
        self.access_token = self.shop.access_token
        data_post = json.loads(request.body.decode("utf-8"))
        order_documents = data_post.get("order_documents", [])

        with ThreadPoolExecutor(max_workers=constant.MAX_WORKER) as executor:
            futures = []
            for order_document in order_documents:
                futures.append(executor.submit(self.get_order_detail, order_document))

            for future in futures:
                result = future.result()
                # logger.info(f'User {request.user}: Order detail and OCR label result: {result}')
                data.append(result)

        return JsonResponse(data, status=200, safe=False)


class PackageCreateForFlash(APIView):
    def post(self, request, shop_id, format=None):
        request.data["fulfillment_name"] = "FlashShip"
        if shop_id == 0:
            request.data["shop"] = None
        else:
            request.data["shop"] = shop_id
        request.data["seller"] = request.user.username  # Lưu ID của user thay vì object User
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PackageCreateForPrint(APIView):
    def post(self, request, shop_id, format=None):
        request.data["fulfillment_name"] = "PrintCare"
        if shop_id == 0:
            request.data["shop"] = None
        else:
            request.data["shop"] = shop_id
        request.data["seller"] = request.user.username  # Lưu ID của user thay vì object User
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PackageCreateForCkf(APIView):
    def post(self, request, shop_id, format=None):
        request.data["fulfillment_name"] = "Ckf"
        if shop_id == 0:
            request.data["shop"] = None
        else:
            request.data["shop"] = shop_id
        request.data["seller"] = request.user.username  # Lưu ID của user thay vì object User
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class PackageCreateForDropShip(APIView):
    def post(self, request, shop_id, format=None):
        request.data["fulfillment_name"] = "DropShip"
        if shop_id == 0:
            request.data["shop"] = None
        else:
            request.data["shop"] = shop_id
        request.data["seller"] = request.user.username  # Lưu ID của user thay vì object User
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

class PackageCreateForTeeClub(APIView):
    def post(self, request, shop_id, format=None):
        request.data["fulfillment_name"] = "TeeClub"
        if shop_id == 0:
            request.data["shop"] = None
        else:
            request.data["shop"] = shop_id
        request.data["seller"] = request.user.username  # Lưu ID của user thay vì object User
        serializer = PackageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PackageListByShop(APIView):
    def get(self, request, shop_id, format=None):
        packages = Package.objects.filter(shop_id=shop_id)

        # Kiểm tra nếu không có gói hàng nào được tìm thấy
        if not packages:
            return Response([], status=status.HTTP_200_OK)  # Trả về một mảng JSON rỗng

        serializer = PackageSerializer(packages, many=True)
        return Response(serializer.data)


class DeactivePack(APIView):
    # permission_classes = (IsAuthenticated,)

    def put(self, request, pack_id):
        package = get_object_or_404(Package, pack_id=pack_id)
        serializer = PackageDeactiveSerializer(package, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)


class UploaddriveAndSearchPrintCare(APIView):
    def post(self, request):
        PDF_DIRECTORY = (
            constant.PDF_DIRECTORY_WINDOW
            if platform.system() == "Windows"
            else constant.PDF_DIRECTORY_UNIX
        )
        os.makedirs(PDF_DIRECTORY, exist_ok=True)
        
        data = json.loads(request.body.decode("utf-8"))
        queries = data.get("pdf_name")

        search_results = []
        found_files = []

        # Tìm kiếm các file PDF có trong queries
        for filename in os.listdir(PDF_DIRECTORY):
            if filename.endswith(".pdf") and filename in queries:
                found_files.append(filename)

        def upload_and_search(file_name):
            file_path = os.path.join(PDF_DIRECTORY, file_name)
            print("file path", file_path)
            
            # Upload to Google Drive
            file_id = upload_pdf(file_path, file_name)
            print(f"Uploaded '{file_name}' to Google Drive with ID: {file_id}")
            
            # Search in Google Drive
            search_result = search_file(file_name)
            return search_result

        # Sử dụng ThreadPoolExecutor để upload và search song song
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Submit all tasks to the executor
            future_to_file = {executor.submit(upload_and_search, file): file for file in found_files}
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                search_results.append(future.result())

        return Response(search_results)


class CancelOrder(APIView):
    def post(self, request, shop_id):
        try:
            shop = get_object_or_404(Shop, id=shop_id)
            access_token = shop.access_token
            data = json.loads(request.body.decode("utf-8"))
            cancel_reason_key = data.get("cancel_reason_key", "")
            order_id = data.get("order_id", "")
            response = order.cancel_order(
                access_token=access_token,
                order_id=order_id,
                cancel_reason_key=cancel_reason_key,
                app_key=shop.app_key,
                app_secret=shop.app_secret
            )
            response = json.loads(response.text)
            return JsonResponse(response, safe=False)
        except Exception as e:
            error_message = str(e)
            return JsonResponse({"error": error_message}, status=500)
        
class PackageFilter(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageSerializer

    # Hàm chuyển đổi unix time thành datetime
    def convert_unix_to_datetime(self, unix_time):
        try:
            local_tz = pytz.timezone("Asia/Ho_Chi_Minh")  # Đổi sang múi giờ của bạn
            utc_time = datetime.fromtimestamp(int(unix_time), pytz.utc)
            return utc_time.astimezone(local_tz)
        except ValueError:
            raise ValueError("Invalid unix time format")

    def get(self, request):
        try:
            pagination, filters, sorts = get_pagination(
                request,
                ["create_time", "shop_id", "fulfillment_name"],
            )
            user = request.user
            errors = []

            # Lấy danh sách các shop theo người dùng
            shops, _ = get_shop_list(user, filters)

            # Kiểm tra nếu người dùng có truyền thêm shop_id vào query parameters
            shop_ids_from_request = request.GET.get("shop_id", "")

            # Kiểm tra nếu shop_ids_from_request không rỗng, tách và chuyển thành số nguyên
            if shop_ids_from_request:
                try:
                    # print("da vao if")
                    shop_id_value = [int(shop_id) for shop_id in shop_ids_from_request.split(',') if shop_id.strip().isdigit()]
                except ValueError:
                    return JsonResponse({"error": "Invalid shop_id format, must be integers."}, status=400)
            else:
                # print("da vao else")
                shop_id_value = [shop.id for shop in shops]

            # Lấy fulfillment_name từ request dưới dạng mảng
            fulfillment_names = request.GET.getlist("fulfillment_name")
            status_names = request.GET.getlist("status_name")
            # Xử lý bộ lọc create_time
            create_time_gte = request.GET.get("create_time[$gte]")
            create_time_lt = request.GET.get("create_time[$lt]")
            supify_create_time_gte = request.GET.get("supify_create_time[$gte]")
            supify_create_time_lt = request.GET.get("supify_create_time[$lt]")
            # now = datetime.now(pytz.utc)
            # default_create_time_ge = (now - timedelta(days=3)).isoformat()
            # default_create_time_lt = now.isoformat()

            # package_filters = {
            #     "created_at__gte": filters.get("create_time", {}).get("$gte", default_create_time_ge),
            #     "created_at__lt": filters.get("create_time", {}).get("$lt", default_create_time_lt),
            # }
            package_filters = {}

            if create_time_gte:
                try:
                    # print("Da vao")
                    package_filters["created_at__gte"] = self.convert_unix_to_datetime(create_time_gte).isoformat()
                except ValueError:
                    return JsonResponse({"error": "Invalid format for create_time[$gte]. Must be a valid unix time."}, status=400)

            if create_time_lt:
                try:
                    package_filters["created_at__lt"] = self.convert_unix_to_datetime(create_time_lt).isoformat()
                except ValueError:
                    return JsonResponse({"error": "Invalid format for create_time[$lt]. Must be a valid unix time."}, status=400)
            if supify_create_time_gte:
                try:
                    package_filters["supify_create_time__gte"] = self.convert_unix_to_datetime(supify_create_time_gte)
                except ValueError:
                    return JsonResponse({"error": "Invalid supify_create_time[$gte]. Must be a valid UNIX timestamp."}, status=400)

            if supify_create_time_lt:
                try:
                    package_filters["supify_create_time__lt"] = self.convert_unix_to_datetime(supify_create_time_lt)
                except ValueError:
                    return JsonResponse({"error": "Invalid supify_create_time[$lt]. Must be a valid UNIX timestamp."}, status=400)

          
            # Nếu có shop_id_value, thêm vào bộ lọc
            if shop_id_value:
                package_filters["shop__id__in"] = tuple(shop_id_value)

            # Nếu có fulfillment_names, thêm bộ lọc dùng __in
            if fulfillment_names:
                package_filters["fulfillment_name__in"] = fulfillment_names
            if status_names:
                package_filters["status__in"] = status_names
            product_name = request.GET.get("product_name")
            order_id = request.GET.get("order_id")
            if product_name:
                package_filters["products__product_name__icontains"] = product_name
            if order_id:
                package_filters["order_id__icontains"] = order_id
            print("filter", package_filters)

            # Truy vấn các package với bộ lọc áp dụng
            packages = Package.objects.filter(**package_filters)
            # packages = packages.distinct('pack_id')
            subquery = Package.objects.filter(pack_id=OuterRef('pack_id')).order_by('created_at').values('id')[:1]
            packages = packages.filter(id__in=Subquery(subquery))

            # Áp dụng sắp xếp
            sorts.setdefault("created_at", "desc")
            sort_criteria = list(sorts.items())
            for field, order in reversed(sort_criteria):
                packages = packages.order_by(f"{'-' if order == 'desc' else ''}{field}")

            # Phân trang
            limit = pagination.get("limit", 10)
            offset = pagination.get("offset", 0)
            paginated_packages = packages[offset * limit : (offset + 1) * limit]

            # Serialize kết quả
            serializer = self.serializer_class(paginated_packages, many=True)

            # Tạo metadata cho phản hồi
            total_items = packages.count()
            total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)

            custom_response = {
                "status": "success",
                "meta": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "offset": offset,
                    "limit": limit,
                },
                "data": serializer.data,
                "error": errors
            }

            return JsonResponse(custom_response)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        

class ProductPackageUpdateView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return ProductPackage.objects.get(pk=pk)
        except ProductPackage.DoesNotExist:
            return None

    def put(self, request, pk):
        # Lấy đối tượng ProductPackage
        product_package = self.get_object(pk)
        data = request.data
        print("data body", data)
        if product_package is None:
            return Response({"error": "ProductPackage not found."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize lại dữ liệu từ request
        serializer = ProductPackageSerializer(product_package, data=request.data["product"], partial=True)

        if serializer.is_valid():
            # Lưu lại các thay đổi vào cơ sở dữ liệu
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        # PATCH có thể chỉ sửa một số trường, do đó logic tương tự PUT
        return self.put(request, pk)

class UpdatePackageStatusView(APIView):
    """
    View để cập nhật trạng thái của Package.
    """
    def put(self, request, pk):
        # Lấy package theo id
        package = get_object_or_404(Package, pk=pk)
        request.data["update_by"] = request.user.customuser.id
        # Deserialize dữ liệu
        serializer = PackageStatusUpdateSerializer(package, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Cập nhật trạng thái thành công.", "data": serializer.data}, status=status.HTTP_200_OK)
        
        return Response({"message": "Dữ liệu không hợp lệ.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class UpdateFulfillmentNameView(APIView):
    """
    View để cập nhật fulfillment_name của Package.
    """
    def put(self, request, pk):
        # Lấy package theo id
        package = get_object_or_404(Package, pk=pk)
        request.data["update_by"] = request.user.customuser.id
        request.data["supify_create_time"] = datetime.now()
        print("resssssssssssssssssssa",request.data["supify_create_time"] )
        # Deserialize dữ liệu
        serializer = PackageFulfillmentNameUpdateSerializer(package, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Cập nhật fulfillment_name thành công.", "data": serializer.data}, status=status.HTTP_200_OK)
        
        return Response({"message": "Dữ liệu không hợp lệ.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class GetNumbersortMax(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = PackageSerializer

    def get(self, request):
        try:
            # Lấy múi giờ Asia/Ho_Chi_Minh
            local_tz = pytz.timezone("Asia/Ho_Chi_Minh")
            today_start = datetime.now(local_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now(local_tz).replace(hour=23, minute=59, second=59, microsecond=999999)

            # Lọc các package có fulfillment_name='Teelover' và supify_create_time trong ngày
            packages = Package.objects.filter(
                fulfillment_name="Teelover",
                supify_create_time__gte=today_start,
                supify_create_time__lte=today_end
            )

            # Lấy tất cả các number_sort
            number_sort_values = packages.values_list('number_sort', flat=True)

            # Tìm giá trị lớn nhất
            max_number_sort = number_sort_values.aggregate(Max('number_sort'))['number_sort__max']

            custom_response = {
                "status": "success",
                "data": {
                    "all_number_sort": list(number_sort_values),
                    "max_number_sort": max_number_sort
                }
            }
            return JsonResponse(custom_response)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class CsvFulfillmentSkuValidationAPI(APIView):
    """
    API endpoint for CSV fulfillment SKU validation
    Validates multiple SKU IDs and returns existing designs or missing status
    """
    permission_classes = (IsAuthenticated,)

    def get_user_group(self, user):
        user_group = UserGroup.objects.filter(user=user)
        if user_group.exists():
            return user_group[0].group_custom
        return None

    def post(self, request):
        """
        Validate multiple SKU IDs
        Expected input: {
            "sku_ids": ["sku1", "sku2", "sku3", ...]
        }
        Output: {
            "results": [
                {
                    "sku_id": "sku1",
                    "exists": true,
                    "design": { design_data }
                },
                {
                    "sku_id": "sku2", 
                    "exists": false,
                    "design": null
                }
            ]
        }
        """
        try:
            group_custom = self.get_user_group(request.user)
            if not group_custom:
                return Response(
                    {"error": "User does not belong to any group."}, 
                    status=status.HTTP_404_NOT_FOUND
                )

            # Enhanced request data validation
            try:
                data = json.loads(request.body.decode("utf-8"))
            except json.JSONDecodeError as e:
                return Response(
                    {"error": f"Invalid JSON format: {str(e)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            sku_ids = data.get("sku_ids", [])
            
            if not sku_ids:
                return Response(
                    {"error": "No SKU IDs provided"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(sku_ids, list):
                return Response(
                    {"error": "SKU IDs must be provided as a list"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Limit the number of SKUs that can be validated at once
            max_skus = 1000
            if len(sku_ids) > max_skus:
                return Response(
                    {"error": f"Too many SKU IDs. Maximum allowed: {max_skus}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = []
            
            for sku_id in sku_ids:
                try:
                    # Check if design exists for this SKU ID in user's group
                    design_sku = DesignSku.objects.filter(
                        department=group_custom, 
                        sku_id=sku_id
                    ).first()
                    
                    if design_sku:
                        serializer = DesignSkuSerializer(design_sku)
                        results.append({
                            "sku_id": sku_id,
                            "exists": True,
                            "design": serializer.data
                        })
                    else:
                        results.append({
                            "sku_id": sku_id,
                            "exists": False,
                            "design": None
                        })
                        
                except Exception as e:
                    logger.error(f"Error validating SKU {sku_id}", exc_info=e)
                    results.append({
                        "sku_id": sku_id,
                        "exists": False,
                        "design": None,
                        "error": str(e)
                    })

            return Response({"results": results}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error("Error in CsvFulfillmentSkuValidationAPI", exc_info=e)
            return Response(
                {"error": f"Server error: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CsvFulfillmentPdfOcrAPI(APIView):
    """
    API endpoint for CSV fulfillment workflow
    Processes PDF file with multiple labels and extracts OCR information
    Clone and enhanced version of ToShipOrderAPI for CSV workflow
    """
    permission_classes = (IsAuthenticated,)

    def process_pdf_with_ocr(self, pdf_base64_data, temp_package_id) -> dict:
        """
        Process a single PDF (which may contain multiple labels) with OCR
        Enhanced version of get_order_detail method
        """
        try:
            # Decode base64 PDF data
            import base64
            from PyPDF2 import PdfReader, PdfWriter
            import io
            
            pdf_data = base64.b64decode(pdf_base64_data.split('base64,')[1])
            
            # Save to temporary file for initial processing
            temp_file_name = f"temp_{temp_package_id}.pdf"
            platform_name = platform.system()
            parent_dir = (
                constant.PDF_DIRECTORY_WINDOW
                if platform_name == "Windows"
                else constant.PDF_DIRECTORY_UNIX
            )
            os.makedirs(parent_dir, exist_ok=True)
            temp_file_path = os.path.join(parent_dir, temp_file_name)

            with open(temp_file_path, "wb") as file:
                file.write(pdf_data)

            # Process PDF with OCR to extract labels
            ocr_result = process_pdf_to_info(temp_file_path)
            
            # Initialize PDF reader
            pdf_reader = PdfReader(io.BytesIO(pdf_data))
            
            if "pages" in ocr_result:
                # Multi-page PDF handling
                results = []
                for page_data in ocr_result.get("pages", []):
                    if page_data.get("status") == "success":
                        # Get tracking ID for this page
                        tracking_id = page_data.get("data", {}).get("tracking_id")
                        page_number = page_data.get("page_number", 1) - 1  # Convert to 0-based index
                        
                        if tracking_id and page_number < len(pdf_reader.pages):
                            # Create single page PDF
                            pdf_writer = PdfWriter()
                            pdf_writer.add_page(pdf_reader.pages[page_number])
                            
                            # Save page as separate PDF with tracking ID name
                            final_file_name = f"{tracking_id}.pdf"
                            final_file_path = os.path.join(parent_dir, final_file_name)
                            
                            # Remove old file if exists
                            if os.path.exists(final_file_path):
                                os.remove(final_file_path)
                                
                            # Save new file
                            with open(final_file_path, "wb") as output_file:
                                pdf_writer.write(output_file)
                        
                        results.append({
                            "status": "success",
                            "message": f"Page {page_data.get('page_number', '?')} processed successfully",
                            "data": {
                                "package_id": f"{temp_package_id}_page_{page_data.get('page_number', '?')}",
                                "ocr_result": page_data,
                                "order_list": []
                            }
                        })
                    else:
                        results.append({
                            "status": "error",
                            "message": page_data.get("message", f"Failed to process page {page_data.get('page_number', '?')}"),
                            "data": None
                        })
                
                # Remove temporary file
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
                    
                # Return summary with all page results
                return {
                    "status": ocr_result.get("status", "success"),
                    "message": ocr_result.get("message", "Multi-page PDF processed"),
                    "total_pages": ocr_result.get("total_pages", len(results)),
                    "successful_pages": ocr_result.get("successful_pages", 0),
                    "results": results
                }
            else:
                # Single page PDF handling
                if ocr_result.get("status") == "success":
                    tracking_id = ocr_result.get("data", {}).get("tracking_id")
                    if tracking_id:
                        final_file_name = f"{tracking_id}.pdf"
                        final_file_path = os.path.join(parent_dir, final_file_name)
                        
                        # Remove old file if exists
                        if os.path.exists(final_file_path):
                            os.remove(final_file_path)
                            
                        # Save PDF with tracking ID name
                        with open(final_file_path, "wb") as file:
                            file.write(pdf_data)
                    
                    # Remove temporary file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        
                    return {
                        "status": "success",
                        "message": "PDF processed successfully",
                        "data": {
                            "package_id": temp_package_id,
                            "ocr_result": ocr_result,
                            "order_list": []
                        }
                    }
                else:
                    # Remove temporary file
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                        
                    return {
                        "status": "error",
                        "message": ocr_result.get("message", "Failed to process PDF"),
                        "data": None
                    }

        except Exception as e:
            logger.error("Error processing PDF with OCR", exc_info=e)
            # Clean up temporary file if exists
            if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return {
                "status": "error",
                "message": f"Error processing PDF: {str(e)}",
                "data": None
            }

    def post(self, request, shop_id=None):
        """
        Process PDF files for CSV fulfillment workflow
        Expected input: {
            "pdf_documents": [
                {
                    "temp_id": "temp_1234567890",
                    "pdf_data": "data:application/pdf;base64,..."
                }
            ]
        }
        Note: shop_id is optional for CSV fulfillment workflow
        """
        try:
            data_post = json.loads(request.body.decode("utf-8"))
            pdf_documents = data_post.get("pdf_documents", [])
            
            if not pdf_documents:
                return JsonResponse([{
                    "status": "error",
                    "message": "No PDF documents provided",
                    "data": None
                }], status=400, safe=False)

            results = []
            
            # Process each PDF document
            for pdf_doc in pdf_documents:
                temp_id = pdf_doc.get("temp_id", f"temp_{int(datetime.now().timestamp())}")
                pdf_data = pdf_doc.get("pdf_data", "")
                
                if not pdf_data:
                    results.append({
                        "status": "error",
                        "message": "PDF data is empty",
                        "data": None
                    })
                    continue
                
                # Process PDF with OCR
                result = self.process_pdf_with_ocr(pdf_data, temp_id)
                results.append(result)

            return JsonResponse(results, status=200, safe=False)

        except Exception as e:
            logger.error("Error in CsvFulfillmentPdfOcrAPI", exc_info=e)
            return JsonResponse([{
                "status": "error",
                "message": f"Server error: {str(e)}",
                "data": None
            }], status=500, safe=False)