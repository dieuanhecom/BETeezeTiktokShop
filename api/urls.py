from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

import api.views.google_trend as google_trend
import api.views.image_action as image_action
import api.views.media as media
import api.views.combine_label as combine_label
import api.views.csv_to_pdf as csv_to_pdf

# Import các views module
# import api.views.google_trend as google_trend
import api.views.tiktok as tiktok
from api.utils.flashship import flashshipapi

swagger_urls = [
    path("schema", SpectacularAPIView.as_view(), name="schema"),
    path(
        "schema/swagger-ui",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

auth_urls = [
    path("login", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh", TokenRefreshView.as_view(), name="token_refresh"),
    path("signup", tiktok.auth_action.SignUp.as_view(), name="signup"),
    path(
        "verify/<str:uidb64>/<str:token>",
        tiktok.auth_action.Verify.as_view(),
        name="verify",
    ),
]

shop_urls = [
    path("shops", tiktok.shop_action.Shops.as_view(), name="manipulate_shops_info"),
    path(
        "shops/list",
        tiktok.shop_action.ShopList.as_view(),
        name="product_lists_each_user",
    ),
    path(
        "shops/lists",
        tiktok.shop_action.ShopListAPI.as_view(),
        name="product_lists_all_user",
    ),
    path(
        "shops/<int:shop_id>",
        tiktok.shop_action.ShopDetail.as_view(),
        name="shop_put_get_delete",
    ),
    path(
        "shops/<int:shop_id>/refreshtoken",
        tiktok.token_action.RefreshToken.as_view(),
        name="refresh_token",
    ),
    path(
        "shops/<int:shop_id>/products/<int:product_id>",
        tiktok.product_action.ProductDetail.as_view(),
        name="product_detail",
    ),
    path(
        "shops/<int:shop_id>/products/list/page=<int:page_number>",
        tiktok.product_action.ListProduct.as_view(),
        name="product_list",
    ),
    path(
        "shops/<int:shop_id>/categories",
        tiktok.product_action.CategoriesByShopId.as_view(),
        name="categories",
    ),
    path(
        "shops/<int:shop_id>/warehouses",
        tiktok.product_action.WareHouse.as_view(),
        name="wareHouse",
    ),
    path(
        "shops/<int:shop_id>/attributes",
        tiktok.product_action.Attributes.as_view(),
        name="attributes",
    ),
    path(
        "shops/search", tiktok.shop_action.ShopSearchViews.as_view(), name="shop_search"
    ),
    path(
        "shops/<int:shop_id>/upload",
        tiktok.product_action.UploadImage.as_view(),
        name="upload_images",
    ),
    path(
        "shops/upload-image",
        tiktok.product_action.uploadImageToTiktok.as_view(),
        name="upload_tiktok_images",
    ),
    path(
        "shops/upload-image/<int:shop_id>",
        tiktok.product_action.uploadImageToTiktok.as_view(),
        name="upload_tiktok_images",
    ),
    path(
        "shops/<int:shop_id>/brands",
        tiktok.product_action.GetAllBrands.as_view(),
        name="get_brands",
    ),
    path(
        "shops/<int:shop_id>/categories/is_leaf",
        tiktok.product_action.CategoriesIsLeaf.as_view(),
        name="categories_is_leaf",
    ),
    path(
        "shops/<int:shop_id>/products/create_product_excel3",
        tiktok.product_action.ProcessExcel.as_view(),
        name="process_excel_for_batch_create_products",
    ),
    path(
        "shops/<int:shop_id>/products/update_product/<int:product_id>",
        tiktok.product_action.EditProduct.as_view(),
        name="edit_product",
    ),
    path(
        "shops/<int:shop_id>/orders/list",
        tiktok.order_action.ListOrder.as_view(),
        name="order_list",
    ),
    path(
        "shops/<int:shop_id>/orders/detail",
        tiktok.order_action.OrderDetail.as_view(),
        name="order_detail",
    ),
    path(
        "shops/<int:shop_id>/products/create_product",
        tiktok.product_action.CreateOneProduct.as_view(),
        name="create_one_product",
    ),
    path(
        "shops/<int:shop_id>/buy_lebal",
        tiktok.order_action.ShippingLabel.as_view(),
        name="buy_shipping_label",
    ),
    path(
        "shops/<int:shop_id>/categories/<int:category_id>/products/get_attribute",
        tiktok.product_action.GetProductAttribute.as_view(),
        name="get_product_att",
    ),
    path(
        "shops/<int:shop_id>/products/create_product_draf",
        tiktok.product_action.CreateOneProductDraf.as_view(),
        name="create_one_product_draf",
    ),
    path(
        "shops/<int:shop_id>/products/delete_product",
        tiktok.product_action.DeleteProduct.as_view(),
        name="delete_product",
    ),
    #     promotion
    path(
        "shops/<int:shop_id>/promotions",
        tiktok.promotion_action.GetPromotionsView.as_view(),
        name="get_promotions",
    ),
    path(
        "shops/<int:shop_id>/promotions/<int:promotion_id>",
        tiktok.promotion_action.GetPromotionDetailView.as_view(),
        name="get_promotion_detail",
    ),
    path(
        "shops/<int:shop_id>/promotions/create_discount",
        tiktok.promotion_action.AddOrUpdateDiscount.as_view(),
        name="create_promotion_discount",
    ),
    # path("shops/<int:shop_id>/promotions/add_or_update",
    # tiktok.promotion_action.AddOrUpdatePromotion.as_view(), name="add_or_update_promotion"),
    path(
        "shops/<int:shop_id>/promotions/list_unpromotion",
        tiktok.promotion_action.GetAllUnPromotionProduct.as_view(),
        name="list_unpromotion",
    ),
    path(
        "shops/<int:shop_id>/promotions/list_unpromotion_sku",
        tiktok.promotion_action.GetAllUnPromotionSKU.as_view(),
        name="list_unpromotion_sku",
    ),
    path(
        "shops/<int:shop_id>/promotions/create_flashsale",
        tiktok.promotion_action.AddOrUpdateFlashDeal.as_view(),
        name="create_promotion_flashdeal",
    ),
    path(
        "shops/<int:shop_id>/promotions/deactive_promotion",
        tiktok.promotion_action.DeactivePromotion.as_view(),
        name="deactive_promotion",
    ),
    path(
        "shops/<int:shop_id>/promotions/<int:promo_id>/detail_promotion",
        tiktok.promotion_action.DetailPromo.as_view(),
        name="detail_promotion",
    ),
]

template_urls = [
    path(
        "templates", tiktok.template_action.TemplateList.as_view(), name="template_list"
    ),
    path(
        "templates/<int:template_id>",
        tiktok.template_action.TemplateList.as_view(),
        name="template_detail",
    ),
    path(
        "template-design",
        tiktok.template_action.TemplateDesignList.as_view(),
        name="template-design-list",
    ),
    path(
        "template-design/<int:pk>",
        tiktok.template_action.TemplateDesignDetail.as_view(),
        name="template-design-detail",
    ),
    path(
        "template-designlist",
        tiktok.template_action.TemplateDesignLit.as_view(),
        name="template-design-lit",
    ),
]

global_urls = [
    path(
        "categories/global",
        tiktok.product_action.GlobalCategory.as_view(),
        name="global_categories",
    ),
    path(
        "brands/global",
        tiktok.product_action.GlobalBrand.as_view(),
        name="globals_brands",
    ),
]

user_group_urls = [
    path(
        "groups/change_user",
        tiktok.permission_action.PermissionRole.as_view(),
        name="divide_role",
    ),
    path(
        "groups/add_user_group",
        tiktok.permission_action.AddUserToGroup.as_view(),
        name="add_user_to_group",
    ),
    path(
        "groups/user_login_infor",
        tiktok.permission_action.InforUserCurrent.as_view(),
        name="user_current_infor",
    ),
    path(
        "user-shops/groups",
        tiktok.shop_action.UserShopList.as_view(),
        name="user_shops_list",
    ),
    path(
        "user/<int:user_id>/groups/infor",
        tiktok.permission_action.UserInfo.as_view(),
        name="user_group_infor",
    ),
    path(
        "groupcustoms",
        tiktok.permission_action.GroupCustomListAPIView.as_view(),
        name="groupcustom_list",
    ),
    path(
        "groupcustoms/<int:group_id>",
        tiktok.permission_action.GetAllUserGroup.as_view(),
        name="groupcustom_list_user",
    ),
    path(
        "user-shop-all/<int:group_id>",
        tiktok.permission_action.UserShopListAll.as_view(),
        name="user-shop list all",
    ),
]

fulfillment_urls = [
    path(
        "shops/<int:shop_id>/pre_combine_pkg",
        tiktok.order_action.AllCombinePackage.as_view(),
        name="pre_combine_pkg",
    ),
    path(
        "shops/<int:shop_id>/confirm_combine_pkg",
        tiktok.order_action.ConfirmCombinePackage.as_view(),
        name="confirm_combine_pkg",
    ),
    path(
        "shops/<int:shop_id>/category_recommend",
        tiktok.product_action.CategoryRecommend.as_view(),
        name="category_recommend",
    ),
    path(
        "shops/<int:shop_id>/shipping_service",
        tiktok.order_action.ShippingService.as_view(),
        name="shipping_service",
    ),
    path(
        "shops/<int:shop_id>/search_package",
        tiktok.order_action.SearchPackage.as_view(),
        name="search_package",
    ),
    path(
        "shops/<int:shop_id>/packages/package_detail",
        tiktok.order_action.PackageDetail.as_view(),
        name="package_detail",
    ),
    path(
        "shops/get_package_buyed",
        tiktok.order_action.PackageBought.as_view(),
        name="get_all_package_buyed",
    ),
    path("pdf-search/", tiktok.order_action.PDFSearch.as_view(), name="pdf_search"),
    path(
        "pdf-download/", tiktok.order_action.PDFDownload.as_view(), name="pdf_download"
    ),
    path(
        "shops/<int:shop_id>/packages/buy_label",
        tiktok.order_action.CreateLabel.as_view(),
        name="buy_label",
    ),  # oke
    path(
        "shops/<int:shop_id>/get_shipping_doc_package_ids",
        tiktok.order_action.ShippingDoc.as_view(),
        name="get_shipping_doc_package_ids",
    ),  # oke
    path(
        "designskus/",
        tiktok.order_action.DesignSkuListCreateAPIView.as_view(),
        name="designsku-list",
    ),
    path(
        "designskus-page/",
        tiktok.order_action.DesignSkuListCreateAPIViewPage.as_view(),
        name="designsku-list-page",
    ),
    path(
        "designskus/<int:pk>/",
        tiktok.order_action.DesignSkuDetailAPIView.as_view(),
        name="designsku-detail",
    ),
    path(
        "designskus/find_by_group/<int:group_id>",
        tiktok.order_action.DesignSkuDepartment.as_view(),
        name="designsku-find-by-group",
    ),
    path(
        "designskus/find_by_group/all",
        tiktok.order_action.DesignSkuAllDepartment.as_view(),
        name="designsku-find-by-group-all",
    ),
    path(
        "designskus/search",
        tiktok.order_action.DesignSkuSearch.as_view(),
        name="designsku_search",
    ),
    path(
        "flashship/create",
        flashshipapi.SaveVariantDataFromExcel.as_view(),
        name="flashship_create",
    ),
    path(
        "flashship/all",
        flashshipapi.FlashShipPODVariantListView.as_view(),
        name="flashship_getall",
    ),
    path(
        "ckf/all",
        flashshipapi.CkfVariantListView.as_view(),
        name="ckf-variant-list",
    ),
    path(
        "shops/upload_driver",
        tiktok.order_action.UploadDriver.as_view(),
        name="upload_driver",
    ),
    path(
        "shops/<int:shop_id>/orders/to_ship_infor",
        tiktok.order_action.ToShipOrderAPI.as_view(),
        name="to_ship_order",
    ),
    # New endpoint for CSV fulfillment: Validate SKU IDs
    path(
        "csv_fulfillment/validate_skus",
        tiktok.order_action.CsvFulfillmentSkuValidationAPI.as_view(),
        name="csv_fulfillment_validate_skus",
    ),
    # New endpoint for CSV fulfillment: Process PDF with OCR
    path(
        "shops/<int:shop_id>/csv_fulfillment/process_pdf",
        tiktok.order_action.CsvFulfillmentPdfOcrAPI.as_view(),
        name="csv_fulfillment_pdf_ocr",
    ),
    # New endpoint for CSV fulfillment: Process PDF with OCR (without shop_id)
    path(
        "csv_fulfillment/process_pdf",
        tiktok.order_action.CsvFulfillmentPdfOcrAPI.as_view(),
        name="csv_fulfillment_pdf_ocr_no_shop",
    ),
    path(
        "designskus/<str:sku_id>",
        tiktok.order_action.DesignSkuBySkuId.as_view(),
        name="designsku_detail",
    ),
    # New endpoint for CSV fulfillment: Get design SKU by SKU ID
    path(
        "designskus/by_sku_id/<str:sku_id>",
        tiktok.order_action.DesignSkuBySkuId.as_view(),
        name="designsku_by_sku_id",
    ),
    path(
        "shop/<int:shop_id>/packages/create_flash",
        tiktok.order_action.PackageCreateForFlash.as_view(),
        name="package_create_flash_ship",
    ),
    path(
        "shop/<int:shop_id>/packages/create_print",
        tiktok.order_action.PackageCreateForPrint.as_view(),
        name="package_create_prin_care",
    ),
    path(
        "shop/<int:shop_id>/packages/create_ckf",
        tiktok.order_action.PackageCreateForCkf.as_view(),
        name="package_create_prin_ckf",
    ),
    path(
        "shop/<int:shop_id>/packages/create_drop_ship",
        tiktok.order_action.PackageCreateForDropShip.as_view(),
        name="package_create_drop_ship",
    ),
    path(
        "shop/<int:shop_id>/packages/create_teeclub",
        tiktok.order_action.PackageCreateForTeeClub.as_view(),
        name="package_create_prin_teeclub",
    ),
    path(
        "shop/<int:shop_id>/packages/list",
        tiktok.order_action.PackageListByShop.as_view(),
        name="get_list_package",
    ),
    path(
        "flashship/account",
        flashshipapi.FlashShipAccountApi.as_view(),
        name="flashship_account",
    ),
    path(
        "package/<str:pack_id>/deactive",
        tiktok.order_action.DeactivePack.as_view(),
        name="deactive_package",
    ),
    path(
        "pdf-upload-search",
        tiktok.order_action.UploaddriveAndSearchPrintCare.as_view(),
        name="pdf_search_upload",
    ),
    path(
        "shop/<int:shop_id>/orders/cancel",
        tiktok.order_action.CancelOrder.as_view(),
        name="cancel_order",
    ),
]

"""Google Trend"""

google_trend_urls = [
    path(
        "ggtrend/options",
        google_trend.GoogleTrendOptions.as_view(),
        name="ggtrend_options",
    ),
    path(
        "ggtrend/query",
        google_trend.QueryGoogleTrend.as_view(),
        name="ggtrend_query",
    ),
]

image_process_urls = [
    path(
        "crawl/process_image",
        image_action.ReplaceBackgroundView.as_view(),
        name="crawl_process_image",
    ),
     path('upload-image', image_action.ImageUploadView.as_view(), name='upload_imagewwww'),
]
web_hook_url = [
    path(
        "tokens/refresh-shopId",
        tiktok.token_action.RefreshTokenAuthorizedShop.as_view(),
        name="refreshtoken-getshopid-author",
    ),
    path(
        "webhook/get-order-status",
        tiktok.webhook_action.WebhookDataView.as_view(),
        name="get-order-status",
    ),
    path(
        "webhook/view-noti-order",
        tiktok.webhook_action.ViewNotiForOrder.as_view(),
        name="view-noti-order",
    ),
    path(
        "webhook/mark-as-read",
        tiktok.webhook_action.MaskAsReadNoti.as_view(),
        name="mark-as-read-noti",
    ),
]
media_image = [
    path(
        "folder-images",
        media.ImageFolderListCreateAPIView.as_view(),
        name="getlist and post folder images parent",
    ),
    path(
        "folder-images/<int:id>",
        media.SubfoldersListAPIView.as_view(),
        name="getlist and post sub-folder images ",
    ),
    path(
        "folder-images/<int:pk>/",
        media.ImageFolderRetrieveUpdateDestroyAPIView.as_view(),
        name="image-folder-detail",
    ),
    path(
        "upload-folder-images/<int:folder_id>",
        media.UploadImageIntoFolder.as_view(),
        name="post image into folder",
    ),
    path(
        "get-all-folder/<int:id>",
        media.GetImageAndSubFolder.as_view(),
        name="get all image and folder",
    ),
]

order_urls = [
    path(
        "orders",
        tiktok.order_action.ListOrderAPI.ListOderOfUserView.as_view(),
        name="list_order_of_user",
    ),
]
crawl_url = [
    path(
        "crawl-insta",
        media.GetInstagramData.as_view(),
        name="get_insta_infor"
)
]

statistics_urls = [
    path(
        "statistics/orders",
        tiktok.statistics_action.FinanceApi.StatisticsApi.as_view(),
        name="get_order_statistics",
    ),
    path(
        "statistics/finance",
        tiktok.statistics_action.FinanceApi.StatisticsFinanceApi.as_view(),
        name="get_finance_statistics",
    ),
]
packages = [
    path('packages/filter', tiktok.order_action.PackageFilter.as_view(), name='get_packages'),
    path('update-tracking/<int:shop_id>/',  tiktok.order_action.UpdateTrackingInfor.as_view(), name='update_tracking_info'),
    path('product-package/<int:pk>/update/', tiktok.order_action.ProductPackageUpdateView.as_view(), name='update-product-package'),
    path('package/<int:pk>/update-status/', tiktok.order_action.UpdatePackageStatusView.as_view(), name='update-package-status'),
    path('package/<int:pk>/update-fulfillment-name/', tiktok.order_action.UpdateFulfillmentNameView.as_view(), name='update-fulfillment-name'),
    path('package-max/', tiktok.order_action.GetNumbersortMax.as_view(), name='get max number sort' )
]

affiliate_urls = [
    path('affiliate/search-seller-creators', tiktok.affiliate_action.SearchSellerCreators.as_view(), name='search-seller-creators'),
]

combine_label_urls = [
    path('combine-label/', combine_label.CombineLabelAPI.as_view({
        'post': 'create',
        'get': 'list'
    }), name='combine-label'),
    path('combine-label/<int:pk>/', combine_label.CombineLabelAPI.as_view({
        'get': 'retrieve'
    }), name='combine-label-detail'),
    path('combine-label/<int:pk>/cancel/', combine_label.CombineLabelAPI.as_view({
        'post': 'cancel'
    }), name='combine-label-cancel'),
]

csv_to_pdf_urls = [
    path('csv-to-pdf', csv_to_pdf.CsvToPdfGeneratorAPI.as_view(), name='csv-to-pdf'),
]

# Tách URLs ra thành các nhóm URLs nhỏ để dễ quản lý
urlpatterns = (
    swagger_urls
    + auth_urls
    + shop_urls
    + template_urls
    + global_urls
    + user_group_urls
    + fulfillment_urls
    + google_trend_urls
    + image_process_urls
    + web_hook_url
    + media_image
    + order_urls
    + statistics_urls
    + crawl_url
    + packages
    + affiliate_urls
    + combine_label_urls
    + csv_to_pdf_urls
)
