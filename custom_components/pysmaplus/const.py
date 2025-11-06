"""Constants for the sma integration."""

from homeassistant.const import Platform

DOMAIN = "pysmaplus"

PYSMA_COORDINATOR = "coordinator"
PYSMA_OBJECT = "pysma"
PYSMA_REMOVE_LISTENER = "remove_listener"
PYSMA_SENSORS = "pysma_sensors"
PYSMA_DEVICE_INFO = "device_info"
PYSMA_ENTITIES = "entities"
PYSMA_DEVICEID = "deviceid"

PLATFORMS = [Platform.SENSOR]

CONF_GROUP = "group"
CONF_ACCESS = "access"
CONF_ACCESSLONG = "accesslong"
CONF_DISCOVERY = "discovery"
CONF_DEVICE = "device"
CONF_RETRIES = "retries"
CONF_SCAN_INTERVAL = "scaninterval"
DEFAULT_SCAN_INTERVAL = 5

GROUPS = ["user", "installer"]
ACCESS = ["discovery", "speedwireinv", "webconnect", "ennexos", "speedwireem", "shm2", "speedwireinvV2"]
ACCESSLONG = [
    "Discovery Modus", #0
    "SMA Devices with Speedwire", #1
    "SMA Devices of the Webconnect-Generation", #2
    "SMA Devices with EnnexOS (e.g. Tripower X Serie)", #3
    "SMA Energy Meter / Sunny Home Manager 2.0", #4
    "Sunny Home Manager 2 with Grid Guard Code", #5
    "SMA Devices with Speedwire V2 (Beta-Testing)", #6
]
