from google.oauth2 import service_account
from googleapiclient.discovery import build

from tiktok.settings import PUB_ENVIRONMENT

# Thông tin xác thực từ tệp JSON bạn đã tải xuống
SERVICE_ACCOUNT_FILE = (
    "api/utils/google/dev.json"
    if PUB_ENVIRONMENT == "dev"
    else "api/utils/google/prod.json"
)
PARENT_FOLDER_ID = (
    "1cKBThKJSGTrFlbc0H2xTlGWXICP0EdAv"
    if PUB_ENVIRONMENT == "dev"
    else "1x3QwHDfYXbeUuQj2yel5zsphHy98sQj1"
)
# 1fcgoUghiIh_sr7JxUnL9_2xObkCfBM94

# Phạm vi quyền truy cập API, ở đây là đọc và ghi vào Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.appdata",
]


def authenticate():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return creds


def upload_pdf(file_path, order_id):
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": order_id, "parents": [PARENT_FOLDER_ID]}
    file = service.files().create(body=file_metadata, media_body=file_path).execute()


def search_file(file_name):
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    # Perform the search query
    query = f"name='{file_name}'"
    results = service.files().list(q=query).execute()

    files = results.get("files", [])

    search_results = []

    if not files:
        print(f"No files found with the name '{file_name}'.")
    else:
        print(f"Files found with the name '{file_name}':")
        for file in files:
            file_info = {
                "name": file["name"],
                "link": f"https://drive.google.com/file/d/{file['id']}",
            }
            search_results.append(file_info)

    return search_results


class GoogleDriveService:
    """Service class for Google Drive operations with retry mechanism"""
    
    def __init__(self):
        self.creds = authenticate()
        self.service = build("drive", "v3", credentials=self.creds)
    
    def upload_pdf_to_drive(self, pdf_buffer, filename, max_retries=3):
        """
        Upload PDF buffer to Google Drive with retry mechanism
        
        Args:
            pdf_buffer (BytesIO): PDF buffer to upload
            filename (str): Name for the file in Google Drive
            max_retries (int): Maximum number of retry attempts
            
        Returns:
            dict: Result dictionary containing:
                - success (bool): Whether upload was successful
                - link (str): Google Drive shareable link if successful
                - error (str): Error message if failed
        """
        import time
        import logging
        from googleapiclient.http import MediaInMemoryUpload
        
        logger = logging.getLogger(__name__)
        
        for attempt in range(max_retries):
            try:
                # Calculate backoff time: 1s, 2s, 4s
                if attempt > 0:
                    backoff_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying upload, attempt {attempt + 1}/{max_retries} after {backoff_time}s")
                    time.sleep(backoff_time)
                
                # Prepare file metadata
                file_metadata = {
                    'name': filename,
                    'parents': [PARENT_FOLDER_ID],
                    'mimeType': 'application/pdf'
                }
                
                # Create media upload from buffer
                pdf_buffer.seek(0)
                media = MediaInMemoryUpload(
                    pdf_buffer.read(),
                    mimetype='application/pdf',
                    resumable=True
                )
                
                # Upload file
                file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id,webViewLink'
                ).execute()
                
                # Set file permissions to "anyone with link can view"
                permission = {
                    'type': 'anyone',
                    'role': 'reader',
                }
                
                self.service.permissions().create(
                    fileId=file.get('id'),
                    body=permission
                ).execute()
                
                # Get shareable link
                file_link = file.get('webViewLink')
                
                logger.info(f"Successfully uploaded {filename} to Google Drive")
                
                return {
                    'success': True,
                    'link': file_link
                }
                
            except Exception as e:
                error_msg = f"Upload error (attempt {attempt + 1}/{max_retries}): {str(e)}"
                logger.error(error_msg)
                
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': f"Failed to upload after {max_retries} retries: {str(e)}"
                    }
