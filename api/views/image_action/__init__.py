import json

from django.http import JsonResponse
from django.views import View

from api.utils.image_generation.replace_background import remove_background_and_paste
from api.utils.image_generation.genimage_urls import generate_image_url

class ReplaceBackgroundView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            img_url = data.get("img_url")
            success, processed_image_base64 = remove_background_and_paste(img_url)
            if success:
                return JsonResponse({"output_image_base64": processed_image_base64})
            else:
                return JsonResponse({"error": "Failed to process image"}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data"}, status=400)
        
class ImageUploadView(View):
    def post(self, request):
        # Nhận dữ liệu từ yêu cầu JSON
        data = request.body.decode('utf-8')
        image_data = json.loads(data).get('image_data')
        # print("base64",base64_data)
        if not image_data:
            return JsonResponse({'error': 'Không tìm thấy dữ liệu hình ảnh'}, status=400)

        # Gọi hàm để tải lên hình ảnh và nhận URL
        image_url = generate_image_url(image_data)

        if image_url:
            return JsonResponse({'url': image_url}, status=200)
        else:
            return JsonResponse({'error': 'Lỗi tải lên hình ảnh'}, status=500)