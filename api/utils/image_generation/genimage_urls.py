import requests
import base64
from io import BytesIO

# def generate_image_url(base64_data):
#     # Chuyển đổi chuỗi Base64 thành dữ liệu nhị phân
#     image_data = base64.b64decode(base64_data)

#     # Sử dụng BytesIO để tạo tệp nhị phân trong bộ nhớ
#     image_file = BytesIO(image_data)

#     # Thiết lập các tham số cho yêu cầu tải lên
#     url = "https://freeimage.host/json"
#     payload = {
#         'type': 'file',
#         'action': 'upload',
#         'timestamp': '1730125565258',
#         'auth_token': 'd7f21191b562b2015b0d3372a5168582430f1298',
#         'nsfw': '0'
#     }
    
#     # Thiết lập tệp để gửi trong yêu cầu
#     files = [
#         ('source', ('image.png', image_file, 'image/png'))
#     ]

#     headers = {
#         'accept': 'application/json',
#         'accept-language': 'vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5',
#         'origin': 'https://freeimage.host',
#         'referer': 'https://freeimage.host/page/api?lang=en',
#         'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
#     }

#     # Gửi yêu cầu tải lên
#     response = requests.post(url, headers=headers, data=payload, files=files)

#     # Kiểm tra phản hồi và trả về URL
#     if response.status_code == 200:
#         response_data = response.json()
#         if 'image' in response_data and 'image' in response_data['image']:
#             return response_data['image']['image']['url']
#         else:
#             print("Không tìm thấy URL hình ảnh trong phản hồi.")
#             return None
#     else:
#         print(f"Lỗi tải lên hình ảnh: {response.status_code} - {response.text}")
#         return None

def generate_image_url(base64_data):
    # Chuyển đổi chuỗi Base64 thành dữ liệu nhị phân
    image_data = base64.b64decode(base64_data)

    # Sử dụng BytesIO để tạo tệp nhị phân trong bộ nhớ
    image_file = BytesIO(image_data)

    # Thiết lập các tham số cho yêu cầu tải lên
    url = "https://api.imghippo.com/file"
    payload = {
        'browser': 'Chrome',
        'device': 'Android'
    }

    # Thiết lập tệp để gửi trong yêu cầu
    files = [
        ('image', ('image.png', image_file, 'image/png'))
    ]

    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9,vi;q=0.8',
        'authorization': '',
        'origin': 'https://www.imghippo.com',
        'priority': 'u=1, i',
        'referer': 'https://www.imghippo.com/',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
    }

    # Gửi yêu cầu tải lên
    response = requests.post(url, headers=headers, data=payload, files=files)
    print("ressponse", response.text)
    # Kiểm tra phản hồi và trả về URL hình ảnh
    if response.status_code == 200:
        response_data = response.json()
        return response_data['data']['images']
    else:
        print(f"Lỗi tải lên hình ảnh: {response.status_code} - {response.text}")
        return None
