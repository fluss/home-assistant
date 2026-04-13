"""Constants for the Fluss+ integration."""

from datetime import timedelta
import logging

DOMAIN = "fluss"
LOGGER = logging.getLogger(__name__)

DEVICE_LIST_UPDATE_INTERVAL = timedelta(minutes=30)

CONF_SCAN_INTERVAL_STATUS = "scan_interval_status"
DEFAULT_SCAN_INTERVAL_STATUS_MINUTES = 30
MIN_SCAN_INTERVAL_MINUTES = 1
