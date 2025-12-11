import os
import logging

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("mcp_ad_reporting")

# Защитные лимиты
MAX_COUNTERPARTY_LENGTH_NAME = float(os.getenv("MAX_COUNTERPARTY_LENGTH_NAME", "255")) 