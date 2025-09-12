from django.contrib import admin

from api.models import Categories

from .models import (
    Brand,
    BuyedPackage,
    CustomUser,
    CustomUserSendPrint,
    DesignSku,
    DesignSkuChangeHistory,
    ErrorCodes,
    FlashShipAccount,
    FlashShipPODVariantList,
    GroupCustom,
    Image,
    Package,
    Products,
    Shop,
    Templates,
    UserGroup,
    UserShop,
    CkfVariant,
    ProductPackage
)


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("shop_code", "shop_name", "access_token", "refresh_token", "auth_code", "grant_type", "is_active","shop_description")
    search_fields = ("shop_code", "shop_name", "access_token", "refresh_token", "auth_code", "grant_type", "is_active","shop_description")
    list_filter = ("is_active",)


@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ("shop_id", "data")
    search_fields = ("shop__shop_id", "data")


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("user", "verify_token")
    search_fields = ("user", "verify_token")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("image_url","folder")
    search_fields = ("image_url", "folder")


@admin.register(Templates)
class TemplateAdmin(admin.ModelAdmin):
    list_display = (
        "user",
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
        "types",
        "option1",
        "option2",
        "option3",
        "fixed_images",
    )
    search_fields = (
        "user",
        "name",
        "category_id",
        "warehouse_id",
        "description",
        "is_cod_open",
        "package_height",
        "package_length",
        "package_weight",
        "package_width",
        "sizes",
        "colors",
        "type",
        "types",
        "option1",
        "option2",
        "option3",
        "fixed_images",
    )


class CategoriesAdmin(admin.ModelAdmin):
    # Cấu hình hiển thị và tìm kiếm cho mô hình Categories
    list_display = (
        "id",
        "data",
    )  # Thay thế 'id' bằng các trường bạn muốn hiển thị
    search_fields = ("id", "data")  # Thêm các trường bạn muốn tìm kiếm


class UserGroupAdmin(admin.ModelAdmin):
    # Cấu hình hiển thị và tìm kiếm cho mô hình UserGroup
    list_display = (
        "id",
        "user",
        "get_group_name",
        "role",
    )  # Thay thế 'id', 'user', 'role' bằng các trường bạn muốn hiển thị
    search_fields = (
        "id",
        "user__username",
        "group_custom__group_name",
        "role",
    )  # Thêm các trường bạn muốn tìm kiếm

    def get_group_name(self, obj):
        return obj.group_custom.group_name

    get_group_name.short_description = "Group Name"


class GroupCustomAdmin(admin.ModelAdmin):
    # Cấu hình hiển thị và tìm kiếm cho mô hình GroupCustom
    list_display = (
        "id",
        "group_name",
    )  # Thay thế 'id', 'group_name' bằng các trường bạn muốn hiển thị
    search_fields = ("id", "group_name")  # Thêm các trường bạn muốn tìm kiếm


class BrandAdmin(admin.ModelAdmin):
    # Cấu hình hiển thị và tìm kiếm cho mô hình Brand
    list_display = (
        "id",
        "data",
    )  # Thay thế 'id' bằng các trường bạn muốn hiển thị
    search_fields = ("id", "data")  # Thêm các trường bạn muốn tìm kiếm


class UserShopAdmin(admin.ModelAdmin):
    # Cấu hình hiển thị và tìm kiếm cho mô hình UserShop
    list_display = (
        "id",
        "user",
        "get_shop_name",
    )  # Thay thế 'id', 'user' bằng các trường bạn muốn hiển thị
    search_fields = (
        "id",
        "user__username",
        "shop__shop_name",
    )  # Thêm các trường bạn muốn tìm kiếm

    def get_shop_name(self, obj):
        return obj.shop.shop_name

    get_shop_name.short_description = "Shop Name"


class DesignSkuAdmin(admin.ModelAdmin):
    list_display = (
        "sku_id",
        "product_name",
        "variation",
        "image_front",
        "image_back",
        "user",
        "department",
        "mockup_front",
        "mockup_back",
    )


class DesignSkuChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ("design_sku", "user", "changed_at")
    list_filter = ("user", "changed_at")
    search_fields = ("design_sku__sku", "user__username")
    readonly_fields = ("design_sku", "user", "change_data", "changed_at")


class FlashShipPODVariantListAdmin(admin.ModelAdmin):
    list_display = ("variant_id", "color", "size", "product_type")
    list_filter = ("product_type",)
    search_fields = ("variant_id", "color", "size")


@admin.register(ErrorCodes)
class ErrorCodesAdmin(admin.ModelAdmin):
    list_display = ("code", "message", "description")
    search_fields = ("code", "message")


admin.site.register(FlashShipPODVariantList, FlashShipPODVariantListAdmin)
admin.site.register(Categories, CategoriesAdmin)
admin.site.register(UserGroup, UserGroupAdmin)
admin.site.register(GroupCustom, GroupCustomAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(UserShop, UserShopAdmin)
admin.site.register(BuyedPackage)
admin.site.register(DesignSku, DesignSkuAdmin)
admin.site.register(DesignSkuChangeHistory, DesignSkuChangeHistoryAdmin)
admin.site.register(CustomUserSendPrint)
admin.site.register(FlashShipAccount)

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "order_id", 
        "pack_id", 
        "buyer_first_name", 
        "buyer_last_name", 
        "buyer_email", 
        "get_status_display",  # Hiển thị nhãn trạng thái thân thiện
        "tracking_id"
    )
    list_filter = ("status", "package_status")  # Bộ lọc theo trạng thái
    search_fields = ("order_id", "buyer_email", "tracking_id") 

@admin.register(CkfVariant)
class  CkfVariantAdmin(admin.ModelAdmin):
    list_display = ['variant_id', 'color', 'product_type']

# @admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status')  # Các trường sẽ hiển thị trong danh sách
    search_fields = ('name',)  # Thêm tìm kiếm theo tên
    list_filter = ('status',)  # Thêm bộ lọc theo trạng thái
    ordering = ('name',)  # Sắp xếp theo tên

    # Nếu bạn muốn tùy chỉnh form hiển thị, bạn có thể thêm thêm hàm này
    def get_readonly_fields(self, request, obj=None):
        # Thay đổi trường không thể chỉnh sửa nếu cần thiết
        return super().get_readonly_fields(request, obj)
class ProductPackageAdmin(admin.ModelAdmin):
    # Các trường hiển thị trong trang danh sách admin
    list_display = ('package', 'variant_id', 'quantity', 'note', 'printer_design_front_url', 'printer_design_back_url',"mock_up_front_url","mock_up_back_url","color","size","style","product_name","sku_custom")

    # Các trường có thể tìm kiếm trong trang admin
    search_fields = ('variant_id', 'note')

    # Thêm các bộ lọc bên cạnh các trường trong admin
    list_filter = ('quantity', 'note')

    # Cho phép chỉnh sửa nhanh trên trang danh sách admin
    list_editable = ('quantity', 'note')

    # Cho phép chỉnh sửa trực tiếp các trường trong form admin
    fieldsets = (
        (None, {
            'fields': ('package', 'variant_id', 'printer_design_front_url', 'printer_design_back_url',"mock_up_front_url","mock_up_back_url","color","size","style","product_name","sku_custom")
        }),
        ('Quantity & Notes', {
            'fields': ('quantity', 'note')
        }),
    )

    # Để hạn chế các trường hiển thị khi tạo hoặc chỉnh sửa
    readonly_fields = ('package', 'variant_id')  # Chỉ đọc, không cho phép sửa

# Đăng ký admin model vào Django admin
admin.site.register(ProductPackage, ProductPackageAdmin)