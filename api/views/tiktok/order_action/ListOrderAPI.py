import concurrent
import json
from django.contrib.auth.models import User
from django.http import JsonResponse

from api.models import Shop, UserGroup, UserShop,Package
from api.utils.constants.order import order_status
from api.utils.pagination import get_pagination
from api.views import APIView, Response, get_object_or_404
from api.utils.tiktok_base_api import order
from datetime import datetime, timedelta
import pytz
from concurrent.futures import ThreadPoolExecutor
from api.utils.tiktok_base_api.order import update_tracking_infor
from rest_framework.response import Response
from rest_framework import status
from api.serializers import  PackageSerializer
from rest_framework.permissions import IsAuthenticated as IsAuthenticated


def split_into_chunks(lst, chunk_size):
    for i in range(0, len(lst), chunk_size):
        yield lst[i : i + chunk_size]


def fetch_orders_for_shop(shop, filters, user_ids, errors):
    # Get all user_shops for the shop
    user_shops = UserShop.objects.filter(shop_id=shop.id)

    # Check each user_shop
    for user_shop in user_shops:
        user = User.objects.filter(id=user_shop.user_id).first()
        if user and user.id in user_ids:
            return order.req_get_order_list_new(
                shop=shop,
                user=user,
                create_time_ge=filters["create_time_ge"],
                create_time_lt=filters["create_time_lt"],
                order_status=filters["order_status"],
                buyer_user_id=filters["buyer_user_id"],
                errors=errors,
                app_key=shop.app_key,
                app_secret=shop.app_secret
            )

    return []


def sort_orders(all_orders, sorts):
    sort_criteria = list(sorts.items())
    for field, order in reversed(sort_criteria):
        all_orders.sort(key=lambda x: x[field], reverse=(order == "desc"))
    return all_orders


def get_shop_list(user, filters):
    shop_id_value = filters.get("shop_id", {}).get("$in", "")
    shop_id_tuple = (
        tuple(set(int(id.strip()) for id in shop_id_value.split(",")))
        if shop_id_value
        else ()
    )

    user_id_value = filters.get("user_id", {}).get("$in", "")
    user_id_tuple = (
        tuple(set(int(id.strip()) for id in user_id_value.split(",")))
        if user_id_value
        else ()
    )
    user_group = get_object_or_404(UserGroup, user=user)
    if user_group.role != 1:
        user_shops = UserShop.objects.filter(user=user)
        user_shops = user_shops.filter(shop__is_active=True)
        shop_ids = (
            [
                user_shop.shop_id
                for user_shop in user_shops
                if user_shop.shop_id in shop_id_tuple
            ]
            if len(shop_id_tuple) > 0
            else [user_shop.shop_id for user_shop in user_shops]
        )
        shops = Shop.objects.filter(id__in=shop_ids)
        user_ids = tuple([user.id])
    else:
        users_in_group = user_group.group_custom.usergroup_set.values_list(
            "user", flat=True
        )
        shops = (
            Shop.objects.filter(
                usershop__user__in=users_in_group,
                is_active=True,
                id__in=shop_id_tuple,
            ).distinct()
            if len(shop_id_tuple) > 0
            else Shop.objects.filter(
                usershop__user__in=users_in_group, is_active=True
            ).distinct()
        )
        # print("shops", shops)
        user_ids = (
            user_id_tuple
            if len(user_id_tuple) > 0
            else tuple(User.objects.values_list("id", flat=True))
        )
    return shops, user_ids


def get_all_order(user, filters, errors):
    shops, user_ids = get_shop_list(user, filters)
    now = datetime.now(pytz.utc)
    default_create_time_ge = int((now - timedelta(days=3)).timestamp())
    default_create_time_lt = int(now.timestamp())

    order_status_value = filters.get("order_status", {}).get("$in", "")
    order_status_tuple = (
        tuple(set(order_status_value.split(",")))
        if order_status_value
        else (
            order_status["AWAITING_SHIPMENT"],
            order_status["AWAITING_COLLECTION"],
        )
    )

    filters = {
        "create_time_ge": int(
            filters.get("create_time", {}).get("$gte", default_create_time_ge)
        ),
        "create_time_lt": int(
            filters.get("create_time", {}).get("$lt", default_create_time_lt)
        ),
        "order_status": order_status_tuple,
        "buyer_user_id": filters.get("buyer_user_id", {}).get("$eq", ""),
    }
    all_orders = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_shop = {
            executor.submit(fetch_orders_for_shop, shop, filters, user_ids, errors): shop
            for shop in shops
        }
        for future in concurrent.futures.as_completed(future_to_shop):
            all_orders.extend(future.result())
    return all_orders


class ListOderOfUserView(APIView):
    def get(self, request):
        try:
            pagination, filters, sorts = get_pagination(
                request,
                ["create_time", "order_status", "buyer_user_id", "shop_id", "user_id"],
            )
            user = request.user
            errors = []
            all_orders = get_all_order(user, filters, errors)
            limit = pagination.get("limit", 10)
            offset = pagination.get("offset", 0)
            total_items = len(all_orders)
            total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)
            custom_response = {
                "status": "success",
                "meta": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "offset": offset,
                    "limit": limit,
                },
                "data": all_orders,
                "error": errors
            }
            return JsonResponse(custom_response)
            print("all_orders11111111", all_orders)
            sorts.setdefault("create_time", "desc")
            sorted_orders = sort_orders(all_orders, sorts)
            limit = pagination.get("limit", 10)
            offset = pagination.get("offset", 0)
            paginated_orders = order.process_orders_chunk_by_shop_id(
                sorted_orders[offset * limit : (offset + 1) * limit]
            )
            sorted_orders = sort_orders(paginated_orders, sorts)
            total_items = len(all_orders)
            total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)

            shop_id_value = filters.get("shop_id", {}).get("$in", "")
            shop_id_tuple = (
                tuple(set(int(id.strip()) for id in shop_id_value.split(",")))
                if shop_id_value
                else ()
            )
            if len(shop_id_tuple) == 1 & len(errors) > 0:
                return JsonResponse({"error": errors[0]}, status=400)

            custom_response = {
                "status": "success",
                "meta": {
                    "total_items": total_items,
                    "total_pages": total_pages,
                    "offset": offset,
                    "limit": limit,
                },
                "data": sorted_orders,
                "error": errors
            }

            return JsonResponse(custom_response)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


class UpdateTrackingInfor(APIView):
    def post(self, request, shop_id):
        try:
            # Parse the incoming request data
            data = json.loads(request.body.decode("utf-8"))
            order_ids = data.get('package_ids')
            tracking_ids = data.get('tracking_ids')
            
            if not order_ids or not tracking_ids:
                return Response({"error": "package_ids and tracking_ids are required"}, status=status.HTTP_400_BAD_REQUEST)

            # Get the shop object
            shop = Shop.objects.get(id=shop_id)
            
            # Call the utility function to update tracking information
            response = update_tracking_infor(order_ids=order_ids, shop=shop, tracking_ids=tracking_ids)
            
            if response.status_code == 200:
                return Response({"success": "Tracking information updated successfully"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": response.text}, status=response.status_code)
        
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON data"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# class PackageFilter(APIView):
#     permission_classes = (IsAuthenticated,)
#     serializer_class = PackageSerializer

#     # Hàm chuyển đổi unix time thành datetime
#     def convert_unix_to_datetime(self, unix_time):
#         try:
#             return datetime.fromtimestamp(int(unix_time), pytz.utc)
#         except ValueError:
#             raise ValueError("Invalid unix time format")

#     def get(self, request):
#         try:
#             pagination, filters, sorts = get_pagination(
#                 request,
#                 ["create_time", "shop_id", "fulfillment_name"],
#             )
#             user = request.user
#             errors = []

#             # Lấy danh sách các shop theo người dùng
#             shops, _ = get_shop_list(user, filters)

#             # Kiểm tra nếu người dùng có truyền thêm shop_id vào query parameters
#             shop_ids_from_request = request.GET.get("shop_id", "")

#             # Kiểm tra nếu shop_ids_from_request không rỗng, tách và chuyển thành số nguyên
#             if shop_ids_from_request:
#                 try:
#                     shop_id_value = [int(shop_id) for shop_id in shop_ids_from_request.split(',') if shop_id.strip().isdigit()]
#                 except ValueError:
#                     return JsonResponse({"error": "Invalid shop_id format, must be integers."}, status=400)
#             else:
#                 shop_id_value = [shop.id for shop in shops]

#             # Lấy fulfillment_name từ request dưới dạng mảng
#             fulfillment_names = request.GET.getlist("fulfillment_name")

#             # Xử lý bộ lọc create_time
#             create_time_gte = request.GET.get("create_time[$gte]")
#             create_time_lt = request.GET.get("create_time[$lt]")

#             now = datetime.now(pytz.utc)
#             default_create_time_ge = (now - timedelta(days=3)).isoformat()
#             default_create_time_lt = now.isoformat()

#             package_filters = {
#                 "created_at__gte": filters.get("create_time", {}).get("$gte", default_create_time_ge),
#                 "created_at__lt": filters.get("create_time", {}).get("$lt", default_create_time_lt),
#             }

#             if create_time_gte:
#                 try:
#                     package_filters["created_at__gte"] = self.convert_unix_to_datetime(create_time_gte).isoformat()
#                 except ValueError:
#                     return JsonResponse({"error": "Invalid format for create_time[$gte]. Must be a valid unix time."}, status=400)

#             if create_time_lt:
#                 try:
#                     package_filters["created_at__lt"] = self.convert_unix_to_datetime(create_time_lt).isoformat()
#                 except ValueError:
#                     return JsonResponse({"error": "Invalid format for create_time[$lt]. Must be a valid unix time."}, status=400)

#             # Nếu có shop_id_value, thêm vào bộ lọc
#             if shop_id_value:
#                 package_filters["shop__id__in"] = tuple(shop_id_value)

#             # Nếu có fulfillment_names, thêm bộ lọc dùng __in
#             if fulfillment_names:
#                 package_filters["fulfillment_name__in"] = fulfillment_names

#             print("filter", package_filters)

#             # Truy vấn các package với bộ lọc áp dụng
#             packages = Package.objects.filter(**package_filters)

#             # Áp dụng sắp xếp
#             sorts.setdefault("created_at", "desc")
#             sort_criteria = list(sorts.items())
#             for field, order in reversed(sort_criteria):
#                 packages = packages.order_by(f"{'-' if order == 'desc' else ''}{field}")

#             # Phân trang
#             limit = pagination.get("limit", 10)
#             offset = pagination.get("offset", 0)
#             paginated_packages = packages[offset * limit : (offset + 1) * limit]

#             # Serialize kết quả
#             serializer = self.serializer_class(paginated_packages, many=True)

#             # Tạo metadata cho phản hồi
#             total_items = packages.count()
#             total_pages = (total_items // limit) + (1 if total_items % limit > 0 else 0)

#             custom_response = {
#                 "status": "success",
#                 "meta": {
#                     "total_items": total_items,
#                     "total_pages": total_pages,
#                     "offset": offset,
#                     "limit": limit,
#                 },
#                 "data": serializer.data,
#                 "error": errors
#             }

#             return JsonResponse(custom_response)

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=400)