import json
from concurrent.futures import ThreadPoolExecutor

from django.core.paginator import Paginator
from django.http import Http404
from django.http import JsonResponse as JsonResponse
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated as IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Image, ImageFolder, Shop
from api.serializers import ImageFolderSerializer, ImageSerializer, NestedImageFolderSerializer
from api.utils.tiktok_base_api import product
from api.utils.instagram import instagram

# parent folder
class ImageFolderListCreateAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    # get all folder parent
    def get(self, request):
        user = request.user
        folders = ImageFolder.objects.filter(user=user, parent=None)
        serializer = ImageFolderSerializer(folders, many=True)
        return Response(serializer.data)

    # post folder parent
    def post(self, request):
        data = json.loads(request.body.decode("utf-8"))

        serializer = ImageFolderSerializer(data=data)

        if serializer.is_valid():
            user = request.user
            name = data.get("name")
            new_folder = ImageFolder.objects.create(user=user, name=name)
            return Response(ImageFolderSerializer(new_folder).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SubfoldersListAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        user = request.user
        try:
            parent_folder = ImageFolder.objects.get(id=id, user=user)
        except ImageFolder.DoesNotExist:
            return Response({"error": "Parent folder does not exist"}, status=status.HTTP_404_NOT_FOUND)

        subfolders = parent_folder.children.all()
        serializer = ImageFolderSerializer(subfolders, many=True)
        return Response(serializer.data)

    def post(self, request, id):
        user = request.user
        data = json.loads(request.body.decode("utf-8"))
        try:
            parent_folder = ImageFolder.objects.get(id=id, user=user)
        except ImageFolder.DoesNotExist:
            return Response({"error": "Parent folder does not exist"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ImageFolderSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=user, parent=parent_folder, name=data.get("name"))
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ImageFolderRetrieveUpdateDestroyAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return ImageFolder.objects.get(pk=pk)
        except ImageFolder.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        folder = self.get_object(pk)
        serializer = ImageFolderSerializer(folder)
        return Response(serializer.data)

    def put(self, request, pk):
        folder = self.get_object(pk)
        serializer = ImageFolderSerializer(folder, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        folder = self.get_object(pk)
        folder.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UploadImageIntoFolder(APIView):
    permission_classes = (IsAuthenticated,)

    def upload_images(self, image_datas, access_token):
        images_info = []

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(product.callUploadImage, access_token, img_data["base_64"]) for img_data in image_datas
            ]

            for idx, future in enumerate(futures):
                img_id = future.result()

                if img_id:
                    images_info.append({"name": image_datas[idx]["name"], "img_id": img_id})

        return images_info

    def post(self, request, folder_id):
        shop = Shop.objects.get(shop_name__icontains="mediaseller")
        if not shop:
            return JsonResponse({"message": "Shop not found"}, status=status.HTTP_404_NOT_FOUND)

        data = json.loads(request.body.decode("utf-8"))
        image_datas = data.get("image_data")

        if not folder_id:
            return JsonResponse({"message": "Folder ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            folder = ImageFolder.objects.get(id=folder_id)
        except ImageFolder.DoesNotExist:
            return JsonResponse({"message": "Folder not found"}, status=status.HTTP_404_NOT_FOUND)

        access_token = shop.access_token
        after_image_data = self.upload_images(image_datas=image_datas, access_token=access_token)

        for image_res in after_image_data:
            image_res["img_id"] = (
                f"https://p16-oec-ttp.tiktokcdn-us.com/{image_res['img_id']}~tplv-omjb5zjo8w-origin-jpeg.jpeg"
            )

        if folder:
            for data in after_image_data:
                image_create = Image.objects.create(
                    image_url=data["img_id"], image_name=data["name"], folder=folder, created_at=timezone.now()
                )
            print("time", timezone.now())

        response = {"images": after_image_data, "message": "success"}
        return JsonResponse(response)


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Adjust the page size as needed
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return super().get_paginated_response(data)


class GetImageAndSubFolder(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, id):
        user = request.user
        try:
            parent_folder = ImageFolder.objects.get(id=id, user=user)
        except ImageFolder.DoesNotExist:
            return Response({"error": "Parent folder does not exist"}, status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        name = request.query_params.get("image_name")

        images = Image.objects.filter(folder=parent_folder).order_by("-created_at")

        if start_date:
            images = images.filter(created_at__gte=start_date)
        if end_date:
            images = images.filter(created_at__lte=end_date)
        if name:
            images = images.filter(image_name__icontains=name)

        paginator = CustomPageNumberPagination()
        page_obj = paginator.paginate_queryset(images, request)

        serialized_images = [
            {"id": image.id, "image_url": image.image_url, "image_name": image.image_name} for image in page_obj
        ]
        next_page = paginator.get_next_link()
        response = {
            "data": {
                "images": serialized_images,
                "page_number": paginator.page.number,
                "total_pages": paginator.page.paginator.num_pages,
                "has_next_page": paginator.page.has_next(),
                "has_previous_page": paginator.page.has_previous(),
                "next_page": next_page,
            },
            "message": "success",
        }

        return paginator.get_paginated_response(response)

class GetInstagramData(APIView):
    # permission_classes = (IsAuthenticated,)

    def get(self, request):
        username = request.query_params.get('username')  # Extract from query params
        if not username:
            return JsonResponse({"message": "Username query parameter missing"}, status=status.HTTP_400_BAD_REQUEST)

        data = instagram.scrape_user_insta(username)
        if data:
            return Response({"data": data, "message": "success"}, status=status.HTTP_200_OK)
        
        return JsonResponse({"message": "Data not found"}, status=status.HTTP_404_NOT_FOUND)