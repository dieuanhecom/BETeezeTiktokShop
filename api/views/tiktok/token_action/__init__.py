import asyncio
import logging

from rest_framework.permissions import IsAuthenticated as IsAuthenticated

from api import setup_logging
from api.utils.tiktok_base_api import token
from api.views import APIView, Response, get_object_or_404

from ....models import Shop

logger = logging.getLogger("api.views.token")
setup_logging(logger, is_root=False, level=logging.INFO)


class RefreshToken(APIView):
    """
    Refresh token của shop sau 7 ngày
    """

    def post(self, request, shop_id: int):
        shop = get_object_or_404(Shop, id=shop_id)

        # Call TikTok Shop API để refresh token của
        response = token.refreshToken(refresh_token=shop.refresh_token, app_key = shop.app_key, app_secret = shop.app_secret)
        json_data = response.json()
        data = json_data.get("data", {})

        # Lấy ra refresh token mới
        access_token = data.get("access_token", None)
        refresh_token = data.get("refresh_token", None)

        logger.info(f"Access token: {access_token}, Refresh token: {refresh_token}")

        # Update refresh token mới vào database
        shop.access_token = access_token
        shop.refresh_token = refresh_token
        shop.save()

        return Response(response)


class RefreshTokenAuthorizedShop(APIView):
    # permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            shops_active = Shop.objects.filter(is_active=True)
            access_tokens = []

            for shop in shops_active:
                response = token.refreshToken(refresh_token=shop.refresh_token)
                asyncio.sleep(4)
                json_data = response.json()
                data = json_data.get("data", {})
                access_token = data.get("access_token")

                if access_token:
                    access_tokens.append(access_token)
                    shop.access_token = access_token
                    shop.save()

            for access_token in access_tokens:
                shop = Shop.objects.get(access_token=access_token, is_active=True)
                response = token.get_author_shop(access_token=access_token)
                json_data = response.json()
                shop_list = json_data.get("data", {}).get("shop_list", [])

                if shop_list:
                    shop_info = shop_list[0]
                    shop.shop_id_author = shop_info.get("shop_id")
                    shop.shop_cipher = shop_info.get("shop_cipher")
                    shop.save()
                    print("thanh cong shop")
                    asyncio.sleep(4)

        except Exception as e:
            print(e)

        return Response({"message": "Processed authorized shops successfully"})
