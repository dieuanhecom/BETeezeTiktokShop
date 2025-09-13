import json
import os
import pickle

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from tiktok.settings import PUB_ENVIRONMENT

# OAuth2 credentials file path
CREDENTIALS_FILE = (
    "api/utils/google/oauth_credentials_dev.json"
    if PUB_ENVIRONMENT == "dev"
    else "api/utils/google/oauth_credentials_prod.json"
)

# Token file to store user's access and refresh tokens
TOKEN_FILE = (
    "api/utils/google/token_dev.pickle"
    if PUB_ENVIRONMENT == "dev"
    else "api/utils/google/token_prod.pickle"
)

PARENT_FOLDER_ID = (
    "1DPWPANYS9PTx8OEHiywYTJyWC3OlBGK4"
    if PUB_ENVIRONMENT == "dev"
    else "1DPWPANYS9PTx8OEHiywYTJyWC3OlBGK4"
)

# Phạm vi quyền truy cập API cho Google Drive
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


def authenticate(use_console_flow=False):
    """
    Authenticate using OAuth2 flow
    
    Args:
        use_console_flow (bool): If True, use console-based flow instead of local server
        
    Returns:
        valid credentials for Google Drive API
    """
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None

        if not creds:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"OAuth2 credentials file not found: {CREDENTIALS_FILE}. "
                    "Please download your OAuth2 credentials from Google Cloud Console."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            
            if use_console_flow:
                # Console-based flow for server environments
                print("🔐 Using console-based OAuth flow...")
                print("Please visit the following URL to authorize the application:")
                creds = flow.run_console()
            else:
                # Local server flow (default)
                # Try different ports in case default port is occupied
                ports_to_try = [8080, 8081, 8082, 8083, 0]  # 0 = random available port
                
                for port in ports_to_try:
                    try:
                        print(f"🔐 Attempting OAuth authentication on port {port}...")
                        creds = flow.run_local_server(
                            port=port,
                            open_browser=True,
                            timeout_seconds=120  # 2 minute timeout
                        )
                        print(f"✅ OAuth authentication successful on port {port}")
                        break
                    except OSError as e:
                        if "Address already in use" in str(e):
                            print(f"❌ Port {port} is already in use, trying next port...")
                            if port == 0:  # Last attempt with random port failed
                                print("⚠️  All ports occupied. Falling back to console flow...")
                                creds = flow.run_console()
                                break
                            continue
                        else:
                            # Different OSError, re-raise
                            raise
                    except Exception as e:
                        print(f"❌ Authentication failed on port {port}: {str(e)}")
                        if port == 0:  # Last attempt
                            print("⚠️  Local server flow failed. Falling back to console flow...")
                            try:
                                creds = flow.run_console()
                                break
                            except Exception as console_error:
                                raise Exception(
                                    f"Both local server and console flows failed. "
                                    f"Local server error: {str(e)}, "
                                    f"Console error: {str(console_error)}"
                                ) from e
                        continue

        # Save the credentials for the next run
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds


def upload_pdf(file_path, order_id):
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": order_id, "parents": [PARENT_FOLDER_ID]}
    service.files().create(body=file_metadata, media_body=file_path).execute()


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
    """Service class for Google Drive operations with retry mechanism and OAuth2 support"""

    def __init__(self):
        self.creds = None
        self.service = None
        self._initialize_service()

    def _initialize_service(self, use_console_flow=False):
        """Initialize or refresh the Google Drive service"""
        try:
            self.creds = authenticate(use_console_flow=use_console_flow)
            self.service = build("drive", "v3", credentials=self.creds)
        except Exception as e:
            print(f"Failed to initialize Google Drive service: {e}")
            raise

    def _refresh_service_if_needed(self):
        """Refresh service if credentials are expired"""
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.service = build("drive", "v3", credentials=self.creds)
            except Exception as e:
                print(f"Failed to refresh credentials: {e}")
                # Re-initialize service if refresh fails
                self._initialize_service()

    def upload_pdf_to_drive(self, pdf_buffer, filename, max_retries=3):
        """
        Upload PDF buffer to Google Drive with retry mechanism and OAuth2 support

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
        import logging
        import time

        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaInMemoryUpload

        logger = logging.getLogger(__name__)

        for attempt in range(max_retries):
            try:
                # Calculate backoff time: 1s, 2s, 4s
                if attempt > 0:
                    backoff_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying upload, attempt {attempt + 1}/{max_retries} after {backoff_time}s")
                    time.sleep(backoff_time)

                # Refresh service if needed (for OAuth2 token expiry)
                self._refresh_service_if_needed()

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
                    fields='id,webViewLink,webContentLink'
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

                # Get shareable link (prefer webContentLink for direct download)
                file_link = file.get('webViewLink')
                download_link = file.get('webContentLink')

                logger.info(f"Successfully uploaded {filename} to Google Drive")

                return {
                    'success': True,
                    'link': file_link,
                    'download_link': download_link,
                    'file_id': file.get('id')
                }

            except HttpError as e:
                # Handle specific Google API errors
                if e.resp.status == 401:  # Unauthorized
                    logger.warning("Unauthorized access, attempting to re-authenticate")
                    try:
                        self._initialize_service()
                        continue  # Retry with new credentials
                    except Exception as auth_error:
                        error_msg = f"Re-authentication failed: {str(auth_error)}"
                        logger.error(error_msg)

                error_msg = f"Google API error (attempt {attempt + 1}/{max_retries}): {str(e)}"
                logger.error(error_msg)

            except Exception as e:
                error_msg = f"Upload error (attempt {attempt + 1}/{max_retries}): {str(e)}"
                logger.error(error_msg)

                # If it's a credential issue, try to re-initialize
                if "credentials" in str(e).lower() or "auth" in str(e).lower():
                    try:
                        # Try console flow if local server fails
                        self._initialize_service(use_console_flow=True)
                        continue  # Retry with new service
                    except Exception as init_error:
                        logger.error(f"Service re-initialization failed: {str(init_error)}")

                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': f"Failed to upload after {max_retries} retries: {str(e)}"
                    }

        return {
            'success': False,
            'error': f"Upload failed after {max_retries} attempts"
        }

    def check_authentication_status(self):
        """
        Check current authentication status

        Returns:
            dict: Status information
        """
        try:
            if not self.creds:
                return {
                    'authenticated': False,
                    'message': 'No credentials found'
                }

            if not self.creds.valid:
                if self.creds.expired and self.creds.refresh_token:
                    return {
                        'authenticated': False,
                        'message': 'Token expired but can be refreshed'
                    }
                else:
                    return {
                        'authenticated': False,
                        'message': 'Invalid credentials, re-authentication needed'
                    }

            # Test API call
            self.service.about().get(fields="user").execute()

            return {
                'authenticated': True,
                'message': 'Successfully authenticated'
            }

        except Exception as e:
            return {
                'authenticated': False,
                'message': f'Authentication check failed: {str(e)}'
            }

    def force_reauth(self):
        """
        Force re-authentication by removing stored token
        """
        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)

            # Re-initialize service with console flow fallback
            try:
                self._initialize_service()
            except Exception:
                # If local server fails, try console flow
                self._initialize_service(use_console_flow=True)

            return {
                'success': True,
                'message': 'Re-authentication completed successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Re-authentication failed: {str(e)}'
            }


def is_server_environment():
    """
    Detect if running in a server environment where GUI/browser is not available
    """
    import sys
    
    # Check for common server environment indicators
    server_indicators = [
        not hasattr(sys, 'ps1'),  # Not in interactive mode
        os.getenv('SSH_CLIENT') is not None,  # SSH connection
        os.getenv('SSH_TTY') is not None,  # SSH TTY
        os.getenv('DISPLAY') is None,  # No display server
        os.getenv('TERM') == 'dumb',  # Dumb terminal
        'PYTEST_CURRENT_TEST' in os.environ,  # Running in pytest
    ]
    
    return any(server_indicators)


def get_drive_service(force_console_flow=None):
    """
    Convenience function to get a GoogleDriveService instance
    
    Args:
        force_console_flow (bool): Force console flow. If None, auto-detect environment
    """
    if force_console_flow is None:
        force_console_flow = is_server_environment()
    
    service = GoogleDriveService()
    
    # If we detected server environment, try to re-initialize with console flow
    if force_console_flow:
        try:
            service._initialize_service(use_console_flow=True)
        except Exception as e:
            print(f"Console flow initialization failed: {e}")
            # Fall back to regular flow
            pass
    
    return service


def check_oauth_setup():
    """
    Check if OAuth2 setup is complete

    Returns:
        dict: Setup status information
    """
    issues = []

    # Check credentials file
    if not os.path.exists(CREDENTIALS_FILE):
        issues.append(f"OAuth2 credentials file not found: {CREDENTIALS_FILE}")

    # Check if it's a valid JSON
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r') as f:
                creds_data = json.load(f)
                if 'installed' not in creds_data:
                    issues.append("Invalid credentials format. Should contain 'installed' key.")
        except json.JSONDecodeError:
            issues.append("Credentials file is not valid JSON")
        except Exception as e:
            issues.append(f"Error reading credentials file: {str(e)}")

    # Check token file existence (optional)
    token_exists = os.path.exists(TOKEN_FILE)

    return {
        'setup_complete': len(issues) == 0,
        'issues': issues,
        'token_exists': token_exists,
        'credentials_file': CREDENTIALS_FILE,
        'token_file': TOKEN_FILE
    }
