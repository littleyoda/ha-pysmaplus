"""Constants for the sma integration."""

from homeassistant.const import Platform

DOMAIN = "pysmaplus"

PYSMA_COORDINATOR = "coordinator"
PYSMA_OBJECT = "pysma"
PYSMA_REMOVE_LISTENER = "remove_listener"
PYSMA_SENSORS = "pysma_sensors"
PYSMA_DEVICE_INFO = "device_info"
PYSMA_ENTITIES = "entities"

PLATFORMS = [Platform.SENSOR]

CONF_GROUP = "group"
CONF_ACCESS = "access"
CONF_ACCESSLONG = "accesslong"
CONF_DEVICE = "device"
CONF_SCAN_INTERVAL = "scaninterval"
DEFAULT_SCAN_INTERVAL = 5

GROUPS = ["user", "installer"]
ACCESS = ["speedwireinv", "webconnect", "ennexos", "speedwireem"]
ACCESSLONG = [
    "SMA Devices with Speedwire",
    "SMA Devices with Webconnect",
    "SMA Devices with EnnexOS (e.g. Tripower X Serie)",
    "SMA Energy Meter / Sunny Home Manager 2.0",
]
