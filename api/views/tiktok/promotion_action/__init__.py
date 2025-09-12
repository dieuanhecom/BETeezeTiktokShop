import json
import logging

from asgiref.sync import async_to_sync

from api import setup_logging
from api.utils.tiktok_base_api import promotion
from api.views import APIView, JsonResponse, get_object_or_404

from ....models import Shop

logger = logging.getLogger("api.views.tiktok.product")
setup_logging(logger, is_root=False, level=logging.INFO)

"""Promotion"""


class GetPromotionsView(APIView):
    def get(self, request, shop_id: str):
        shop = get_object_or_404(Shop, id=shop_id)
        status = request.GET.get("status")
        page_number = request.GET.get("page_number")
        page_size = request.GET.get("page_size")
        title = request.GET.get("title")

        data = async_to_sync(promotion.get_promotions)(
            access_token=shop.access_token, status=status, title=title, page_number=page_number, page_size=page_size
        )

        return JsonResponse(data)


class GetPromotionDetailView(APIView):
    def get(self, request, shop_id: int, promotion_id: int):
        shop = get_object_or_404(Shop, id=shop_id)

        data = promotion.get_promotion_detail(
            access_token=shop.access_token, shop_id=str(shop_id), promotion_id=str(promotion_id)
        )

        return JsonResponse(data)


class CreatePromotionView(APIView):
    def post(self, request, shop_id: str):
        shop = get_object_or_404(Shop, id=shop_id)
        body_raw = request.body.decode("utf-8")
        promotion_data = json.loads(body_raw)

        data = async_to_sync(promotion.create_promotion)(access_token=shop.access_token, **promotion_data)

        return JsonResponse(data)


class AddOrUpdatePromotionView(APIView):
    def patch(self, request, shop_id: str):
        shop = get_object_or_404(Shop, id=shop_id)
        body_raw = request.body.decode("utf-8")
        promotion_data = json.loads(body_raw)

        data = promotion.add_or_update_promotion(access_token=shop.access_token, **promotion_data)

        return JsonResponse(data)


class GetAllUnPromotionProduct(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        data = promotion.get_unpromotion_products(access_token=access_token)
        return JsonResponse(data)


class AddOrUpdateDiscount(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        promotion_data = json.loads(body_raw)
        response = promotion.add_update_discount(
            access_token=access_token,
            title=promotion_data.get("title"),
            begin_time=promotion_data.get("begin_time"),
            end_time=promotion_data.get("end_time"),
            type=promotion_data.get("type"),
            product_type="SPU",
            product_list=promotion_data.get("product_list"),
        )
        return response


class AddOrUpdateFlashDeal(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        body_raw = request.body.decode("utf-8")
        promotion_data = json.loads(body_raw)
        response = promotion.add_update_flashdeal(
            access_token=access_token,
            title=promotion_data.get("title"),
            begin_time=promotion_data.get("begin_time"),
            end_time=promotion_data.get("end_time"),
            type=promotion_data.get("type", "FlashSale"),
            product_type="SKU",
            product_list=promotion_data.get("product_list"),
        )
        return response


class GetAllUnPromotionSKU(APIView):
    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        data = promotion.get_unpromotion_sku(access_token=access_token)
        return JsonResponse(data)


class DeactivePromotion(APIView):
    def post(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)

        access_token = shop.access_token

        body_raw = request.body.decode("utf-8")
        body_data = json.loads(body_raw)

        promotion_ids = body_data.get("promotion_ids", [])

        data = []
        for promotion_id in promotion_ids:
            response = promotion.deactivate_promotion(access_token=access_token, promotion_id=promotion_id)
            data.append(response.get("title"))

        return JsonResponse(data, safe=False)


class DetailPromo(APIView):
    def get(self, request, shop_id, promo_id):
        shop = get_object_or_404(Shop, id=shop_id)
        access_token = shop.access_token
        res = promotion.detail_promotion(access_token=access_token, promotion_id=promo_id)
        return JsonResponse(res, safe=False)
