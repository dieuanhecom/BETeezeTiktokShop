import logging
import requests
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import tempfile
import os

logger = logging.getLogger(__name__)

def encode_vietnamese_text(text):
    """
    Ensure Vietnamese text is properly encoded for PDF generation
    
    Args:
        text (str): Vietnamese text
        
    Returns:
        str: Properly encoded text
    """
    if not text:
        return ''
    
    # Common encoding fixes for Vietnamese characters
    encoding_fixes = {
        'Sá»': 'So',
        'thá»©': 'thu', 
        'tá»±': 'tu',
        'Loáº¡i': 'Loai',
        'Ã¡o': 'ao',
        'MÃ u': 'Mau',
        'sáº¯c': 'sac',
        'KÃ­ch': 'Kich',
        'thÆ°á»›c': 'thuoc',
        'Lng': 'Luong',
        'Loi': 'Loai',
        'S■': 'So',
        'Áo': 'Ao',
        'Số': 'So',
        'Lượng': 'Luong',
        'Loại': 'Loai',
        'Màu': 'Mau',
        'Áo': 'Ao'
    }
    
    result = text
    for encoded, decoded in encoding_fixes.items():
        if encoded in result:
            logger.info(f"Encoding fix: '{encoded}' -> '{decoded}' in text: '{text}'")
        result = result.replace(encoded, decoded)
    
    if result != text:
        logger.info(f"Text encoded: '{text}' -> '{result}'")
    
    return result

def download_image(url, timeout=30):
    """
    Download image from URL with timeout
    
    Args:
        url (str): Image URL
        timeout (int): Request timeout in seconds
        
    Returns:
        bytes: Image data or None if failed
    """
    try:
        # Add headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, timeout=timeout, stream=True, headers=headers)
        response.raise_for_status()
        
        # Read image data
        image_data = response.content
        
        # Validate it's actually an image
        try:
            Image.open(BytesIO(image_data))
            return image_data
        except Exception as e:
            logger.warning(f"Invalid image data from {url}: {str(e)}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to download image from {url}: {str(e)}")
        return None

def optimize_image(image_data, max_size=(800, 600)):
    """
    Optimize image for PDF generation
    
    Args:
        image_data (bytes): Original image data
        max_size (tuple): Maximum width and height
        
    Returns:
        bytes: Optimized image data
    """
    try:
        # Open image
        img = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save optimized image
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Failed to optimize image: {str(e)}")
        return image_data

def generate_pdf_from_data(order_data):
    """
    Generate PDF from order data using ReportLab
    
    Args:
        order_data (dict): Order data
        
    Returns:
        BytesIO: PDF buffer
    """
    try:
        pdf_buffer = BytesIO()
        # Reduce margins to maximize content area
        doc = SimpleDocTemplate(
            pdf_buffer, 
            pagesize=A5,
            leftMargin=10,
            rightMargin=10,
            topMargin=5,    # Reduced from default ~72pt to 5pt
            bottomMargin=10
        )
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Use default font but ensure proper encoding
        vietnamese_font = 'Helvetica'
        
        # No spacing at the top - table starts immediately
        # story.append(Spacer(1, 5))  # Commented out for maximum top positioning
        
        # Create table data with proper Vietnamese text encoding
        table_data = [
            ['Field', 'Value'],
            ['Lo', encode_vietnamese_text(order_data.get('lo', ''))],
            ['Ngay', encode_vietnamese_text(order_data.get('ngay', ''))],
            ['STT', encode_vietnamese_text(order_data.get('stt', ''))],
            ['So Luong Ao', encode_vietnamese_text(order_data.get('soLuongAo', ''))],
            ['Ma tracking', encode_vietnamese_text(order_data.get('maTracking', ''))],
            ['Loai Ao', encode_vietnamese_text(order_data.get('loaiAo', ''))],
            ['Loai Pet', encode_vietnamese_text(order_data.get('loaiPet', ''))],
            ['Mau', encode_vietnamese_text(order_data.get('mau', ''))],
            ['Size', encode_vietnamese_text(order_data.get('size', ''))],
        ]
        
        # Debug log for table data
        logger.info("Table data for PDF generation:")
        for i, row in enumerate(table_data):
            logger.info(f"Row {i}: {row}")
        
        # Debug page dimensions
        logger.info(f"A5 page size: {A5}")
        logger.info(f"Document margins: left={doc.leftMargin}, right={doc.rightMargin}, top={doc.topMargin}, bottom={doc.bottomMargin}")
        logger.info(f"Content area: width={doc.width}, height={doc.height}")
        
        # Create table optimized for A5 with Vietnamese font support
        table = Table(table_data, colWidths=[1.5*inch, 3.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), f'{vietnamese_font}-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), vietnamese_font),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Make specific fields bold (Loại Áo, Loại Pet, Màu, and Size)
            ('FONTNAME', (1, 6), (1, 6), f'{vietnamese_font}-Bold'),  # Loại Áo value
            ('FONTNAME', (1, 7), (1, 7), f'{vietnamese_font}-Bold'),  # Loại Pet value
            ('FONTNAME', (1, 8), (1, 8), f'{vietnamese_font}-Bold'),  # Màu value
            ('FONTNAME', (1, 9), (1, 9), f'{vietnamese_font}-Bold'),  # Size value
            ('FONTSIZE', (1, 6), (1, 6), 9),  # Slightly larger for bold fields
            ('FONTSIZE', (1, 7), (1, 7), 9),  # Slightly larger for bold fields
            ('FONTSIZE', (1, 8), (1, 8), 9),  # Slightly larger for bold fields
            ('FONTSIZE', (1, 9), (1, 9), 9),  # Slightly larger for bold fields
        ]))
        
        story.append(table)
        story.append(Spacer(1, 2))  # Reduced spacing between table and image
        
        # Add images from URL
        image_url = order_data.get('anh', '')
        if image_url:
            try:
                # Download and optimize image
                image_data = download_image(image_url)
                if image_data:
                    optimized_data = optimize_image(image_data)
                    
                    # Create BytesIO object for ReportLab
                    image_buffer = BytesIO(optimized_data)
                    
                    # Add single image to PDF using BytesIO - optimized for A5
                    img = RLImage(image_buffer, width=4*inch, height=4*inch)
                    story.append(img)
                            
                else:
                    # Add placeholder text if image download failed
                    story.append(Paragraph("Image not available", styles['Normal']))
                    
            except Exception as e:
                logger.error(f"Failed to add image to PDF: {str(e)}")
                story.append(Paragraph("Image not available", styles['Normal']))
        else:
            story.append(Paragraph("No image URL provided", styles['Normal']))
        
        # Build PDF
        doc.build(story)
        pdf_buffer.seek(0)
        
        logger.info("PDF generated successfully with ReportLab")
        return pdf_buffer
        
    except Exception as e:
        logger.error(f"Failed to generate PDF: {str(e)}")
        raise

def generate_pdf_for_order(order_data):
    """
    Generate PDF for a single order
    
    Args:
        order_data (dict): Order data
        
    Returns:
        BytesIO: PDF buffer
    """
    try:
        # Generate PDF using ReportLab
        pdf_buffer = generate_pdf_from_data(order_data)
        
        return pdf_buffer
        
    except Exception as e:
        logger.error(f"Failed to generate PDF for order: {str(e)}")
        raise 