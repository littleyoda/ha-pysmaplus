# """Support for Renault services."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any
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
from .const import DOMAIN, PYSMA_ENTITIES, PYSMA_OBJECT

LOGGER = logging.getLogger(__name__)

ATTR_SCHEDULES = "schedules"
ATTR_TEMPERATURE = "temperature"
ATTR_VEHICLE = "value"
ATTR_WHEN = "when"

# SERVICE_VEHICLE_SCHEMA = vol.Schema(
#     {
#         vol.Required(ATTR_VEHICLE): cv.string,
#     }
# )


SERVICE_SET_VALUE = "set_value"
SERVICE_GET_VALUE_RANGE = "get_value_range"
SERVICES = [SERVICE_SET_VALUE]  # , SERVICE_AC_START, SERVICE_CHARGE_SET_SCHEDULES]


def get_sensor_from_entityid(
    hass: HomeAssistant, entity_id: str
) -> (SMAsensor, pysma.Device):
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
                    return (sensor, hass.data[DOMAIN][configidx][PYSMA_OBJECT])
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
        sensor, device = get_sensor_from_entityid(hass, service_call.data["entity_id"])
        LOGGER.debug(f'Setting {sensor.name} to {int(service_call.data["value"])}')
        await device.set_parameter(sensor._sensor, int(service_call.data["value"]))

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VALUE,
        set_value,
        #        schema=SERVICE_XXX_SCHEMA,
        #    supports_response=SupportsResponse.ONLY,
    )

    async def get_value_range(service_call: ServiceCall) -> ServiceResponse:
        """Return the allowed values."""
        sensor, device = get_sensor_from_entityid(hass, service_call.data["entity_id"])
        return {
            "typ": sensor._sensor.range.typ,
            "values": sensor._sensor.range.values,
            "editable": sensor._sensor.range.editable,
        }

    hass.services.async_register(
        DOMAIN,
        # SERVICE_AC_CANCEL,
        # ac_cancel
        SERVICE_GET_VALUE_RANGE,
        get_value_range,
        #        schema=SERVICE_XXX_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
