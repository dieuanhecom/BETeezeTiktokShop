from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.viewsets import ViewSet
from django.utils import timezone
from api.models import CombineLabelTask
from api.serializers import CombineLabelTaskSerializer
import logging

# Import Celery app để đảm bảo tasks được register
from tiktok.celery import app
from api.tasks import process_combine_label_task

logger = logging.getLogger(__name__)

class CombineLabelAPI(ViewSet):
    """
    API endpoints cho Combine Label với background processing
    """
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        """
        POST /api/combine-label/
        Tạo task mới và trả về ngay lập tức
        """
        try:
            urls = request.data.get('urls', [])
            
            if not urls:
                return Response({
                    'success': False,
                    'message': 'No URLs provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Tạo record trong database
            task = CombineLabelTask.objects.create(
                user=request.user,
                urls=urls,
                total_urls=len(urls),
                status='PENDING'
            )
            
            # Trigger background task
            try:
                # Import task trực tiếp để đảm bảo được register
                from api.tasks import process_combine_label_task
                process_combine_label_task.delay(task.id)
            except Exception as celery_error:
                logger.error(f"Celery task error: {str(celery_error)}")
                # Tạm thời: nếu Celery fail, vẫn tạo task với status PENDING
                # User có thể check lại sau khi Celery được fix
                task.status = 'PENDING'
                task.error_message = f"Background task will be processed later. Error: {str(celery_error)}"
                task.save()
            
            return Response({
                'success': True,
                'data': {
                    'task_id': task.id,
                    'status': task.status,
                    'total_urls': task.total_urls,
                    'created_at': task.created_at
                },
                'message': f'Task created successfully. Processing {len(urls)} URLs in background.'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error creating combine label task: {str(e)}")
            return Response({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def list(self, request):
        """
        GET /api/combine-label/
        Lấy danh sách tasks của user
        """
        try:
            tasks = CombineLabelTask.objects.filter(user=request.user)
            serializer = CombineLabelTaskSerializer(tasks, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error fetching combine label tasks: {str(e)}")
            return Response({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def retrieve(self, request, pk=None):
        """
        GET /api/combine-label/{task_id}/
        Lấy chi tiết task
        """
        try:
            task = CombineLabelTask.objects.get(id=pk, user=request.user)
            serializer = CombineLabelTaskSerializer(task)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
            
        except CombineLabelTask.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching combine label task {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        POST /api/combine-label/{task_id}/cancel/
        Hủy task (chỉ khi đang PENDING)
        """
        try:
            task = CombineLabelTask.objects.get(id=pk, user=request.user)
            
            if task.status != 'PENDING':
                return Response({
                    'success': False,
                    'message': 'Can only cancel pending tasks'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            task.status = 'CANCELLED'
            task.completed_at = timezone.now()
            task.save()
            
            return Response({
                'success': True,
                'message': 'Task cancelled successfully'
            }, status=status.HTTP_200_OK)
            
        except CombineLabelTask.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Task not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error cancelling combine label task {pk}: {str(e)}")
            return Response({
                'success': False,
                'message': f'Internal server error: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)