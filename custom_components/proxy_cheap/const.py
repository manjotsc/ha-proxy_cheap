"""Constants for the Proxy-Cheap integration."""

DOMAIN = "proxy_cheap"

# API Configuration
API_BASE_URL = "https://api.proxy-cheap.com"
API_TIMEOUT = 30

# Config keys
CONF_API_KEY = "api_key"
CONF_API_SECRET = "api_secret"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PROXY_NAMES = "proxy_names"
CONF_ENABLED_SENSORS = "enabled_sensors"

# Available sensor keys
SENSOR_KEYS = [
    "status",
    "ip_address",
    "port",
    "username",
    "protocol",
    "network_type",
    "country",
    "bandwidth_total",
    "bandwidth_used",
    "bandwidth_remaining",
    "expiry_date",
    "auto_extend",
    "active",  # binary sensor
    "auto_extend_enabled",  # binary sensor
]

# Default enabled sensors
DEFAULT_ENABLED_SENSORS = [
    "status",
    "ip_address",
    "port",
    "bandwidth_remaining",
    "expiry_date",
    "active",
]

# Defaults
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes

# API Endpoints
ENDPOINT_BALANCE = "account/balance"
ENDPOINT_PROXIES = "proxies"
ENDPOINT_PROXY = "proxies/{proxy_id}"
ENDPOINT_WHITELIST = "proxies/{proxy_id}/whitelist-ip"
ENDPOINT_EXTEND = "proxies/{proxy_id}/extend-period"
ENDPOINT_BUY_BANDWIDTH = "proxies/{proxy_id}/buy-bandwidth"
ENDPOINT_AUTO_EXTEND_ENABLE = "proxies/{proxy_id}/auto-extend/enable"
ENDPOINT_AUTO_EXTEND_DISABLE = "proxies/{proxy_id}/auto-extend/disable"

# Network types
NETWORK_TYPE_MOBILE = "MOBILE"
NETWORK_TYPE_DATACENTER = "DATACENTER"
NETWORK_TYPE_RESIDENTIAL = "RESIDENTIAL"
NETWORK_TYPE_RESIDENTIAL_STATIC = "RESIDENTIAL_STATIC"

# Proxy protocols
PROTOCOL_HTTP = "HTTP"
PROTOCOL_HTTPS = "HTTPS"
PROTOCOL_SOCKS5 = "SOCKS5"

# Authentication types
AUTH_USERNAME_PASSWORD = "USERNAME_PASSWORD"
AUTH_IP_WHITELIST = "IP_WHITELIST"

# Sensor attributes
ATTR_PROXY_ID = "proxy_id"
ATTR_IP_ADDRESS = "ip_address"
ATTR_PORT = "port"
ATTR_USERNAME = "username"
ATTR_PROTOCOL = "protocol"
ATTR_NETWORK_TYPE = "network_type"
ATTR_COUNTRY = "country"
ATTR_REGION = "region"
ATTR_BANDWIDTH_TOTAL = "bandwidth_total"
ATTR_BANDWIDTH_USED = "bandwidth_used"
ATTR_BANDWIDTH_REMAINING = "bandwidth_remaining"
ATTR_EXPIRY_DATE = "expiry_date"
ATTR_AUTO_EXTEND = "auto_extend_enabled"
ATTR_AUTHENTICATION_TYPE = "authentication_type"
ATTR_WHITELISTED_IPS = "whitelisted_ips"
ATTR_STATUS = "status"
ATTR_CREATED_AT = "created_at"

# Proxy statuses
STATUS_ACTIVE = "active"
STATUS_EXPIRED = "expired"
STATUS_SUSPENDED = "suspended"
