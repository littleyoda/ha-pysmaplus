"""The sma integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any
import pysmaplus as pysma
from pysmaplus import Device
from homeassistant.components import network

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_VERIFY_SSL,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .services import setup_services

from .const import (
    CONF_GROUP,
    CONF_ACCESS,
    CONF_SCAN_INTERVAL,
    CONF_DEVICE,
    CONF_RETRIES,
    DOMAIN,
    PLATFORMS,
    PYSMA_COORDINATOR,
    PYSMA_DEVICE_INFO,
    PYSMA_OBJECT,
    PYSMA_REMOVE_LISTENER,
    PYSMA_SENSORS,
    PYSMA_ENTITIES,
    PYSMA_DEVICEID,
)


_LOGGER = logging.getLogger(__name__)


async def _create_sma_device(hass: HomeAssistant, data: dict[str, Any]) -> Device:
    """Creates and configures a pysmaplus device object without establishing a session."""
    url = None
    session = None
    if data[CONF_ACCESS] == "speedwireinv" or data[CONF_ACCESS] == "speedwireinvV2":
        url = data[CONF_HOST]
    elif data[CONF_ACCESS] == "webconnect":
        protocol = "https" if data[CONF_SSL] else "http"
        url = f"{protocol}://{data[CONF_HOST]}"
        session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])
    elif CONF_SSL in data and CONF_HOST in data:
        url = {data[CONF_HOST]}
        protocol = "https" if data[CONF_SSL] else "http"
        if "://" not in url:
            url = f"{protocol}://{data[CONF_HOST]}"
        session = async_get_clientsession(hass, verify_ssl=data[CONF_VERIFY_SSL])
    am = data[CONF_ACCESS]
    if am == "speedwire":
        am = "speedwireem"

    _LOGGER.info(
        f"Creating new pysma-Device [Session: {(session is not None)}, Verify-SSL: {data[CONF_VERIFY_SSL]}, Url: {url}, User/Group: {data[CONF_GROUP]}, Accessmethod: {am}]"
    )
    sma = pysma.getDevice(
        session,
        url,
        password=data[CONF_PASSWORD],
        groupuser=data[CONF_GROUP],
        accessmethod=am,
    )

    # Options for Speedwire
    if am == "speedwireinv":
        # set_options replaces the entire dict, so build it in one call
        options: dict = {"overallTimeout": 15}  # default 5s is too tight; inverters take 3-5s
        retries = data.get(CONF_RETRIES, 0)
        if (retries > 0):
            _LOGGER.info(f"Login retries: {retries}")
            options["loginRetries"] = retries
        sma.set_options(options)

    # Adding Bindingaddresses for energy meter multicast
    if am == "speedwireem":
        addrs = []
        adapters = await network.async_get_adapters(hass)
        for adapter in adapters:
            for ip_info in adapter["ipv4"]:
                addrs.append(ip_info["address"])
        _LOGGER.info("Binding Addr: " + ",".join(addrs))
        sma.set_options({"bindingaddr": ",".join(addrs)})
    return sma


async def getPysmaInstance(hass: HomeAssistant, data: dict[str, Any]) -> Device:
    """Returns a connected pysma Instance."""
    sma = await _create_sma_device(hass, data)
    last_exc = None
    for attempt in range(3):
        try:
            await sma.new_session()
            return sma
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                _LOGGER.warning(f"Session attempt {attempt + 1}/3 failed ({type(exc).__name__}: {exc}), retrying in 3s...")
                await asyncio.sleep(3)
    raise last_exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up sma from a config entry."""
    sma = await _create_sma_device(hass, entry.data)
    sma_device_info = None
    sensor_def = None
    last_exc = None

    for attempt in range(5):
        try:
            await sma.new_session()
            device_list = await sma.device_list()
            sma_device_info = device_list[entry.data[CONF_DEVICE]]
            _LOGGER.info(
                f"Device info: name={sma_device_info.name}, type={sma_device_info.type}, serial={sma_device_info.serial}"
            )
            # On a cold boot the inverter sometimes returns SusyId=0 ("Unknown device (0)").
            # Retry so we get the real device info and the correct sensor list.
            if "Unknown" in (sma_device_info.name or "") or "Unknown" in (sma_device_info.type or ""):
                raise Exception(
                    f"Incomplete device info returned ({sma_device_info.name}/{sma_device_info.type}), will retry"
                )
            sensor_def = await sma.get_sensors(entry.data[CONF_DEVICE])
            _LOGGER.info(
                f"Setup successful, {len(sensor_def)} sensors loaded: "
                + ", ".join(s.name for s in sensor_def)
            )
            last_exc = None
            break
        except Exception as exc:
            last_exc = exc
            _LOGGER.warning(f"Setup attempt {attempt + 1}/5 failed ({type(exc).__name__}: {exc}), retrying in 5s...")
            try:
                await sma.close_session()
            except Exception:
                pass
            if attempt < 4:
                await asyncio.sleep(5)
                sma = await _create_sma_device(hass, entry.data)

    if last_exc is not None:
        raise ConfigEntryNotReady from last_exc

    if TYPE_CHECKING:
        assert entry.unique_id

    # Create HA-DeviceInfo object from sma_device_info
    device_info = DeviceInfo(
        #        configuration_url=url,
        configuration_url=None,
        identifiers={(DOMAIN, entry.unique_id)},
        manufacturer=sma_device_info.manufacturer,
        model=sma_device_info.type,
        name=sma_device_info.name,
        sw_version=sma_device_info.sw_version,
    )

    consecutive_failures = 0

    # Define the coordinator
    async def async_update_data():
        """Update the used SMA sensors."""
        nonlocal sma, consecutive_failures
        try:
            _LOGGER.info(f"Update pysma {entry.data[CONF_HOST]}/{entry.data[CONF_ACCESS]}/{entry.data[CONF_DEVICE]}")
            await sma.read(sensor_def, entry.data[CONF_DEVICE])
            consecutive_failures = 0
        except (
            pysma.exceptions.SmaReadException,
            pysma.exceptions.SmaConnectionException,
            TimeoutError
        ) as exc:
            _LOGGER.warning(f"Update Failed {type(exc)} {entry.data[CONF_HOST]}/{entry.data[CONF_ACCESS]}/{entry.data[CONF_DEVICE]}, attempting reconnect...")
            try:
                try:
                    await sma.close_session()
                except Exception:
                    pass
                # pysmaplus close_session() has a typo (_trasport vs _transport) that
                # leaves the transport reference alive, causing zombie socket sends.
                # Clear both attrs so the new session starts from a clean state.
                for _attr in ("_transport", "_protocol"):
                    try:
                        setattr(sma, _attr, None)
                    except Exception:
                        pass
                # Give the inverter 2 s to release its session slot after logoff,
                # reducing interference from in-flight retransmit packets.
                await asyncio.sleep(2)
                sma = await getPysmaInstance(hass, entry.data)
                if entry.entry_id in hass.data.get(DOMAIN, {}):
                    hass.data[DOMAIN][entry.entry_id][PYSMA_OBJECT] = sma
                await sma.read(sensor_def, entry.data[CONF_DEVICE])
                _LOGGER.info(f"Reconnect successful {entry.data[CONF_HOST]}/{entry.data[CONF_ACCESS]}/{entry.data[CONF_DEVICE]}")
                consecutive_failures = 0
            except Exception as reconnect_exc:
                consecutive_failures += 1
                _LOGGER.warning(f"Reconnect also failed ({consecutive_failures}) {type(reconnect_exc)} {entry.data[CONF_HOST]}/{entry.data[CONF_ACCESS]}/{entry.data[CONF_DEVICE]}")
                _LOGGER.warning(exc, exc_info=True)
                if consecutive_failures >= 3:
                    _LOGGER.warning(f"Scheduling config entry reload after {consecutive_failures} consecutive failures {entry.data[CONF_HOST]}")
                    consecutive_failures = 0
                    hass.async_create_task(hass.config_entries.async_reload(entry.entry_id))
                raise UpdateFailed(exc) from exc
        except Exception as e:
            _LOGGER.warning(f"Update Failed. Unfetched Exception {type(e)} {entry.data[CONF_HOST]}/{entry.data[CONF_ACCESS]}/{entry.data[CONF_DEVICE]}")



    interval = timedelta(
        seconds=entry.options.get(CONF_SCAN_INTERVAL, entry.data[CONF_SCAN_INTERVAL])
    )

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="pysmaplus",
        update_method=async_update_data,
        update_interval=interval,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        await sma.close_session()
        raise

    # Ensure we logout on shutdown
    async def async_close_session(event):
        """Close the session."""
        await sma.close_session()

    remove_stop_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, async_close_session
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        PYSMA_OBJECT: sma,
        PYSMA_COORDINATOR: coordinator,
        PYSMA_SENSORS: sensor_def,
        PYSMA_REMOVE_LISTENER: remove_stop_listener,
        PYSMA_DEVICE_INFO: device_info,
        PYSMA_ENTITIES: [],
        PYSMA_DEVICEID: entry.data[CONF_DEVICE],
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # The first coordinator refresh ran before entities were subscribed, so they
    # never received a callback.  Refresh again now so all entities immediately
    # get fresh data pushed via the coordinator, instead of waiting scan_interval
    # seconds and showing stale/unavailable state restored from the DB.
    await coordinator.async_refresh()

    setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data[PYSMA_OBJECT].close_session()
        data[PYSMA_REMOVE_LISTENER]()

    return unload_ok


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.error(
        "Migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    if config_entry.version > 2:
        return False

    if config_entry.version == 1:

        # Add Device and Scan_interval to config
        new_data = {**config_entry.data}
        sma = await getPysmaInstance(hass, new_data)
        device_info = await sma.device_info()
        await sma.close_session()
        if "id" not in device_info:
            _LOGGER.error("Can not migrate! %s %s", config_entry, device_info)
            return False
        new_data[CONF_DEVICE] = device_info["id"]
        new_data[CONF_SCAN_INTERVAL] = 5
        hass.config_entries.async_update_entry(
            config_entry, data=new_data, minor_version=0, version=2
        )

        _LOGGER.error(
            "Migration to configuration version %s.%s successful",
            config_entry.version,
            config_entry.minor_version,
        )
    return True
