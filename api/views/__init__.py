import os
import platform

from django.core.exceptions import ObjectDoesNotExist as ObjectDoesNotExist
from django.db import transaction as transaction
from django.db.models import Q as Q
from django.db.utils import IntegrityError as IntegrityError
from django.forms.models import model_to_dict as model_to_dict
from django.http import FileResponse as FileResponse
from django.http import HttpResponse as HttpResponse
from django.http import JsonResponse as JsonResponse
from django.shortcuts import get_object_or_404 as get_object_or_404
from django.utils.decorators import method_decorator as method_decorator
from django.utils.encoding import force_str as force_str
from django.utils.http import urlsafe_base64_decode as urlsafe_base64_decode
from django.views import View as View
from django.views.decorators.csrf import csrf_exempt as csrf_exempt
from drf_spectacular.utils import OpenApiParameter as OpenApiParameter
from drf_spectacular.utils import extend_schema as extend_schema
from rest_framework import status as status
from rest_framework.generics import ListAPIView as ListAPIView
from rest_framework.pagination import PageNumberPagination as PageNumberPagination
from rest_framework.permissions import AllowAny as AllowAny
from rest_framework.permissions import IsAuthenticated as IsAuthenticated
from rest_framework.response import Response as Response
from rest_framework.views import APIView as APIView

from api.utils import constant

if platform.system() == "Windows":
    dirs_to_setup = [constant.PDF_DIRECTORY_WINDOW, constant.DOWNLOAD_IMAGES_DIR_WINDOW]
else:
    dirs_to_setup = [constant.PDF_DIRECTORY_UNIX, constant.DOWNLOAD_IMAGES_DIR_UNIX]

for dir_to_setup in dirs_to_setup:
    os.makedirs(dir_to_setup, exist_ok=True)
