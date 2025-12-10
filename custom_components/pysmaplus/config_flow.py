"""Config flow for the sma integration."""

from __future__ import annotations

import logging
from typing import Any, Dict
import json
import homeassistant.helpers.config_validation as cv
from pysmaplus.device import DeviceInformation
from .helper import discoveryAndScan
from . import getPysmaInstance
import pysmaplus as pysma
import voluptuous as vol
import json
from homeassistant.helpers import selector
from homeassistant import config_entries, core
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import (
    CONF_DEVICE,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from .const import (
    ACCESS,
    ACCESSLONG,
    CONF_ACCESS,
    CONF_ACCESSLONG,
    CONF_DISCOVERY,
    CONF_GROUP,
    CONF_SCAN_INTERVAL,
    CONF_RETRIES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GROUPS,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(
    hass: core.HomeAssistant, data: dict[str, Any]
) -> (dict[str, DeviceInformation], dict[str, str]):
    """Validate the user input allows us to connect."""
    errors: dict[str, str] = {}

    device_list = None
    try:
        sma = await getPysmaInstance(hass, data)
        device_list = await sma.device_list()
        await sma.close_session()
    except pysma.exceptions.SmaConnectionException:
        errors["base"] = "cannot_connect"
    except pysma.exceptions.SmaAuthenticationException:
        errors["base"] = "invalid_auth"
    except pysma.exceptions.SmaReadException:
        errors["base"] = "cannot_retrieve_device_info"
    except Exception:  # pylint: disable=broad-except
        _LOGGER.exception("Unexpected exception")
        errors["base"] = "unknown"
    return device_list, errors


class PySMAOptionsConfigFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle a pyscript options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize pyscript options flow."""
        super().__init__(config_entry)
        self._show_form = False

    async def async_step_init(
        self, user_input: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Manage the pyscript options."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_SCAN_INTERVAL,
                            default=self.config_entry.data.get(CONF_SCAN_INTERVAL, 5),
                        ): int
                    },
                    extra=vol.ALLOW_EXTRA,
                ),
            )

        if any(
            name not in self.config_entry.data
            or user_input[name] != self.config_entry.data[name]
            for name in [CONF_SCAN_INTERVAL]
        ):
            updated_data = self.config_entry.data.copy()
            updated_data.update(user_input)
            self.hass.config_entries.async_update_entry(
                entry=self.config_entry, data=updated_data
            )
            return self.async_create_entry(title="", data={})

        self._show_form = True
        return await self.async_step_no_update()

    async def async_step_no_update(
        self, user_input: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """Tell user no update to process."""
        if self._show_form:
            self._show_form = False
            return self.async_show_form(step_id="no_update", data_schema=vol.Schema({}))

        return self.async_create_entry(title="", data={})


class SmaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Entry-Point for HomeAssistnat

    Handle a config flow for SMA.
    Dialogs
    1. _user     Access Methode
    2. _details  Details (User, Pwd) [optional, not needed for Energy Meter]
    2. _device   Selection of the Device [optional, not needed]
    """

    VERSION = 2
    MINOR_VERSION = 0

    def __init__(self) -> None:
        """Initialize."""
        self._data = {
            CONF_HOST: vol.UNDEFINED,
            CONF_SSL: True,
            CONF_VERIFY_SSL: False,
            CONF_ACCESS: ACCESS[0],
            CONF_GROUP: GROUPS[0],
            CONF_PASSWORD: vol.UNDEFINED,
            CONF_DEVICE: vol.UNDEFINED,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            CONF_RETRIES: 0
        }
        self.listNames: list[str] = []
        self.listDeviceInfo: list[DeviceInformation] = []
        self.discovery: dict[str, list] = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PySMAOptionsConfigFlow:
        """Get the options flow for this handler."""
        return PySMAOptionsConfigFlow(config_entry)

    # "User" => 0,1,2,4 => details => selection
    #        => 3 => selection
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step in config flow."""
        self.config_data = {}
        errors: dict[str, str] = {}
        if user_input is None:
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_ACCESSLONG,
                        default=ACCESSLONG[ACCESS.index(self._data[CONF_ACCESS])],
                    ): vol.In(ACCESSLONG),
                }
            )
            return self.async_show_form(
                step_id="user", data_schema=data_schema, errors=errors
            )

        deviceIdx = ACCESSLONG.index(user_input[CONF_ACCESSLONG])
        if deviceIdx in [1, 2, 3, 5, 6]:
            self.config_data.update(user_input)
            # Return the form of the next step
            return await self.async_step_details()

        if deviceIdx == 4:
            # EM/SHM2 do not require any further parameters.
            self._data[CONF_HOST] = "localhost"
            self._data[CONF_SSL] = False
            self._data[CONF_VERIFY_SSL] = False
            self._data[CONF_GROUP] = ""
            self._data[CONF_PASSWORD] = ""
            self._data[CONF_ACCESS] = ACCESS[deviceIdx]
            self._data[CONF_DEVICE] = ""
            return await self.async_step_deviceselection()

        if deviceIdx == 0:
            return await self.async_step_discovery()

        return self.async_abort(reason="not_supported")

    async def async_step_discovery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            ret = await discoveryAndScan()
            _LOGGER.error(json.dumps(ret))
            errors: dict[str, str] = {}
            self.discovery: dict[str, list] = {"data": [], "name": []}
            # Fill self.dicovery this dicovery-data
            for ip in ret["discovery"]:
                for am in ip["identify"]:
                    if am["status"] == "failed" or am["access"] == "shm2":
                        continue
                    am["addr"] = ip["addr"]
                    am["accessidx"] = -1
                    #                   access = am["access"]
                    if am["access"] not in ACCESS:
                        continue
                    am["accessidx"] = ACCESS.index(am["access"])
                    am["accessnice"] = ACCESSLONG[am["accessidx"]]

                    self.discovery["name"].append(
                        f'[{ip["addr"]}] {am["accessnice"]} {am["remark"]}'
                    )
                    self.discovery["data"].append(am)

            if len(self.discovery["data"]) == 0:
                return self.async_abort(reason="No SMA Device detected!")

            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_DISCOVERY,
                    ): vol.In(self.discovery["name"]),
                }
            )
            return self.async_show_form(
                step_id="discovery", data_schema=data_schema, errors=errors
            )
        amidx = self.discovery["name"].index(user_input[CONF_DISCOVERY])
        am = self.discovery["data"][amidx]
        self.config_data[CONF_ACCESSLONG] = ACCESSLONG[ACCESS.index(am["access"])]
        self.config_data[CONF_DISCOVERY] = am

        if ACCESS.index(am["access"]) == 4:
            # EM/SHM2 do not require any further parameters.
            self._data[CONF_HOST] = "localhost"
            self._data[CONF_SSL] = False
            self._data[CONF_VERIFY_SSL] = False
            self._data[CONF_GROUP] = ""
            self._data[CONF_PASSWORD] = ""
            self._data[CONF_ACCESS] = am["access"]
            self._data[CONF_DEVICE] = ""
            return await self.async_step_deviceselection()

        return await self.async_step_details()

    async def async_step_details(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step in config flow."""
        errors = {}

        deviceIdx = ACCESSLONG.index(self.config_data[CONF_ACCESSLONG])

        if self.config_data and "discovery" in self.config_data:
            # Default-Values based on discovery information
            disc = self.config_data["discovery"]
            self._data[CONF_HOST] = disc["addr"]
            if "https" in disc["remark"]:
                self._data[CONF_SSL] = True
                self._data[CONF_VERIFY_SSL] = False
            if disc["remark"] == "http" or "http://" in disc["remark"]:
                self._data[CONF_SSL] = False
                self._data[CONF_VERIFY_SSL] = False

        if user_input is not None:
            self._data[CONF_HOST] = user_input.get(CONF_HOST)
            self._data[CONF_SSL] = user_input.get(CONF_SSL, True)
            self._data[CONF_VERIFY_SSL] = user_input.get(CONF_VERIFY_SSL, False)
            self._data[CONF_GROUP] = user_input.get(CONF_GROUP, "")
            self._data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, "")
            self._data[CONF_ACCESS] = ACCESS[deviceIdx]
            self._data[CONF_DEVICE] = ""
            self._data[CONF_RETRIES] = int(user_input.get(CONF_RETRIES, 0))
            return await self.async_step_deviceselection()

        if deviceIdx == 1:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Required(CONF_GROUP, default=self._data[CONF_GROUP]): vol.In(
                        GROUPS
                    ),
                    vol.Required(CONF_PASSWORD): cv.string,
                    vol.Optional(
                        CONF_RETRIES,
                        default=3,
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=3,
                            max=100,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        ),
                    )
                }
            )
        elif deviceIdx == 2:
            data_schema = vol.Schema(
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
        elif deviceIdx == 3:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Required(CONF_GROUP, default=self._data[CONF_GROUP]): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        elif deviceIdx == 5:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        elif deviceIdx == 6:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=self._data[CONF_HOST]): cv.string,
                    vol.Required(CONF_GROUP, default=self._data[CONF_GROUP]): vol.In(
                        GROUPS
                    ),
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )           
        else:
            errors["base"] = "unknown_device"

        return self.async_show_form(
            step_id="details", data_schema=data_schema, errors=errors
        )

    async def async_step_deviceselection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """."""

        if user_input is None:
            # Create a list of all devices
            errors = {}
            device_list, errors = await validate_input(self.hass, self._data)
            if errors:
                return self.async_abort(reason=errors["base"])
            self.listNames = []
            self.listDeviceInfo = []
            self.deviceList = device_list
            if self.deviceList is None or len(self.deviceList.values()) == 0:
                return self.async_abort(reason="No Device found!")

            for i in device_list.values():
                self.listNames.append(f"{i.name} {i.type} ({i.serial})")
                self.listDeviceInfo.append(i)
            if len(self.listDeviceInfo) == 1:
                self._data[CONF_DEVICE] = self.listDeviceInfo[0].id

        if user_input is not None:
            idx = self.listNames.index(user_input.get(CONF_DEVICE))
            self._data[CONF_DEVICE] = self.listDeviceInfo[idx].id

        if self._data[CONF_DEVICE] != "":
            return await self.createEntry(self.deviceList[self._data[CONF_DEVICE]])

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE,
                ): vol.In(self.listNames),
            }
        )
        return self.async_show_form(
            step_id="deviceselection", data_schema=data_schema, errors=errors
        )

    def shortConfAcccess(self, access):
        if access == "speedwire" or access == "speedwireinv":
            return "sw"
        if access == "webconnect":
            return "wc"
        if access == "ennexos":
            return "en"
        if access == "speedwireem":
            return "em"
        if access == "shm2":
            return "ggc"
        if access == "speedwireV2":
            return "sw2"
        return "???"

    async def createEntry(self, device_info: DeviceInformation):
        """Create Entry based on device_info"""
        await self.async_set_unique_id(
            self._data[CONF_ACCESS]
            + "-"
            + str(device_info.serial)
            + "-"
            + str(device_info.id)
        )
        self._abort_if_unique_id_configured(updates=self._data)
        return self.async_create_entry(
            title=f"{device_info.name} ({self.shortConfAcccess(self._data[CONF_ACCESS])}{str(device_info.serial)})",
            data=self._data,
        )
