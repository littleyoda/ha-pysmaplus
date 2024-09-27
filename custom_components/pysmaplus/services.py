# """Support for Renault services."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from .sensor import SMAsensor
import voluptuous as vol
import pysmaplus as pysma
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers import entity_registry as er
from .const import (
    DOMAIN,
    PYSMA_ENTITIES,
    PYSMA_OBJECT,
    PYSMA_DEVICE_INFO,
    PYSMA_DEVICEID,
)

LOGGER = logging.getLogger(__name__)

ATTR_SCHEDULES = "schedules"
ATTR_TEMPERATURE = "temperature"
ATTR_VEHICLE = "value"
ATTR_WHEN = "when"

SERVICE_DISCOVERY = "run_discovery"
SERVICE_SET_VALUE = "set_value"
SERVICE_GET_VALUE_RANGE = "get_value_range"
SERVICES = [
    SERVICE_SET_VALUE,
    SERVICE_DISCOVERY,
]  


def get_sensor_from_entityid(
    hass: HomeAssistant, entity_id: str
) -> (SMAsensor, pysma.Device, str):
    """This method seems rather complicated to me.
    Who knows a better method?"""
    # get RegisterEntry
    registry = er.async_get(hass)
    source_entity_id = er.async_validate_entity_id(registry, entity_id)
    re = registry.async_get(source_entity_id)

    # from registeryEntry, get the device_register
    uid = re.unique_id
    device_registry = dr.async_get(hass)
    device_entry = device_registry.async_get(re.device_id)

    # Search in the Device_Entry
    for configidx in list(device_entry.config_entries):
        if configidx in hass.data[DOMAIN]:
            deviceCfg = hass.data[DOMAIN][configidx]
            for sensor in deviceCfg[PYSMA_ENTITIES]:
                if sensor._attr_unique_id == uid:
                    return (
                        sensor,
                        hass.data[DOMAIN][configidx][PYSMA_OBJECT],
                        hass.data[DOMAIN][configidx][PYSMA_DEVICEID],
                    )
    return None


def setup_services(hass: HomeAssistant) -> None:
    """Register the Renault services."""

    SERVICE_SET_VALUE_SCHEMA = vol.Schema(
        {
            vol.Required("entity_id"): cv.string,
            vol.Required("value"): cv.positive_int,
        }
    )

    async def set_value(service_call: ServiceCall) -> None:
        """Set Parameter Value."""
        sensor, pysmadevice, deviceid = get_sensor_from_entityid(
            hass, service_call.data["entity_id"]
        )
        LOGGER.debug(
            f'Setting {deviceid} / {sensor.name} to {int(service_call.data["value"])}'
        )
        await pysmadevice.set_parameter(
            sensor._sensor, int(service_call.data["value"]), deviceid
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VALUE,
        set_value,
    )

    async def get_value_range(service_call: ServiceCall) -> ServiceResponse:
        """Return the allowed values."""
        sensor, pysmadevice, deviceid = get_sensor_from_entityid(
            hass, service_call.data["entity_id"]
        )
        return {
            "typ": sensor._sensor.range.typ,
            "values": sensor._sensor.range.values,
            "names": sensor._sensor.range.names(),
            "editable": sensor._sensor.range.editable,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_VALUE_RANGE,
        get_value_range,
        supports_response=SupportsResponse.ONLY,
    )

    async def identify(url: str, savedebug: bool) -> list:
        order_list = ["found", "maybe", "failed"]
        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False)
        ) as session:
            ret = await pysma.autoDetect(session, url)
            ret_sorted = sorted(ret, key=lambda x: order_list.index(x.status))
            return ret_sorted

    async def discovery(service_call: ServiceCall) -> ServiceResponse:
        LOGGER.info("PYSMA Discovery started. Expect Errors in the Logfiles.")
        debug: dict[str, Any] = {"discovery": [], "status": {}}
        ret = await pysma.discovery()
        if len(ret) == 0:
            debug["status"] = "Found no SMA devices via speedwire discovery request!"
        #      debug["addr"] = ret

        for r in ret:
            z = {"addr": r[0], "port": r[1], "identify": []}
            debug["discovery"].append(z)
            # print(r[0])
            ident = await identify(r[0], False)
            for i in ident:
                z["identify"].append(
                    {
                        "access": i.access,
                        "status": i.status,
                        "tested_endpoints": i.tested_endpoints,
                        "exception": str(i.exception),
                        "remark": i.remark,
                        "device": i.device,
                    }
                )
        LOGGER.info("PYSMA Discovery finisehd.")

        return debug

    hass.services.async_register(
        DOMAIN,
        SERVICE_DISCOVERY,
        discovery,
        supports_response=SupportsResponse.ONLY,
    )
