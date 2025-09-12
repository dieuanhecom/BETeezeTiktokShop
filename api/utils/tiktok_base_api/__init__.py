import logging

from api import setup_logging
from api.utils.auth import GenerateSign

from ..constant import TIKTOK_API_URL as TIKTOK_API_URL
from ..constant import app_key as app_key
from ..constant import secret as secret

logger = logging.getLogger("api.utils.tiktok_base_api")
setup_logging(logger, is_root=False, level=logging.INFO)

# Hàm tạo signature cho Tiktok API
SIGN = GenerateSign()
