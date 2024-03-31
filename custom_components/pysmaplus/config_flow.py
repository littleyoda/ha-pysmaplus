"""Config flow for the sma integration."""
from __future__ import annotations

import logging
from typing import Any

import pysmaimport pysmaplus as pysma
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_SSL, CONF_VERIFY_SSL
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv

from .const import CONF_GROUP, DOMAIN, GROUPS, CONF_ACCESS, ACCESS, CONF_ACCESSLONG, ACCESSLONG

_LOGGER = logging.getLogger(__name__)


async def validate_input(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    url = None
    session = None
    if CONF_SSL in data and CONF_HOST in data:
        protocol = "https" if data[CONF_SSL] else "http"
        url = f"{protocol}://{data[CONF_HOST]}"
        session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])
    sma = pysma.getDevice(session, url, password = data[CONF_PASSWORD], groupuser = data[CONF_GROUP], accessmethod = data[CONF_ACCESS])
    #sma = pysma.SMA(session, url, data[CONF_PASSWORD], group=data[CONF_GROUP])

    # new_session raises SmaAuthenticationException on failure
    await sma.new_session()
    device_info = await sma.device_info()
    await sma.close_session()

    return device_info


class SmaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SMA."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._data = {
            CONF_HOST: vol.UNDEFINED,
            CONF_SSL: False,
            CONF_VERIFY_SSL: True,
            CONF_ACCESS: ACCESS[0],
            CONF_GROUP: GROUPS[0],
            CONF_PASSWORD: vol.UNDEFINED,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First step in config flow."""
        self.config_data = {}
        errors = {}
        if user_input is not None:
            _LOGGER.exception(user_input)
            deviceIdx = ACCESSLONG.index(user_input[CONF_ACCESSLONG])
            if deviceIdx in [0,1]:
                self.config_data.update(user_input)
                # Return the form of the next step
                return await self.async_step_details()

            if deviceIdx == 2:
                # EM/SHM2 do not require any further parameters.
                self._data[CONF_HOST] = "localhost"
                self._data[CONF_SSL] = False
                self._data[CONF_VERIFY_SSL] = False
                self._data[CONF_GROUP] = ""
                self._data[CONF_PASSWORD] = ""
                self._data[CONF_ACCESS] = ACCESS[deviceIdx]

                try:
                    device_info = await validate_input(self.hass, self._data)
                except pysma.exceptions.SmaConnectionException:
                    errors["base"] = "cannot_connect"
                except pysma.exceptions.SmaAuthenticationException:
                    errors["base"] = "invalid_auth"
                except pysma.exceptions.SmaReadException:
                    errors["base"] = "cannot_retrieve_device_info"
                except Exception:  # pylint: disable=broad-except
                    _LOGGER.exception("Unexpected exception")
                    errors["base"] = "unknown"

                if not errors:
                    await self.async_set_unique_id(device_info["serial"])
                    self._abort_if_unique_id_configured(updates=self._data)
                    return self.async_create_entry(
                        title=device_info["serial"], data=self._data
                    )

        data_schema=vol.Schema(
            {
                vol.Required(CONF_ACCESSLONG, default=ACCESSLONG[ACCESS.index(self._data[CONF_ACCESS])]): vol.In(
                    ACCESSLONG
                ),
            })
        return self.async_show_form(step_id="user", data_schema = data_schema, errors=errors)
    

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """First step in config flow."""
        errors = {}

        deviceIdx = ACCESSLONG.index(self.config_data[CONF_ACCESSLONG])
        if user_input is not None:
            self._data[CONF_HOST] = user_input.get(CONF_HOST)
            self._data[CONF_SSL] = user_input.get(CONF_SSL, True)
            self._data[CONF_VERIFY_SSL] = user_input.get(CONF_VERIFY_SSL, False)
            self._data[CONF_GROUP] = user_input.get(CONF_GROUP, "")
            self._data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
            self._data[CONF_ACCESS] = ACCESS[deviceIdx]

            try:
                device_info = await validate_input(self.hass, self._data)
            except pysma.exceptions.SmaConnectionException:
                errors["base"] = "cannot_connect"
            except pysma.exceptions.SmaAuthenticationException:
                errors["base"] = "invalid_auth"
            except pysma.exceptions.SmaReadException:
                errors["base"] = "cannot_retrieve_device_info"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(device_info["serial"])
                self._abort_if_unique_id_configured(updates=self._data)
                return self.async_create_entry(
                    title=self._data[CONF_HOST], data=self._data
                )
            
        if (deviceIdx == 0):
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Optional(CONF_SSL, default=self._data[CONF_SSL]): cv.boolean,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=self._data[CONF_VERIFY_SSL]
                    ): cv.boolean,
                    vol.Required(CONF_GROUP, default=self._data[CONF_GROUP]): vol.In(
                        GROUPS
                    ),
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        elif (deviceIdx == 1):
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Required(CONF_GROUP, default=self._data[CONF_GROUP]): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        else:
            errors["base"] = "unknown_device"            

        return self.async_show_form(step_id="details", data_schema=data_schema, errors=errors)
