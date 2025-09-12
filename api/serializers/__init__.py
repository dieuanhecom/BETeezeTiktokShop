from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from ..helpers import check_token
from ..models import (BuyedPackage, DesignSku, FlashShipPODVariantList,
                      GroupCustom, Image, ImageFolder, Notification,
                      NotiMessage, Package, ProductPackage, Shop,
                      TemplateDesign, Templates, CkfVariant, CombineLabelTask)


class SignUpSerializers(serializers.ModelSerializer):
    username = serializers.CharField(
        max_length=30,
        label=("Username"),
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    email = serializers.EmailField(
        max_length=100,
        label=("Email"),
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())],
    )
    password1 = serializers.CharField(
        max_length=255,
        label=("Password"),
        write_only=True,
        required=True,
        validators=[validate_password],
    )
    password2 = serializers.CharField(
        max_length=255,
        label=("Confirm Password"),
        write_only=True,
        required=True,
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password1",
            "password2",
            "first_name",
            "last_name",
        ]

    def validate(self, data):
        if data["password1"] != data["password2"]:
            raise serializers.ValidationError(("Password does not match"))

        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password1"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=False,
        )

        return user


class VerifySerializers(serializers.ModelSerializer):
    pk = serializers.IntegerField(label=("User ID"))
    verify_token = serializers.CharField(max_length=255, label=("Verify token"))

    class Meta:
        model = User
        fields = ["pk", "verify_token"]

    def validate(self, data):
        user = User.objects.get(pk=data["pk"])
        if not check_token(user, data["verify_token"]):
            raise serializers.ValidationError(("Activation link is invalid!"))
        return data

    def update(self, instance, validated_data):
        instance.is_active = True
        instance.save()
        return instance


class ShopSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = "__all__"


class ShopRequestSerializers(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ["shop_name", "auth_code"]


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Templates
        exclude = ['size_chart', 'fixed_images']


class TemplatePutSerializer(serializers.ModelSerializer):
    images_link_variant = serializers.ListField(
        child=serializers.CharField(max_length=500, allow_blank=True),
        required=False,
        default=list
    )

    class Meta:
        model = Templates
        fields = [
            "name",
            "category_id",
            "description",
            "is_cod_open",
            "package_height",
            "package_length",
            "package_weight",
            "package_width",
            "sizes",
            "colors",
            "type",
            "option1",
            "option2",
            "option3",
            "types",
            "badWords",
            "suffixTitle",
            "size_chart",
            "fixed_images",
            "images_link_variant",
            "templateType",
            "customTemplateData",
            "attributes",
            "size_chart_url",
            "fixed_image_urls",
        ]



class BuyedPackageSeri(serializers.ModelSerializer):
    class Meta:
        model = BuyedPackage
        fields = "__all__"


class DesignSkuSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignSku
        fields = "__all__"


class DesignSkuPutSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignSku
        fields = ["image_front", "image_back","mockup_front","mockup_back", "type_print", "type_shirt"]
        extra_kwargs = {
            "image_front": {"required": False},
            "image_back": {"required": False},
            "mockup_front": {"required": False},
            "mockup_back": {"required": False},
            "type_print": {"required": False},
            "type_shirt": {"required": False},
        }


class GroupCustomSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupCustom
        fields = ["id", "group_name"]


class FlashShipPODVariantListSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashShipPODVariantList
        fields = ["variant_id", "color", "size", "product_type"]



class ProductPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductPackage
        fields = [
            "id",  # Thêm trường id để lấy ra id của product package
            "quantity",
            "variant_id",
            "note",
            "printer_design_front_url",
            "printer_design_back_url",
            "mock_up_front_url",
            "mock_up_back_url",
            "color",
            "size",
            "style",
            "product_name",
            "sku_custom"
        ]
        extra_kwargs = {
            "printer_design_front_url": {"allow_blank": True, "required": False},
            "printer_design_back_url": {"allow_blank": True, "required": False},
            "mock_up_front_url": {"allow_blank": True, "required": False},
            "mock_up_back_url": {"allow_blank": True, "required": False},
            "color": {"allow_blank": True, "required": False},
            "size": {"allow_blank": True, "required": False},
            "style": {"allow_blank": True, "required": False},
            "product_name": {"allow_blank": True, "required": False},
        }



class PackageSerializer(serializers.ModelSerializer):
    products = ProductPackageSerializer(many=True)
    shop_name = serializers.CharField(source='shop.shop_name', read_only=True)
    seller_username = serializers.CharField(source='seller', read_only=True)  # Lấy username từ seller
 
    class Meta:
        model = Package
        fields = [
            "id",
            "order_id",
            "buyer_first_name",
            "buyer_last_name",
            "buyer_email",
            "buyer_phone",
            "buyer_address1",
            "buyer_address2",
            "buyer_city",
            "buyer_province_code",
            "buyer_zip",
            "buyer_country_code",
            "shipment",
            "linkLabel",
            "products",
            "fulfillment_name",
            "shop",
            "shop_name",
            "order_code",
            "pack_id",
            "package_status",
            "created_at",
            "seller",
            "seller_username",
            "tracking_id",
            "status",
            "update_time",
            "update_by",
            "supify_create_time",
            "seller_note",
            "number_sort"
        ]

    def create(self, validated_data):
        products_data = validated_data.pop("products")
        package = Package.objects.create(**validated_data)
        for product_data in products_data:
            ProductPackage.objects.create(package=package, **product_data)
        return package


class PackageDeactiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ["package_status"]


class TemplateDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateDesign
        fields = "__all__"


class NotiMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotiMessage
        fields = ("id", "type", "message")


class NotificationSerializer(serializers.ModelSerializer):
    message = NotiMessageSerializer()
    shop = serializers.SerializerMethodField()

    # Lấy tên người dùng từ mô hình người dùng Django
    user = serializers.SerializerMethodField()

    def get_shop(self, obj):
        return obj.id

    def get_user(self, obj):
        return obj.user.username  # Lấy username từ user object

    class Meta:
        model = Notification
        fields = ("id", "user", "shop", "message", "created_at", "is_read")


class NotiPutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "is_read"


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = ("id", "image_url", "image_name", "created_at")


class NestedImageFolderSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        children_qs = obj.children.all()
        serializer = NestedImageFolderSerializer(children_qs, many=True)
        return serializer.data

    class Meta:
        model = ImageFolder
        fields = "__all__"


class ImageFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageFolder
        fields = ["id", "name", "parent"]


class CkfVariantListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CkfVariant
        fields = ["variant_id", "color", "product_type"]

class PackageStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ['status','update_by']  # Chỉ cho phép cập nhật trường 'status'

    def validate_status(self, value):
        """
        Validate để kiểm tra trạng thái hợp lệ.
        """
        if value not in dict(Package.PackageStatus.choices).keys():
            raise serializers.ValidationError("Trạng thái không hợp lệ.")
        return value

class PackageFulfillmentNameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = ['fulfillment_name','update_by','supify_create_time','status','number_sort']  # Chỉ cho phép cập nhật trường 'fulfillment_name'

    def validate_fulfillment_name(self, value):
        """
        Validate để kiểm tra fulfillment_name hợp lệ.
        """
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Fulfillment name không được để trống.")
        if len(value) > 500:
            raise serializers.ValidationError("Fulfillment name không được dài quá 500 ký tự.")
        return value


class CombineLabelTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CombineLabelTask
        fields = [
            'id', 'user', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'urls', 'total_urls', 'status', 'status_display', 'successful_count',
            'failed_count', 'successful_urls', 'failed_urls', 'drive_link',
            'error_message', 'duration'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'started_at', 'completed_at',
            'status', 'successful_count', 'failed_count', 'successful_urls',
            'failed_urls', 'drive_link', 'error_message'
        ]
    
    def get_duration(self, obj):
        """Tính thời gian xử lý"""
        from django.utils import timezone
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        elif obj.started_at:
            return (timezone.now() - obj.started_at).total_seconds()
        return None