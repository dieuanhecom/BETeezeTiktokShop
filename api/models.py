from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import JSONField
from django.utils import timezone
from api.utils import constant


class CustomUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    verify_token = models.CharField(("Verify token"), max_length=255, null=True)


class GroupCustom(models.Model):
    group_name = models.CharField(null=False, help_text="ten cua phong ban", max_length=500, default="chua co ten")


class UserGroup(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group_custom = models.ForeignKey(GroupCustom, on_delete=models.CASCADE)

    role = models.IntegerField(
        ("Role"),
        choices=constant.ROLE_USERGROUP_CHOICES,
        default=constant.ROLE_USERGROUP_DEFAULT,
    )

    class Meta:
        unique_together = (("user", "group_custom"),)

    def print_attributes(self):
        print(f"User: {self.user}")
        print(f"Group Custom: {self.group_custom}")
        print(f"Role: {self.role}")


class Shop(models.Model):
    shop_code = models.CharField(null=False, help_text="Shop id lấy từ shop code", max_length=500, default="")
    access_token = models.CharField(null=False, max_length=500)
    refresh_token = models.CharField(null=True, max_length=500)
    auth_code = models.CharField(null=False, max_length=500)
    grant_type = models.CharField(default="authorized_code", max_length=500)
    shop_name = models.CharField(max_length=500)
    group_custom_id = models.ForeignKey(GroupCustom, on_delete=models.SET_NULL, null=True)
    objects = models.Manager()
    is_active = models.BooleanField(default=True)
    shop_id_author = models.CharField(null=True, max_length=500)
    shop_cipher = models.CharField(null=True, max_length=500)
    shop_description = models.CharField(null=True, max_length=500)
    app_key = models.CharField(null=True, max_length=500)
    app_secret = models.CharField(null=True, max_length=500)
    service_link = models.CharField(null=True, max_length=500)
# class Image(models.Model):
#     image_data = models.TextField()


class AppKey(models.Model):
    app_key = models.CharField(
        null=False, help_text="App key lấy từ tiktok app for developer", max_length=500, default=""
    )
    secret = models.CharField(
        null=False, help_text="App secret lấy từ tiktok app for developer", max_length=500, default=""
    )
    link_service = models.CharField(
        null=False, help_text="Link service lấy từ tiktok app for developer", max_length=500, default=""
    )


class Categories(models.Model):
    data = JSONField()
    objects = models.Manager()


class Brand(models.Model):
    data = JSONField()
    objects = models.Manager()


class UserShop(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE)


class Templates(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(null=False, max_length=500, default="")
    category_id = JSONField()
    description = models.TextField(null=False, max_length=50000, default="")
    is_cod_open = models.BooleanField(default=False)
    package_height = models.FloatField(default=1)
    package_length = models.FloatField(default=1)
    package_weight = models.FloatField(default=1)
    package_width = models.FloatField(default=1)
    sizes = ArrayField(models.CharField(max_length=200), null=True, default=list)
    colors = ArrayField(models.CharField(max_length=200), null=True, default=list)
    type = ArrayField(models.CharField(max_length=200), null=True, default=list)
    types = JSONField()
    badWords = ArrayField(models.CharField(max_length=200), null=True, default=list)
    suffixTitle = models.CharField(null=True, max_length=500, default="")
    size_chart = models.TextField(null=True)
    fixed_images = ArrayField(models.TextField(), null=True, default=list)
    option1 =  JSONField(null=True)
    option2 =  JSONField(null=True)
    option3 =  JSONField(null=True)
    images_link_variant = ArrayField(models.CharField(max_length=500, null=True), null=True, default=list)
    objects = models.Manager()
    templateType = models.CharField(null=True, max_length=500, default="")
    customTemplateData = models.JSONField(null=True)
    attributes = JSONField(null=True)
    size_chart_url = models.CharField(null=True, max_length=500, default="")
    fixed_image_urls = ArrayField(models.CharField(max_length=500, null=True), null=True, default=list)


class Products(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.SET_NULL, null=True)
    data = models.JSONField()


class BuyedPackage(models.Model):
    package_id = models.CharField(null=False, max_length=500, help_text="Package_id da duoc buy label")


class DesignSku(models.Model):
    sku_id = models.CharField(null=False, max_length=500, help_text="SKU ID")
    product_name = models.CharField(null=False, max_length=500, help_text="product_name")
    variation = models.CharField(null=False, max_length=500, help_text="variation")
    image_front = models.CharField(null=True, max_length=500, help_text="image_front", blank=True)
    image_back = models.CharField(null=True, max_length=500, help_text="image_back", blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(GroupCustom, on_delete=models.SET_NULL, null=True)
    mockup_front = models.CharField(null=True, max_length=500, help_text="mockup_front", blank=True)
    mockup_back = models.CharField(null=True, max_length=500, help_text="mockup_back", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_designs')
    type_print = models.CharField(null=True, max_length=50, help_text="type_print", blank=True)
    type_shirt = models.CharField(null=True, max_length=50, help_text="type_shirt", blank=True)

class DesignSkuChangeHistory(models.Model):
    design_sku = models.ForeignKey(DesignSku, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    change_data = models.TextField(null=True)
    changed_at = models.DateTimeField(auto_now_add=True)


class FlashShipPODVariantList(models.Model):
    SHIRT = "SHIRT"
    HOODIE = "HOODIE"
    SWEATSHIRT = "SWEATSHIRT"

    PRODUCT_TYPE_CHOICES = [
        (SHIRT, "Shirt"),
        (HOODIE, "Hoodie"),
        (SWEATSHIRT, "Sweatshirt"),
    ]

    variant_id = models.IntegerField()
    color = models.CharField(max_length=500)
    size = models.CharField(max_length=200)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)

    def __str__(self):
        return f"{self.variant_id} - {self.color} - {self.size} - {self.product_type}"


class CombineLabelTask(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Đang chờ xử lý'),
        ('PROCESSING', 'Đang xử lý'),
        ('COMPLETED', 'Hoàn thành'),
        ('FAILED', 'Thất bại'),
        ('CANCELLED', 'Đã hủy'),
    ]
    
    # Thông tin cơ bản
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='combine_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Input data
    urls = ArrayField(models.CharField(max_length=1000), default=list)
    total_urls = models.IntegerField(default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    successful_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    successful_urls = ArrayField(models.CharField(max_length=1000), default=list)
    failed_urls = JSONField(default=list)  # [{url: "...", error: "..."}]
    drive_link = models.CharField(max_length=1000, null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Task tracking
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'combine_label_tasks'
    
    def __str__(self):
        return f"Combine Task {self.id} - {self.status} - {self.user.username}"



class Package(models.Model):
    # Các trường hiện tại
    order_id = models.CharField(max_length=500)
    buyer_first_name = models.CharField(max_length=500, blank=True, null=True)
    buyer_last_name = models.CharField(max_length=500, blank=True, null=True)
    buyer_email = models.CharField(max_length=500, null=True)
    buyer_phone = models.CharField(max_length=200, blank=True, null=True)
    buyer_address1 = models.CharField(max_length=1000, blank=True, null=True)
    buyer_address2 = models.CharField(max_length=1000, blank=True)
    buyer_city = models.CharField(max_length=500, blank=True, null=True)
    buyer_province_code = models.CharField(max_length=20, blank=True, null=True)
    buyer_zip = models.CharField(max_length=100, blank=True, null=True)
    buyer_country_code = models.CharField(max_length=2, null=True)
    shipment = models.IntegerField(null=True)
    linkLabel = models.CharField(max_length=1000, blank=True, null=True)
    fulfillment_name = models.CharField(max_length=500, null=True)
    shop = models.ForeignKey('Shop', on_delete=models.SET_NULL, null=True)
    order_code = models.CharField(max_length=500, blank=True, null=True)
    pack_id = models.CharField(max_length=500, blank=True, null=True)
    package_status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    seller = models.CharField(max_length=500, blank=True, null=True)
    tracking_id = models.CharField(max_length=500, blank=True, null=True)
    update_time = models.DateTimeField(auto_now_add=True, null=True)
    update_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True,related_name='updated_packages')
    supify_create_time = models.DateTimeField(null=True)
    seller_note = models.CharField(max_length=100, blank=True, null=True)
    number_sort = models.IntegerField(null=True)
    # Trạng thái của package
    class PackageStatus(models.TextChoices):
        INIT ='init','khởi tạo'
        NO_DESIGN = 'no_design', 'Chưa có design'
        HAS_DESIGN = 'has_design', 'Đã tồn tại design'
        PRINT_PENDING = 'print_pending', 'Đang inpet'
        PRINTED = 'printed', 'Đã inpet'
        IN_PRODUCTION = 'in_production', 'Đang sản xuất'
        PRODUCTION_DONE = 'production_done', 'Đã sản xuất xong'
        SHIPPING_TO_US = 'shipping_to_us', 'Đang ship đến Mỹ'
        SHIPPED_TO_US = 'shipped_to_us', 'Đã ship đến Mỹ'
        SHIPPING_WITHIN_US = 'shipping_within_us', 'Đang ship trong Mỹ'
        DELIVERED_TO_CUSTOMER = 'delivered_to_customer', 'Đã giao tới khách hàng'
        CANCELLED = 'cancelled', 'Cancel'
        CANNOT_PRODUCE = 'can_not_produce', 'Không thể sản xuất'
        LACK_OF_PET ='lack_of_pet','chưa có pet'
        WRONG_DESIGN = 'wrong_design','sai design'
        Wrong_MOCKKUP ='wrong_mockkup', 'sai mockup'
        FORWARDED_TO_SUPIFY = 'forwarded_to_supify', 'Đã chuyển tiếp đến xưởng supify',
        SENT_TO_ONOS = 'sent_to_onos','Đã chuyển cho onos'
        FULLFILLED = 'fullfilled','Đã fullfill'
        REFORWARDED_TO_HALL = 'reforwarded_to_hall', 'Đã chuyển lại cho sảnh',


    status = models.CharField(
        max_length=50,
        choices=PackageStatus.choices,
        default=PackageStatus.INIT
    )

  


class ProductPackage(models.Model):
    package = models.ForeignKey(Package, related_name="products", on_delete=models.SET_NULL, null=True)
    variant_id = models.CharField(null=True, blank=True, max_length=500)
    printer_design_front_url = models.CharField(max_length=1000, blank=True, null=True)
    printer_design_back_url = models.CharField(max_length=1000, blank=True, null=True)
    quantity = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=1000, blank=True, null=True)
    mock_up_front_url = models.CharField( max_length=500, null=True)
    mock_up_back_url = models.CharField( max_length=500, null=True)
    color = models.CharField( max_length=500, null=True)
    size = models.CharField( max_length=200, null=True)
    style = models.CharField( max_length=500, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    product_name = models.CharField(max_length=500, null=True)
    sku_custom = models.CharField(null=True, blank=True, max_length=500)
class CustomUserSendPrint(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_code = models.CharField(max_length=1000, blank=True, null=True)


class ErrorCodes(models.Model):
    code = models.CharField(max_length=500)
    message = models.CharField(max_length=500)
    description = models.CharField(max_length=500)


class FlashShipAccount(models.Model):
    user_name = models.CharField(max_length=1000, blank=True, null=True)
    pass_word = models.CharField(max_length=1000, blank=True, null=True)
    group = models.ForeignKey(GroupCustom, related_name="group", on_delete=models.SET_NULL, null=True)


class TemplateDesign(models.Model):
    user = models.ForeignKey(User, related_name="user_template", on_delete=models.SET_NULL, null=True)
    content = JSONField()


class NotiMessage(models.Model):
    type = models.CharField(("type of notification"), max_length=500)
    message = models.TextField(("message for notification"))


class Notification(models.Model):
    user = models.ForeignKey(User, related_name="user_noti", on_delete=models.SET_NULL, null=True)
    shop = models.ForeignKey(Shop, related_name="shop_noti", on_delete=models.SET_NULL, null=True)
    message = models.ForeignKey(NotiMessage, related_name="notification", on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_read = models.BooleanField(("mark as read"), default=False)

    class Meta:
        ordering = ["-created_at"]
        


class ImageFolder(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    user = models.ForeignKey(User, verbose_name=("user_image"), on_delete=models.CASCADE)


class Image(models.Model):
    image_url = models.CharField(max_length=255, null=True, default="")
    folder = models.ForeignKey(
        ImageFolder, on_delete=models.SET_NULL, null=True)
    image_name = models.CharField(max_length=255, null=True, default="no name")

    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.image_name

class CkfVariant(models.Model):
    SHIRT = "SHIRT"
    HOODIE = "HOODIE"
    SWEATSHIRT = "SWEATSHIRT"

    PRODUCT_TYPE_CHOICES = [
        (SHIRT, "Shirt"),
        (HOODIE, "Hoodie"),
        (SWEATSHIRT, "Sweatshirt"),
    ]

    variant_id = models.CharField(max_length=500)
    color = models.CharField(max_length=500)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)

    def __str__(self):
        return f"{self.variant_id} - {self.color} - {self.product_type}"

