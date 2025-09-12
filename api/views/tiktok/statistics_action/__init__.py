import logging
from api import setup_logging

from .FinanceApi import *

logger = logging.getLogger("views.tiktok.statistics_action")
setup_logging(logger, is_root=False, level=logging.INFO)
