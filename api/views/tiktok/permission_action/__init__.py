import logging

from django.contrib.auth.hashers import make_password

from api import setup_logging
from api.views import APIView, IsAuthenticated, JsonResponse, ObjectDoesNotExist, Response, get_object_or_404

from ....models import CustomUserSendPrint, GroupCustom, User, UserGroup, UserShop
from ....serializers import GroupCustomSerializer

logger = logging.getLogger("api.views.tiktok.permission_action")
setup_logging(logger, is_root=False, level=logging.INFO)


class AddUsertoGroup(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            user_current = request.user
            user_group = UserGroup.objects.get(user=user_current)
            if not user_group.role == 1:
                return JsonResponse({"status": 404, "error": "you don't have permission to do this bro"}, status=404)
            username = request.data.get("username")
            password = request.data.get("password")
            email = request.data.get("email")
            firstname = request.data.get("first_name")
            lastname = request.data.get("last_name")
            shop_ids = request.data.get("shops")
            new_user = User.objects.create_user(
                username=username, password=password, email=email, first_name=firstname, last_name=lastname
            )
            group_custom = user_group.group_custom
            UserGroup.objects.create(user=new_user, group_custom=group_custom, role=2)
            if shop_ids:  # Check if shop_ids is provided and not empty
                for shop_id in shop_ids:
                    UserShop.objects.create(user=new_user, shop_id=shop_id)

            return JsonResponse({"status": 201, "message": "User added to group successfully."}, status=201)
        except ObjectDoesNotExist:
            return JsonResponse({"status": 404, "error": "Object does not exist."}, status=404)
        except Exception as e:
            return JsonResponse({"status": 500, "error": str(e)}, status=500)


class UserInfo(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, user_id):
        user = get_object_or_404(User, id=user_id)

        user_info = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "password": user.password,
        }

        return Response(user_info)


class AddUserToGroup(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            user_current = request.user
            user_group = UserGroup.objects.get(user=user_current)
            if not user_group.role == 1:
                return JsonResponse({"status": 404, "error": "you don't have permission to do this bro"}, status=404)
            username = request.data.get("username")
            print(f"==>> username: {username}")
            password = request.data.get("password")
            print(f"==>> password: {password}")
            firstname = request.data.get("first_name")
            print(f"==>> firstname: {firstname}")
            lastname = request.data.get("last_name")
            print(f"==>> lastname: {lastname}")
            email = request.data.get("email", "")
            print(f"==>> email: {email}")
            user_code = request.data.get("user_code", "")
            print(f"==>> user_code: {user_code}")
            shop_ids = request.data.get("shops")
            group_custom_id = request.data.get("group_custom_id", 1)
            print(f"==>> shop_ids: {shop_ids}")
            new_user = User.objects.get_or_create(
                username=username, password=password, first_name=firstname, email=email, last_name=lastname
            )
            print(f"==>> new_user: {new_user}")
            print(new_user[0].id)
            if user_code:
                CustomUserSendPrint.objects.get_or_create(user=new_user[0], user_code=user_code)

            group_custom = get_object_or_404(GroupCustom, id=group_custom_id)
            UserGroup.objects.get_or_create(user=new_user[0], group_custom=group_custom, role=2)

            if shop_ids:
                for shop_id in shop_ids:
                    result = UserShop.objects.get_or_create(user=new_user[0], shop_id=shop_id)

                    print(result[0].shop.shop_name)

            return JsonResponse({"status": 201, "message": "User added to group successfully."}, status=201)
        except ObjectDoesNotExist:
            return JsonResponse({"status": 404, "error": "Object does not exist."}, status=404)
        except Exception as e:
            logger.error("Error when adding user to group", exc_info=e)
            return JsonResponse({"status": 500, "error": str(e)}, status=500)


class InforUserCurrent(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user
        user_groups = UserGroup.objects.filter(user=user)

        try:
            user_sen = CustomUserSendPrint.objects.get(user=user)
            user_code = user_sen.user_code
        except CustomUserSendPrint.DoesNotExist:
            user_code = ""  # Set default value if CustomUserSendPrint does not exist

        user_info = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "groups": [user_group.group_custom.group_name for user_group in user_groups],
            "role": [user_group.role for user_group in user_groups],
            "user_code": user_code,
        }
        return Response(user_info)


class GroupCustomListAPIView(APIView):
    def get(self, request):
        group_customs = GroupCustom.objects.all().order_by("id")
        serializer = GroupCustomSerializer(group_customs, many=True)
        return Response(serializer.data)


class PermissionRole(APIView):
    permission_classes = (IsAuthenticated,)

    def put(self, request):
        data = request.data
        user_id = data.get("user_id")
        user = get_object_or_404(User, id=user_id)

        # Cập nhật thông tin người dùng
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.username = data.get("username", user.username)
        user.email = data.get("email", user.email)

        password = data.get("password")
        if password and len(password) <= 60:
            hashed_password = make_password(password)
            user.password = hashed_password

        user.save()

        # Cập nhật thông tin CustomUserSendPrint
        user_custom_senprint, created = CustomUserSendPrint.objects.get_or_create(user=user)
        user_custom_senprint.user_code = data.get("user_code", user_custom_senprint.user_code)
        user_custom_senprint.save()

        # Cập nhật UserGroup
        group_custom_id = data.get("group_custom_id", 1)
        print('group_custom_id', group_custom_id)
        if group_custom_id:
            group_custom = get_object_or_404(GroupCustom, id=group_custom_id)
            
            # Get existing UserGroup record and role
            existing_user_group = UserGroup.objects.filter(user=user).first()
            existing_role = existing_user_group.role if existing_user_group else None
            
            # Delete existing UserGroup record
            UserGroup.objects.filter(user=user).delete()
            
            # Create new UserGroup record with existing role
            user_group = UserGroup.objects.create(
                user=user,
                group_custom=group_custom,
                role=existing_role or 2
            )
            if not created:
                user_group.save()

        # Cập nhật danh sách cửa hàng của người dùng
        stores = data.get("shops", [])
        user_shops = UserShop.objects.filter(user=user)
        user_shop_ids = [user_shop.shop_id for user_shop in user_shops]

        for index, store_id in enumerate(stores):
            if store_id not in user_shop_ids:
                UserShop.objects.create(user=user, shop_id=store_id)

        # Xóa các cửa hàng không cần thiết
        user_shops.exclude(shop_id__in=stores).delete()

        # Cập nhật trạng thái hoạt động của người dùng
        user.is_active = data.get("is_active", True)
        user.save()

        return Response({"message": "User information updated successfully."})

    def isManagerOrAdmin(self, user):
        user_group = get_object_or_404(UserGroup, user=user)
        return user_group.role

class GetAllUserGroup(APIView):
    
    def get(self,request,group_id):
        user_groups = UserGroup.objects.filter(group_custom_id=group_id)
        users = []
        for user_group in user_groups:
            users.append(user_group.user)
        print("user", user_group.user)
        data =[]
        for user in users:
            data.append({"user_id":user.id,"username":user.username})
        return JsonResponse({"data": data},  safe=False)


class UserShopListAll(APIView):
    # permission_classes = (IsAuthenticated,)

    def get(self, request,group_id):
        # user = User.objects.get(id = user_id)
        # users_groups = get_object_or_404(UserGroup, group_custom_id=group_id)
        # if users_groups is None:
        #     return Response({"message": "User does not belong to any group."}, status=404)

        group_custom = get_object_or_404(GroupCustom, id = group_id)
        user_shops_data = {"group_id": group_custom.id,
                           "group_name": group_custom.group_name, "users": []}

        for user_group in group_custom.usergroup_set.filter(role__in=[1, 2]):
            user_data = {
                "user_id": user_group.user.id,
                "user_name": user_group.user.username,
                "first_name": user_group.user.first_name,
                "last_name": user_group.user.last_name,
                "password": user_group.user.password,
                "email": user_group.user.email,
                "user_code": None,
                "shops": [],
            }
            custom_user = CustomUserSendPrint.objects.filter(
                user=user_group.user).first()
            if custom_user:
                user_data["user_code"] = custom_user.user_code

            user_shops = UserShop.objects.filter(
                user=user_group.user, shop__group_custom_id=group_custom.id)
            for user_shop in user_shops.filter():
                user_data["shops"].append(
                    {"id": user_shop.shop.id, "name": user_shop.shop.shop_name})

            user_shops_data["users"].append(user_data)

        # Filter out users with is_active = False
        user_shops_data["users"] = [
            user_data for user_data in user_shops_data["users"] if User.objects.get(id=user_data["user_id"]).is_active
        ]

        # Sort users by creation date in descending order (newest first)
        user_shops_data["users"].sort(key=lambda x: User.objects.get(
            id=x["user_id"]).date_joined, reverse=True)

        return Response({"data": user_shops_data})


# class AsyncAllorder(APIView):
    
#     def post(self, request,shop_id):
        