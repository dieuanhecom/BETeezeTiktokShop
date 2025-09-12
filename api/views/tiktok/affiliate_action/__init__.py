from rest_framework.views import APIView
from rest_framework.response import Response
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
from api.utils.tiktok_base_api import affiliate
from ....models import Shop
from api.utils.tiktok_base_api import product
import logging
logger = logging.getLogger("api.views.tiktok.affiliate")
import json

class SearchSellerCreators(APIView):
    def get(self, request):
        shop = get_object_or_404(Shop, id=947)
        access_token = shop.access_token

        try:
            response = affiliate.search_seller_creators(access_token=access_token, app_key = shop.app_key, app_secret = shop.app_secret, shop_cipher = shop.shop_cipher, page_size = 20, page_token = '')
            data_json_string = response.content.decode("utf-8")
            print("data_json_string: ", data_json_string)
            data = json.loads(data_json_string)
            response_data = {
                "code": 0,
                "data": data,
                "message": "Success",
            }
            return JsonResponse(response_data, status=200)
        except Exception as e:
            logger.error(f"User {request.user}: Error when get seller creators", exc_info=e)
            return Response(
                {"status": "error", "message": "Có lỗi xảy ra khi lấy seller creators", "data": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
    
    def post(self, request):
        return Response({"message": "Hello, world!"})
    
    def put(self, request):
        return Response({"message": "Hello, world!"})
    
    def delete(self, request):
        return Response({"message": "Hello, world!"})
    
    def patch(self, request):
        return Response({"message": "Hello, world!"})
