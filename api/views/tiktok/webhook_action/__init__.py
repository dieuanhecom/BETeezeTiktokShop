import json

from django.http import JsonResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated as IsAuthenticated
from rest_framework.response import Response

from api.models import Notification, NotiMessage, Shop, UserShop
from api.serializers import NotificationSerializer
from api.views import APIView


class WebhookDataView(APIView):
    def post(self, request):
        try:
            data = json.loads(request.body)
            shop_author_id = data.get("shop_id")
            shop = Shop.objects.get(shop_id_author=shop_author_id)
            pre_order_status = data["data"]["order_status"]
            if pre_order_status == "AWAITING_SHIPMENT":
                order_status = pre_order_status
            else:
                order_status = ""
            user_shop = UserShop.objects.filter(shop=shop)

            if order_status is not None:
                new_message = NotiMessage.objects.create(
                    type="Order",
                    message=f"New order {order_status} from shop: {shop.shop_name} and orderId {data['data']['order_id']}",
                )
                new_message.save()
                notification = Notification.objects.create(
                    user=user_shop[0].user, shop=shop, message=new_message, is_read=False
                )
                notification.save()

            return JsonResponse({"status": "success", "order_id": data["data"]["order_id"], "shop_id": shop.id})
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)


class ViewNotiForOrder(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            user = request.user
            user_shops = UserShop.objects.filter(user=user)
            shop_ids = []
            for user_shop in user_shops:
                shop_ids.append(user_shop.shop.id)
            lastest_notis = []
            for shop_id in shop_ids:
                latest_noti = Notification.objects.filter(shop=shop_id, is_read=False).order_by("-created_at")
                lastest_notis.extend(latest_noti)

            serializer = NotificationSerializer(lastest_notis, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)


class MaskAsReadNoti(APIView):
    def put(self, request, noti_id):
        try:
            noti = Notification.objects.get(id=noti_id)
            noti.is_read = True
            noti.save()
            return Response({"message": "Notification marked as read"}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
