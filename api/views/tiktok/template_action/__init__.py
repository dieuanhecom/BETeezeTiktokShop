import logging

from django.http import Http404

from api import setup_logging
from api.views import APIView, IsAuthenticated, Response, csrf_exempt, get_object_or_404, method_decorator, status

from ....models import TemplateDesign, Templates
from ....serializers import TemplateDesignSerializer, TemplatePutSerializer, TemplateSerializer
from datetime import datetime
from collections import OrderedDict
logger = logging.getLogger("api.views.tiktok.template")
setup_logging(logger, is_root=False, level=logging.INFO)


@method_decorator(csrf_exempt, name="dispatch")
class TemplateList(APIView):  # đổi tên thành TemplateList
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = self.request.user
        template_type = request.query_params.get('templateType', '')

        if template_type.lower() == 'custom':
            templates = Templates.objects.filter(
                user=user, templateType='custom')
        elif template_type.lower() == 'all':
            templates = Templates.objects.filter(user=user)
        else:
            templates = Templates.objects.filter(
                user=user).exclude(templateType='custom')
        serializer = TemplateSerializer(templates, many=True)

        return Response(serializer.data)

    def post(self, request):
        template = Templates.objects.create(
            attributes=request.data.get("attributes", []),
            size_chart_url=request.data.get("size_chart_url", ""),
            fixed_image_urls=request.data.get("fixed_image_urls", []),
            name=request.data.get("name"),
            category_id=request.data.get("category_id"),
            description=request.data.get("description"),
            is_cod_open=request.data.get("is_cod_open"),
            package_height=request.data.get("package_height"),
            package_length=request.data.get("package_length"),
            package_weight=request.data.get("package_weight"),
            package_width=request.data.get("package_width"),
            sizes=request.data.get("sizes"),
            colors=request.data.get("colors"),
            type=request.data.get("type"),
            types=request.data.get("types"),
            option1=request.data.get("option1"),
            option2=request.data.get("option2"),
            option3=request.data.get("option3"),
            user=self.request.user,
            badWords=request.data.get("badWords"),
            suffixTitle=request.data.get("suffixTitle"),
            size_chart=request.data.get("size_chart", ""),
            fixed_images=request.data.get("fixed_images", []),
            images_link_variant=request.data.get("images_link_variant", []),
            templateType=request.data.get("templateType", None),
            customTemplateData=request.data.get("customTemplateData", None),
        )
        template.save()
        return Response({"message": "Template created successfully"}, status=status.HTTP_201_CREATED)

    def put(self, request, template_id):
        # Get the template object or return a 404 if not found
        template = get_object_or_404(Templates, id=template_id)

        # Clear the existing values of fields before updating
        template.sizes = []
        template.colors = []
        template.option1 = []
        template.option2 = []
        template.option3 = []
        template.types = []
        template.badWords = None
        template.suffixTitle = None
        template.size_chart = None
        template.fixed_images = []
        template.images_link_variant = []
        template.attributes = []
        template.fixed_image_urls = []
        template.size_chart_url = None

        # Save the cleared fields before applying new data
        template.save()

        # Adjust incoming request data for fields with empty values
        if request.data.get("suffixTitle", "") == "":
            request.data["suffixTitle"] = None
        if request.data.get("badWords", []) == []:
            request.data["badWords"] = None
        if request.data.get("size_chart", "") == "":
            request.data["size_chart"] = None
        if request.data.get("fixed_images", []) == []:
            request.data["fixed_images"] = None
        if request.data.get("images_link_variant", []) == None:
            request.data["images_link_variant"] = []
        if request.data.get("attributes", []) == []:
            request.data["attributes"] = None
        if request.data.get("fixed_image_urls", []) == []:
            request.data["fixed_image_urls"] = None
        if request.data.get("size_chart_url", "") == "":
            request.data["size_chart_url"] = None

        # Serialize and validate the updated data
        template_serializer = TemplatePutSerializer(template, data=request.data)
        if template_serializer.is_valid():
            template_serializer.save()
            return Response(template_serializer.data, status=200)
        else:
            return Response(template_serializer.errors, status=400)

    def delete(self, request, template_id):
        template = get_object_or_404(Templates, id=template_id)
        try:
            template.delete()
            return Response({"message": "Template deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error("Failed to delete template", exc_info=e)
            return Response(
                {"status": "error", "message": f"Có lỗi xảy ra khi xóa template: {str(e)}", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class TemplateDesignList(APIView):
    # permission_classes = (IsAuthenticated,)

    def get(self, request):
        template_designs = TemplateDesign.objects.filter(user=request.user)
        serializer = TemplateDesignSerializer(template_designs, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        data = request.data.copy()
        data["user"] = user.id

        serializer = TemplateDesignSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TemplateDesignDetail(APIView):
    # permission_classes = (IsAuthenticated,)

    def get_object(self, pk):
        try:
            return TemplateDesign.objects.get(pk=pk)
        except TemplateDesign.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        template_design = self.get_object(pk)
        serializer = TemplateDesignSerializer(template_design)
        return Response(serializer.data)

    def put(self, request, pk):
        template_design = self.get_object(pk)
        serializer = TemplateDesignSerializer(template_design, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, pk):
        data = request.data.copy()
        data["user"] = 2

        serializer = TemplateDesignSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        template_design = self.get_object(pk)
        template_design.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplateDesignLit(APIView):

    def get(self, request):
        username = request.query_params.get('username')
        days = int(request.query_params.get('days', 7))
        templates = TemplateDesign.objects.filter(content__userName=username)

        template_data = list(templates.values('content'))

        grouped_data = {}
        for item in template_data:
            date = datetime.strptime(
                item['content']['time'], '%Y-%m-%dT%H:%M:%S.%fZ').date()
            date_str = date.strftime('%Y-%m-%d')
            if date_str not in grouped_data:
                grouped_data[date_str] = item
            else:
                grouped_data[date_str]['content']['products'].extend(
                    item['content']['products'])

        # Sort the dictionary by date in descending order and keep only the first 7 items
        sorted_data = OrderedDict(
            sorted(grouped_data.items(), key=lambda x: x[0], reverse=True)[:days])

        return Response(list(sorted_data.values()))
