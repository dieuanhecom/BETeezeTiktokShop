import logging

from api import setup_logging
from api.views import (
    AllowAny,
    APIView,
    Response,
    extend_schema,
    force_str,
    model_to_dict,
    status,
    transaction,
    urlsafe_base64_decode,
)

from ....helpers import send_mail_verification  # TODO: Chuyển helpers vào trong utils
from ....models import User
from ....serializers import SignUpSerializers, VerifySerializers

logger = logging.getLogger("api.views.tiktok.auth")
setup_logging(logger, is_root=False, level=logging.INFO)


class SignUp(APIView):
    permission_classes = [AllowAny]  # Cho phép tất cả mọi người truy cập

    @extend_schema(
        request=SignUpSerializers,  # Sử dụng serializer SignUpSerializers để mô tả request
        responses={201: {"description": "Please check your email to verify your account."}},
    )
    def post(self, request):
        serializer = SignUpSerializers(data=request.data)

        if serializer.is_valid():
            with transaction.atomic():  # Sử dụng transaction để đảm bảo dữ liệu được lưu an toàn
                serializer.save()  # Lưu thông tin user vào database
                new_user = serializer.instance
                send_mail_verification(request=request, user=new_user)
                data = {"message": "Please check your email to verify your account.", "user": serializer.data}

                return Response(data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class Verify(APIView):
    permission_classes = [AllowAny]

    def get(self, request, uidb64, token):  # uidb64 là chuỗi mã hóa của user.id
        uid = force_str(urlsafe_base64_decode(uidb64))  # Giải mã uidb64
        user = User.objects.get(id=uid)

        user_dict = model_to_dict(user)
        user_data = {"pk": uid, "verify_token": token}

        serializer = VerifySerializers(user, data=user_data)

        if serializer.is_valid():
            serializer.save()

            data = {
                "message": ("Thank you for your email confirmation. Now you can login your account."),
                "user": user_dict,
            }

            return Response(data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
