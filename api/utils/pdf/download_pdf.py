import requests
import logging
import time
from io import BytesIO
import PyPDF2

logger = logging.getLogger(__name__)


def convert_google_drive_url(url):
    """
    Convert Google Drive sharing URL to direct download URL
    
    Args:
        url (str): Google Drive URL (view/edit format)
        
    Returns:
        str: Direct download URL
    """
    import re
    
    # Pattern for Google Drive URLs
    patterns = [
        r'https://drive\.google\.com/file/d/([a-zA-Z0-9-_]+)/view',
        r'https://drive\.google\.com/file/d/([a-zA-Z0-9-_]+)/edit',
        r'https://drive\.google\.com/file/d/([a-zA-Z0-9-_]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            file_id = match.group(1)
            return f'https://drive.google.com/uc?export=download&id={file_id}'
    
    return url  # Return original URL if not a Google Drive URL


def download_pdf_from_url(url, max_retries=3):
    """
    Download PDF from URL with retry mechanism
    
    Args:
        url (str): URL of the PDF to download
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        dict: Result dictionary containing:
            - success (bool): Whether download was successful
            - data (BytesIO): PDF buffer if successful
            - url (str): Original URL
            - error (str): Error message if failed
    """
    
    # Convert Google Drive URLs to direct download URLs
    download_url = convert_google_drive_url(url)
    if download_url != url:
        logger.info(f"Converted Google Drive URL: {url} -> {download_url}")
    
    for attempt in range(max_retries):
        try:
            # Calculate backoff time: 1s, 2s, 4s
            if attempt > 0:
                backoff_time = 2 ** (attempt - 1)
                logger.info(f"Retrying download for {url}, attempt {attempt + 1}/{max_retries} after {backoff_time}s")
                time.sleep(backoff_time)
            
            # Download with timeout
            response = requests.get(download_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Handle Google Drive virus scan warning for large files
            if 'drive.google.com' in download_url and 'virus scan warning' in response.text.lower():
                # Look for the actual download link in the response
                import re
                confirm_match = re.search(r'confirm=([^&]+)', response.text)
                if confirm_match:
                    confirm_token = confirm_match.group(1)
                    download_url_with_confirm = f"{download_url}&confirm={confirm_token}"
                    response = requests.get(download_url_with_confirm, timeout=30, stream=True)
                    response.raise_for_status()
            
            # Verify content type
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                logger.warning(f"URL {url} may not be a PDF. Content-Type: {content_type}")
            
            # Read content into BytesIO
            pdf_buffer = BytesIO()
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    pdf_buffer.write(chunk)
            
            pdf_buffer.seek(0)
            
            # Validate PDF format
            try:
                PyPDF2.PdfReader(pdf_buffer)
                pdf_buffer.seek(0)  # Reset position after validation
            except Exception as e:
                raise ValueError(f"Invalid PDF format: {str(e)}")
            
            logger.info(f"Successfully downloaded PDF from {url}")
            return {
                'success': True,
                'data': pdf_buffer,
                'url': url
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"Connection timeout (attempt {attempt + 1}/{max_retries})"
            logger.error(f"{error_msg} for URL: {url}")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': f"Connection timeout after {max_retries} retries",
                    'url': url
                }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error (attempt {attempt + 1}/{max_retries}): {str(e)}"
            logger.error(f"{error_msg} for URL: {url}")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': f"Network error after {max_retries} retries: {str(e)}",
                    'url': url
                }
                
        except ValueError as e:
            # PDF validation error, no retry needed
            logger.error(f"PDF validation error for URL {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
            
        except Exception as e:
            error_msg = f"Unexpected error (attempt {attempt + 1}/{max_retries}): {str(e)}"
            logger.error(f"{error_msg} for URL: {url}")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': f"Unexpected error after {max_retries} retries: {str(e)}",
                    'url': url
                }