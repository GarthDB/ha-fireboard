"""Constants for the FireBoard integration."""

from typing import Final

# Integration domain
DOMAIN: Final = "fireboard"

# API Configuration
API_BASE_URL: Final = "https://fireboard.io/api/v1"
API_TIMEOUT: Final = 30
API_RATE_LIMIT: Final = 200  # calls per hour

# Configuration keys
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_POLLING_INTERVAL: Final = "polling_interval"

# Default values
DEFAULT_POLLING_INTERVAL: Final = 40  # seconds (90 calls/hour, well under 200 limit)
MIN_POLLING_INTERVAL: Final = 40  # minimum to respect rate limits
MAX_POLLING_INTERVAL: Final = 300  # 5 minutes maximum

# Device information
ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_UUID: Final = "uuid"
ATTR_DEVICE_TITLE: Final = "title"
ATTR_DEVICE_MODEL: Final = "model"
ATTR_DEVICE_HARDWARE: Final = "hardware_id"

# Channel information
ATTR_CHANNEL_NUMBER: Final = "channel"
ATTR_CHANNEL_LABEL: Final = "label"
ATTR_TEMPERATURE: Final = "temperature"
ATTR_TARGET_TEMP: Final = "target_temp"

# Session information
ATTR_SESSION_ID: Final = "session_id"
ATTR_SESSION_START: Final = "start_time"

# Battery information
ATTR_BATTERY_LEVEL: Final = "battery_level"
ATTR_BATTERY_LOW: Final = "battery_low"

# Connection status
ATTR_ONLINE: Final = "online"
ATTR_LAST_SEEN: Final = "last_seen"

