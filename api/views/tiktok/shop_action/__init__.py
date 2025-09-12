import logging

from api import setup_logging
from api.utils import constant
from api.utils.tiktok_base_api import token
from api.views import (APIView, IsAuthenticated, ListAPIView, OpenApiParameter,
                       Response, extend_schema, get_object_or_404, status)

from ....models import CustomUserSendPrint, Shop, User, UserGroup, UserShop
from ....serializers import ShopRequestSerializers, ShopSerializers

logger = logging.getLogger("api.views.tiktok.shop")
setup_logging(logger, is_root=False, level=logging.INFO)


class Shops(APIView):
    permission_classes = (IsAuthenticated,)

    def get_user_group(self, user):
        """
        Lấy thông tin group (department) của user
        """
        try:
            user_group = UserGroup.objects.get(user=user)
            return user_group.group_custom
        except UserGroup.DoesNotExist:
            return None

    @extend_schema(
        request=ShopSerializers,
        responses=ShopSerializers,
    )
    def get(self, request):
        user = request.user
        user_group = get_object_or_404(UserGroup, user=user)

        if user_group.role != 1:
            user_shops = UserShop.objects.filter(user=request.user)
            user_shops = user_shops.filter(shop__is_active=True)
            shop_ids = [user_shop.shop_id for user_shop in user_shops]
            shops = Shop.objects.filter(id__in=shop_ids)

            serializer = ShopSerializers(shops, many=True)
            filtered_data = []
            for shop in serializer.data:
                shop_data = {k:v for k,v in shop.items() if k not in ['app_key', 'app_secret', 'service_link']}
                filtered_data.append(shop_data)
            return Response(filtered_data)

        group_custom = user_group.group_custom
        users_in_group = group_custom.usergroup_set.values_list("user", flat=True)

        shops = Shop.objects.filter(
            usershop__user__in=users_in_group, is_active=True
        ).distinct()
        serializer = ShopSerializers(shops, many=True)
        filtered_data = []
        for shop in serializer.data:
            shop_data = {k:v for k,v in shop.items() if k not in ['app_key', 'app_secret', 'service_link']}
            filtered_data.append(shop_data)
        return Response(filtered_data)

    @extend_schema(request=ShopRequestSerializers, responses=ShopSerializers)
    def post(self, request):
        auth_code = request.data.get("auth_code", None)
        shop_name = request.data.get("shop_name", None)
        shop_code = request.data.get("shop_code", None)
        user_seller_id = request.data.get("user_id", None)
        # app_key = request.data.get("app_key", None)
        # app_secret = request.data.get("app_secret", None)
        app_key = constant.app_key
        app_secret = constant.secret
        service_link = request.data.get("service_link", None)
        print("auth code", auth_code)
        if not auth_code:
            logger.error(f"User {request.user} does not provide auth_code")
            return Response(
                {"error": "auth_code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Từ auth_code, lấy access_token và refresh_token
        response = token.getAccessToken(auth_code=auth_code, app_key=app_key, app_secret=app_secret)
        group_custom = self.get_user_group(user=self.request.user)
        logger.info(f"User {self.request.user} is in group (department) {group_custom}")

        if response.status_code == 200:
            json_data = response.json()
            print('json_data: ', json_data);
            if json_data.get("code") == 36004004:
                return Response(
                    {"error": "Invalid auth code"}, status=status.HTTP_400_BAD_REQUEST
                )
            data = json_data.get("data", None)
            access_token = data.get("access_token", None)
            refresh_token = data.get("refresh_token", None)
            logger.info(f"Access token: {access_token}, Refresh token: {refresh_token}")
        else:
            print("Ddddd")
            logger.error(
                
                f"User {request.user}: Get access token failed: {response.text}"
            )
            return Response(
                {
                    "error": "Failed to retrieve access_token or refresh_token from the response",
                    "detail": response.text,
                },
                status=response.status_code,
            )

        if not access_token or not refresh_token:
            logger.error(
                f"User {request.user}: Get access token failed: {response.text}"
            )
            return Response(
                {
                    "error": "Failed to retrieve access_token or refresh_token from the response",
                    "detail": response.text,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Sau khi lấy được access_token và refresh_token, lưu vào database
        res_author = token.get_author_shop(access_token=access_token, app_key=app_key, app_secret=app_secret)
        json_data = res_author.json()
        shop_list = json_data.get("data", {}).get("shop_list", [])
        if shop_list:
            shop_info = shop_list[0]
        shop_data = {
            "auth_code": auth_code,
            "app_key": app_key,
            "app_secret":  app_secret,
            "service_link": service_link,
            "grant_type": "authorized_code",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "shop_name": shop_name,
            "shop_code": shop_code,
            "group_custom_id": group_custom.id,
            "is_active": True,
            "shop_id_author": shop_info.get("shop_id"),
            "shop_cipher": shop_info.get("shop_cipher"),
        }

        shop_serializer = ShopSerializers(data=shop_data)

        if shop_serializer.is_valid():
            shop_code = shop_data.get("shop_code")

            # Kiểm tra xem shop đã tồn tại trong database chưa
            if Shop.objects.filter(shop_code=shop_code).exists():
                existing_shop = Shop.objects.get(shop_code=shop_code)

                # Cập nhật instance cửa hàng hiện có với access_token và refresh_token mới
                existing_shop.auth_code = auth_code
                # existing_shop.app_key = constant.app_key
                # existing_shop.app_secret = constant.secret
                # existing_shop.grant_type = "authorized_code"
                existing_shop.access_token = access_token
                existing_shop.refresh_token = refresh_token
                existing_shop.shop_name = shop_name
                existing_shop.is_active = True
                existing_shop.shop_id_author = shop_info.get("shop_id")
                existing_shop.shop_cipher = shop_info.get("shop_cipher")
                existing_shop.save()

                return Response(shop_serializer.data, status=status.HTTP_201_CREATED)

            # Nếu shop chưa tồn tại, tạo mới
            new_shop = shop_serializer.save()

            if user_seller_id:
                try:
                    user_seller = User.objects.get(id=user_seller_id)
                    UserShop.objects.create(user=user_seller, shop=new_shop)
                except User.DoesNotExist:
                    logger.error(f"User {user_seller_id} does not exist")
                    return Response(
                        {"error": f"User {user_seller_id} does not exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            return Response(shop_serializer.data, status=status.HTTP_201_CREATED)

        # Nếu dữ liệu không hợp lệ, trả về thông báo lỗi
        logger.error(
            f"User {request.user}: Invalid shop data: {shop_serializer.errors}"
        )
        return Response(shop_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ShopDetail(APIView):
    def put(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        shop_serializer = ShopSerializers(shop, data=request.data)

        if shop_serializer.is_valid():
            shop_serializer.save()
            return Response(shop_serializer.data, status=status.HTTP_200_OK)
        else:
            logger.error(
                f"User {request.user}: Invalid shop data: {shop_serializer.errors}"
            )
            return Response(shop_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)
        shop_serializer = ShopSerializers(shop)
        return Response(shop_serializer.data)

    def delete(self, request, shop_id):
        shop = get_object_or_404(Shop, id=shop_id)

        try:
            shop.delete()
            return Response(
                {
                    "status": "success",
                    "message": f"Shop with id {shop_id} deleted successfully",
                },
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception as e:
            logger.error(f"User {request.user}: Delete shop failed: {e}")
            return Response(
                {"error": f"Failed to delete shop with id {shop_id}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ShopSearchViews(ListAPIView):
    serializer_class = ShopSerializers

    @extend_schema(
        parameters=[
            OpenApiParameter(name="shop_name", required=False, type=str),
            OpenApiParameter(name="shop_code", required=False, type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(self, request, *args, **kwargs)

    def get_queryset(self):
        queryset = Shop.objects.all()

        shop_name = self.request.query_params.get("shop_name", None)
        shop_code = self.request.query_params.get("shop_code", None)

        if shop_name:
            queryset = queryset.filter(shop_name__icontains=shop_name)
        if shop_code:
            queryset = queryset.filter(shop_code__icontains=shop_code)

        return queryset


class UserShopList(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        # users_groups = get_object_or_404(UserGroup, user=user)
        users_groups = UserGroup.objects.all()
        print('users_groups', users_groups)
        if users_groups is None:
            return Response(
                {"message": "User does not belong to any group."}, status=404
            )

        # group_custom = users_groups.group_custom
        user_shops_data = {
            # "group_id": group_custom.id,
            # "group_name": group_custom.group_name,
            "users": [],
        }

        for user_group in users_groups:
            user_groups = UserGroup.objects.filter(user=user_group.user)
            user_data = {
                "user_id": user_group.user.id,
                "user_name": user_group.user.username,
                "first_name": user_group.user.first_name,
                "last_name": user_group.user.last_name,
                "password": user_group.user.password,
                "email": user_group.user.email,
                "user_code": None,
                "shops": [],
                "group_custom_id": user_groups[0].group_custom.id,
            }
            custom_user = CustomUserSendPrint.objects.filter(
                user=user_group.user
            ).first()
            if custom_user:
                user_data["user_code"] = custom_user.user_code

            user_shops = UserShop.objects.filter(
                user=user_group.user
            )
            for user_shop in user_shops.filter(shop__is_active=True):
                user_data["shops"].append(
                    {"id": user_shop.shop.id, "name": user_shop.shop.shop_name}
                )

            user_shops_data["users"].append(user_data)

        # Filter out users with is_active = False
        user_shops_data["users"] = [
            user_data
            for user_data in user_shops_data["users"]
            if User.objects.get(id=user_data["user_id"]).is_active
        ]

        # Sort users by creation date in descending order (newest first)
        user_shops_data["users"].sort(
            key=lambda x: User.objects.get(id=x["user_id"]).date_joined, reverse=True
        )

        return Response({"data": user_shops_data})


class ShopList(APIView):
    """
    Get shop managed by specific user
    """

    def get(self, request):
        user_shop = UserShop.objects.filter(user=request.user)
        shops = Shop.objects.filter(id=user_shop.shop.id)
        serializer = ShopSerializers(shops, many=True)
        return Response(serializer.data)


class ShopListAPI(APIView):
    """
    List all shops of all users
    """

    def get(self, request):
        shops = Shop.objects.filter()
        serializer = ShopSerializers(shops, many=True)
        return Response(serializer.data)
