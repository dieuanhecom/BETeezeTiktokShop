import logging
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from io import BytesIO
from PyPDF2 import PdfMerger

from api.utils.pdf.generate_pdf import generate_pdf_for_order
from api.utils.pdf.merge_pdf import merge_pdf_files
from api.utils.google.googleapi import GoogleDriveService

logger = logging.getLogger(__name__)

class CsvToPdfGeneratorAPI(APIView):
    """
    API endpoint for generating PDF from CSV data
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
        POST /api/csv-to-pdf/
        Body: {
            "csv_data": [
                {
                    "lo": "1312",
                    "ngay": "17/12/2024",
                    "stt": "599",
                    "soLuongAo": "1/2",
                    "maTracking": "9400109106029356615197",
                    "loaiAo": "Thun - Wash",
                    "mau": "Đen",
                    "size": "S",
                    "anh": "https://example.com/image.jpg"
                }
            ]
        }
        """
        try:
            csv_data = request.data.get('csv_data', [])
            
            if not csv_data:
                return Response({
                    'success': False,
                    'message': 'No CSV data provided'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if not isinstance(csv_data, list):
                return Response({
                    'success': False,
                    'message': 'CSV data must be a list'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info(f"Starting PDF generation for {len(csv_data)} orders")
            
            # Generate PDF for each order
            pdf_pages = []
            successful_pages = 0
            failed_pages = 0
            failed_rows = []
            
            for index, order_data in enumerate(csv_data):
                try:
                    logger.info(f"Generating PDF for order {index + 1}/{len(csv_data)}")
                    
                    # Generate PDF for this order
                    pdf_buffer = generate_pdf_for_order(order_data)
                    pdf_pages.append(pdf_buffer)
                    successful_pages += 1
                    
                except Exception as e:
                    logger.error(f"Failed to generate PDF for order {index + 1}: {str(e)}")
                    failed_pages += 1
                    failed_rows.append({
                        'index': index + 1,
                        'error': str(e),
                        'data': order_data
                    })
            
            if not pdf_pages:
                return Response({
                    'success': False,
                    'message': 'No PDFs were generated successfully',
                    'data': {
                        'total_rows': len(csv_data),
                        'successful_pages': 0,
                        'failed_pages': failed_pages,
                        'failed_rows': failed_rows
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Merge all PDF pages
            logger.info(f"Merging {len(pdf_pages)} PDF pages")
            merged_pdf = self.merge_pdf_pages(pdf_pages)
            
            if not merged_pdf:
                return Response({
                    'success': False,
                    'message': 'Failed to merge PDF pages',
                    'data': {
                        'total_rows': len(csv_data),
                        'successful_pages': successful_pages,
                        'failed_pages': failed_pages,
                        'failed_rows': failed_rows
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Upload to Google Drive
            filename = f"order_labels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            upload_result = GoogleDriveService().upload_pdf_to_drive(
                merged_pdf, filename
            )
            
            if not upload_result['success']:
                return Response({
                    'success': False,
                    'message': f'Failed to upload PDF: {upload_result["error"]}',
                    'data': {
                        'total_rows': len(csv_data),
                        'successful_pages': successful_pages,
                        'failed_pages': failed_pages,
                        'failed_rows': failed_rows
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            logger.info(f"Successfully generated and uploaded PDF with {successful_pages} pages")
            
            return Response({
                'success': True,
                'message': f'Generated {successful_pages} PDF pages successfully',
                'data': {
                    'drive_link': upload_result['link'],
                    'total_pages': successful_pages,
                    'filename': filename,
                    'processing_details': {
                        'total_rows': len(csv_data),
                        'successful_pages': successful_pages,
                        'failed_pages': failed_pages,
                        'failed_rows': failed_rows
                    }
                }
            })
            
        except Exception as e:
            logger.error(f"Error in CSV to PDF generation: {str(e)}")
            return Response({
                'success': False,
                'message': f'Error generating PDF: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def merge_pdf_pages(self, pdf_pages):
        """
        Merge multiple PDF pages into one document
        
        Args:
            pdf_pages (list): List of PDF buffers
            
        Returns:
            BytesIO: Merged PDF buffer or None if failed
        """
        try:
            merger = PdfMerger()
            
            for pdf_buffer in pdf_pages:
                pdf_buffer.seek(0)
                merger.append(pdf_buffer)
            
            merged_buffer = BytesIO()
            merger.write(merged_buffer)
            merger.close()
            
            merged_buffer.seek(0)
            return merged_buffer
            
        except Exception as e:
            logger.error(f"Failed to merge PDF pages: {str(e)}")
            return None 