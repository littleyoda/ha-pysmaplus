"""SMA Solar Webconnect interface."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pysmaplus as pysma

import logging
import math

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfReactivePower,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    PYSMA_COORDINATOR,
    PYSMA_DEVICE_INFO,
    PYSMA_OBJECT,
    PYSMA_SENSORS,
    PYSMA_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)

SENSOR_ENTITIES: dict[str, SensorEntityDescription] = {
    "status": SensorEntityDescription(
        key="status",
        name="Status",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "operating_status_general": SensorEntityDescription(
        key="operating_status_general",
        name="Operating Status General",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "inverter_condition": SensorEntityDescription(
        key="inverter_condition",
        name="Inverter Condition",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "inverter_system_init": SensorEntityDescription(
        key="inverter_system_init",
        name="Inverter System Init",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "grid_connection_status": SensorEntityDescription(
        key="grid_connection_status",
        name="Grid Connection Status",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "grid_relay_status": SensorEntityDescription(
        key="grid_relay_status",
        name="Grid Relay Status",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "pv_power_a": SensorEntityDescription(
        key="pv_power_a",
        name="PV Power A",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "pv_power_b": SensorEntityDescription(
        key="pv_power_b",
        name="PV Power B",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "pv_power_c": SensorEntityDescription(
        key="pv_power_c",
        name="PV Power C",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "pv_total_power_a": SensorEntityDescription(
        key="pv_total_power_a",
        name="PV Total Power A",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    "pv_total_power_b": SensorEntityDescription(
        key="pv_total_power_b",
        name="PV Total Power B",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    "pv_total_power_c": SensorEntityDescription(
        key="pv_total_power_c",
        name="PV Total Power C",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    "pv_voltage_a": SensorEntityDescription(
        key="pv_voltage_a",
        name="PV Voltage A",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "pv_voltage_b": SensorEntityDescription(
        key="pv_voltage_b",
        name="PV Voltage B",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "pv_voltage_c": SensorEntityDescription(
        key="pv_voltage_c",
        name="PV Voltage C",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "pv_current_a": SensorEntityDescription(
        key="pv_current_a",
        name="PV Current A",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "pv_current_b": SensorEntityDescription(
        key="pv_current_b",
        name="PV Current B",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "pv_current_c": SensorEntityDescription(
        key="pv_current_c",
        name="PV Current C",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "pv_isolation_resistance": SensorEntityDescription(
        key="pv_isolation_resistance",
        name="PV Isolation Resistance",
        native_unit_of_measurement="kOhms",
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    "insulation_residual_current": SensorEntityDescription(
        key="insulation_residual_current",
        name="Insulation Residual Current",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "pv_power": SensorEntityDescription(
        key="pv_power",
        name="PV Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "grid_power": SensorEntityDescription(
        key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "frequency": SensorEntityDescription(
        key="frequency",
        name="Frequency",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.FREQUENCY,
        entity_registry_enabled_default=False,
    ),
    "power_l1": SensorEntityDescription(
        key="power_l1",
        name="Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "power_l2": SensorEntityDescription(
        key="power_l2",
        name="Power L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "power_l3": SensorEntityDescription(
        key="power_l3",
        name="Power L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_reactive_power": SensorEntityDescription(
        key="grid_reactive_power",
        name="Grid Reactive Power",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_reactive_power_l1": SensorEntityDescription(
        key="grid_reactive_power_l1",
        name="Grid Reactive Power L1",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_reactive_power_l2": SensorEntityDescription(
        key="grid_reactive_power_l2",
        name="Grid Reactive Power L2",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_reactive_power_l3": SensorEntityDescription(
        key="grid_reactive_power_l3",
        name="Grid Reactive Power L3",
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.REACTIVE_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_apparent_power": SensorEntityDescription(
        key="grid_apparent_power",
        name="Grid Apparent Power",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.APPARENT_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_apparent_power_l1": SensorEntityDescription(
        key="grid_apparent_power_l1",
        name="Grid Apparent Power L1",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.APPARENT_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_apparent_power_l2": SensorEntityDescription(
        key="grid_apparent_power_l2",
        name="Grid Apparent Power L2",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.APPARENT_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_apparent_power_l3": SensorEntityDescription(
        key="grid_apparent_power_l3",
        name="Grid Apparent Power L3",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.APPARENT_POWER,
        entity_registry_enabled_default=False,
    ),
    "grid_power_factor": SensorEntityDescription(
        key="grid_power_factor",
        name="Grid Power Factor",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER_FACTOR,
        entity_registry_enabled_default=False,
    ),
    "grid_power_factor_excitation": SensorEntityDescription(
        key="grid_power_factor_excitation",
        name="Grid Power Factor Excitation",
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "current_l1": SensorEntityDescription(
        key="current_l1",
        name="Current L1",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "current_l2": SensorEntityDescription(
        key="current_l2",
        name="Current L2",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "current_l3": SensorEntityDescription(
        key="current_l3",
        name="Current L3",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "current_total": SensorEntityDescription(
        key="current_total",
        name="Current Total",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "voltage_l1": SensorEntityDescription(
        key="voltage_l1",
        name="Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "voltage_l2": SensorEntityDescription(
        key="voltage_l2",
        name="Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "voltage_l3": SensorEntityDescription(
        key="voltage_l3",
        name="Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "total_yield": SensorEntityDescription(
        key="total_yield",
        name="Total Yield",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "daily_yield": SensorEntityDescription(
        key="daily_yield",
        name="Daily Yield",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "temp_a": SensorEntityDescription(
        key="temp_a",
        name="Temp A",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "temp_b": SensorEntityDescription(
        key="temp_b",
        name="Temp B",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "temp_c": SensorEntityDescription(
        key="temp_c",
        name="Temp C",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "metering_power_supplied": SensorEntityDescription(
        key="metering_power_supplied",
        name="Metering Power Supplied",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_power_absorbed": SensorEntityDescription(
        key="metering_power_absorbed",
        name="Metering Power Absorbed",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_frequency": SensorEntityDescription(
        key="metering_frequency",
        name="Metering Frequency",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.FREQUENCY,
    ),
    "metering_total_yield": SensorEntityDescription(
        key="metering_total_yield",
        name="Metering Total Yield",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "metering_total_absorbed": SensorEntityDescription(
        key="metering_total_absorbed",
        name="Metering Total Absorbed",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "metering_current_l1": SensorEntityDescription(
        key="metering_current_l1",
        name="Metering Current L1",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "metering_current_l2": SensorEntityDescription(
        key="metering_current_l2",
        name="Metering Current L2",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "metering_current_l3": SensorEntityDescription(
        key="metering_current_l3",
        name="Metering Current L3",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "metering_voltage_l1": SensorEntityDescription(
        key="metering_voltage_l1",
        name="Metering Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "metering_voltage_l2": SensorEntityDescription(
        key="metering_voltage_l2",
        name="Metering Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "metering_voltage_l3": SensorEntityDescription(
        key="metering_voltage_l3",
        name="Metering Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "metering_active_power_feed_l1": SensorEntityDescription(
        key="metering_active_power_feed_l1",
        name="Metering Active Power Feed L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_active_power_feed_l2": SensorEntityDescription(
        key="metering_active_power_feed_l2",
        name="Metering Active Power Feed L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_active_power_feed_l3": SensorEntityDescription(
        key="metering_active_power_feed_l3",
        name="Metering Active Power Feed L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_active_power_draw_l1": SensorEntityDescription(
        key="metering_active_power_draw_l1",
        name="Metering Active Power Draw L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_active_power_draw_l2": SensorEntityDescription(
        key="metering_active_power_draw_l2",
        name="Metering Active Power Draw L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_active_power_draw_l3": SensorEntityDescription(
        key="metering_active_power_draw_l3",
        name="Metering Active Power Draw L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "metering_current_consumption": SensorEntityDescription(
        key="metering_current_consumption",
        name="Metering Current Consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "metering_total_consumption": SensorEntityDescription(
        key="metering_total_consumption",
        name="Metering Total Consumption",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "pv_gen_meter": SensorEntityDescription(
        key="pv_gen_meter",
        name="PV Gen Meter",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "sps_voltage": SensorEntityDescription(
        key="sps_voltage",
        name="Secure Power Supply Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "sps_current": SensorEntityDescription(
        key="sps_current",
        name="Secure Power Supply Current",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "sps_power": SensorEntityDescription(
        key="sps_power",
        name="Secure Power Supply Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "optimizer_power": SensorEntityDescription(
        key="optimizer_power",
        name="Optimizer Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "optimizer_current": SensorEntityDescription(
        key="optimizer_current",
        name="Optimizer Current",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        entity_registry_enabled_default=False,
    ),
    "optimizer_voltage": SensorEntityDescription(
        key="optimizer_voltage",
        name="Optimizer Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "optimizer_temp": SensorEntityDescription(
        key="optimizer_temp",
        name="Optimizer Temp",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        entity_registry_enabled_default=False,
    ),
    "battery_soc_total": SensorEntityDescription(
        key="battery_soc_total",
        name="Battery SOC Total",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
    ),
    "battery_soc_a": SensorEntityDescription(
        key="battery_soc_a",
        name="Battery SOC A",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        entity_registry_enabled_default=False,
    ),
    "battery_soc_b": SensorEntityDescription(
        key="battery_soc_b",
        name="Battery SOC B",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        entity_registry_enabled_default=False,
    ),
    "battery_soc_c": SensorEntityDescription(
        key="battery_soc_c",
        name="Battery SOC C",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        entity_registry_enabled_default=False,
    ),
    "battery_voltage_a": SensorEntityDescription(
        key="battery_voltage_a",
        name="Battery Voltage A",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_voltage_b": SensorEntityDescription(
        key="battery_voltage_b",
        name="Battery Voltage B",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_voltage_c": SensorEntityDescription(
        key="battery_voltage_c",
        name="Battery Voltage C",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_current_a": SensorEntityDescription(
        key="battery_current_a",
        name="Battery Current A",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "battery_current_b": SensorEntityDescription(
        key="battery_current_b",
        name="Battery Current B",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "battery_current_c": SensorEntityDescription(
        key="battery_current_c",
        name="Battery Current C",
        suggested_display_precision=1,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
    ),
    "battery_temp_a": SensorEntityDescription(
        key="battery_temp_a",
        name="Battery Temp A",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "battery_temp_b": SensorEntityDescription(
        key="battery_temp_b",
        name="Battery Temp B",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "battery_temp_c": SensorEntityDescription(
        key="battery_temp_c",
        name="Battery Temp C",
        suggested_display_precision=0,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "battery_status_operating_mode": SensorEntityDescription(
        key="battery_status_operating_mode",
        name="Battery Status Operating Mode",
    ),
    "battery_capacity_total": SensorEntityDescription(
        key="battery_capacity_total",
        name="Battery Capacity Total",
        native_unit_of_measurement=PERCENTAGE,
    ),
    "battery_capacity_a": SensorEntityDescription(
        key="battery_capacity_a",
        name="Battery Capacity A",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_capacity_b": SensorEntityDescription(
        key="battery_capacity_b",
        name="Battery Capacity B",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_capacity_c": SensorEntityDescription(
        key="battery_capacity_c",
        name="Battery Capacity C",
        native_unit_of_measurement=PERCENTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_charging_voltage_a": SensorEntityDescription(
        key="battery_charging_voltage_a",
        name="Battery Charging Voltage A",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_charging_voltage_b": SensorEntityDescription(
        key="battery_charging_voltage_b",
        name="Battery Charging Voltage B",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_charging_voltage_c": SensorEntityDescription(
        key="battery_charging_voltage_c",
        name="Battery Charging Voltage C",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_registry_enabled_default=False,
    ),
    "battery_power_charge_total": SensorEntityDescription(
        key="battery_power_charge_total",
        name="Battery Power Charge Total",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "battery_power_charge_a": SensorEntityDescription(
        key="battery_power_charge_a",
        name="Battery Power Charge A",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_power_charge_b": SensorEntityDescription(
        key="battery_power_charge_b",
        name="Battery Power Charge B",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_power_charge_c": SensorEntityDescription(
        key="battery_power_charge_c",
        name="Battery Power Charge C",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_charge_total": SensorEntityDescription(
        key="battery_charge_total",
        name="Battery Charge Total",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "battery_charge_a": SensorEntityDescription(
        key="battery_charge_a",
        name="Battery Charge A",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "battery_charge_b": SensorEntityDescription(
        key="battery_charge_b",
        name="Battery Charge B",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "battery_charge_c": SensorEntityDescription(
        key="battery_charge_c",
        name="Battery Charge C",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "battery_power_discharge_total": SensorEntityDescription(
        key="battery_power_discharge_total",
        name="Battery Power Discharge Total",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "battery_power_discharge_a": SensorEntityDescription(
        key="battery_power_discharge_a",
        name="Battery Power Discharge A",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_power_discharge_b": SensorEntityDescription(
        key="battery_power_discharge_b",
        name="Battery Power Discharge B",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_power_discharge_c": SensorEntityDescription(
        key="battery_power_discharge_c",
        name="Battery Power Discharge C",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        entity_registry_enabled_default=False,
    ),
    "battery_discharge_total": SensorEntityDescription(
        key="battery_discharge_total",
        name="Battery Discharge Total",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
    ),
    "battery_discharge_a": SensorEntityDescription(
        key="battery_discharge_a",
        name="Battery Discharge A",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "battery_discharge_b": SensorEntityDescription(
        key="battery_discharge_b",
        name="Battery Discharge B",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "battery_discharge_c": SensorEntityDescription(
        key="battery_discharge_c",
        name="Battery Discharge C",
        suggested_display_precision=2,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    ),
    "inverter_power_limit": SensorEntityDescription(
        key="inverter_power_limit",
        name="Inverter Power Limit",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "active_power_limitation": SensorEntityDescription(
        key="active_power_limitation",
        name="Active Power Limitation",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "power_limit_via_io": SensorEntityDescription(
        key="power_limit_via_io",
        name="Power Limit (IO)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "operating_mode_plant_control": SensorEntityDescription(
        key="operating_mode_plant_control",
        name="Operating Mode Plant Control",
    ),
    "operating_mode": SensorEntityDescription(
        key="operating_mode",
        name="Operating Mode",
    ),
    "power_setpoint_plant_control": SensorEntityDescription(
        key="power_setpoint_plant_control",
        name="Power Setpoint Plant Control",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "active_power_limitation_gcp": SensorEntityDescription(
        key="active_power_limitation_gcp",
        name="Active Power Limitation (GCP)",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA sensors."""
    sma_data = hass.data[DOMAIN][config_entry.entry_id]

    coordinator = sma_data[PYSMA_COORDINATOR]
    used_sensors = sma_data[PYSMA_SENSORS]
    device_info = sma_data[PYSMA_DEVICE_INFO]
    sma = sma_data[PYSMA_OBJECT]

    if TYPE_CHECKING:
        assert config_entry.unique_id

    unique_id = config_entry.unique_id

    # Track which channels already have an entity, so dynamic re-discovery never
    # creates a duplicate.
    #
    # ``known_keys`` is the primary guard, keyed by Sensor.key, because both the
    # live session mapping (``_AsyncSpeedwireSession.sensors``) and pysma
    # ``read()`` match on Sensor.key. It is seeded from EVERY sensor already in
    # the snapshot (not only the supported/entity-bearing ones): a key that the
    # snapshot already holds under some other name must never be re-added by the
    # listener, or ``Sensors.add()`` would create a second entry for that key.
    #
    # ``known_names`` is an extra guard, keyed by Sensor.name. A late-arriving
    # channel must never reuse a name that already has an entity, because
    # ``Sensors.add()`` REMOVES the existing same-name sensor object from the
    # collection (verified in pysma/sensor.py Sensors.add) -- that would orphan
    # the existing entity (read() would stop updating its now-detached Sensor).
    known_keys: set[str] = {
        key for sensor in used_sensors if (key := getattr(sensor, "key", None))
    }
    known_names: set[str] = set()

    entities = []
    for sensor in used_sensors:
        if sensor.name in SENSOR_ENTITIES:
            entities.append(
                SMAsensor(
                    coordinator,
                    unique_id,
                    SENSOR_ENTITIES.get(sensor.name),
                    device_info,
                    sensor,
                )
            )
            known_names.add(sensor.name)

    async_add_entities(entities)
    # ``used_sensors`` IS the PYSMA_SENSORS collection (read() iterates it); keep
    # a single, shared list of live entities in PYSMA_ENTITIES (services.py reads
    # it fresh from hass.data on every call). Reuse the existing list object if
    # one is present so any holder keeps seeing the current entity set.
    entity_list = sma_data.get(PYSMA_ENTITIES)
    if isinstance(entity_list, list):
        entity_list.clear()
        entity_list.extend(entities)
    else:
        entity_list = entities
        sma_data[PYSMA_ENTITIES] = entity_list

    @callback
    def _async_discover_new_sensors() -> None:
        """Add entities for supported sensors that appeared after setup.

        Runs on every coordinator update. When a Speedwire V2 inverter wakes up
        (e.g. at sunrise after a night-time restart) its live session regains
        the instantaneous channels (grid_power, pv_power_a/b, frequency, ...)
        that were missing from the one-time ``get_sensors()`` snapshot. The
        frozen snapshot and the entity set created at setup never catch up on
        their own, so those entities stay unavailable until a manual reload.

        For each newly seen, supported channel we add a copy of its Sensor into
        the PYSMA_SENSORS collection that ``read()`` iterates, then wrap that
        very copy in a new entity so it receives live values on every poll.

        Strategy: obtain the live sensor set through the no-poll
        ``current_sensors()`` accessor monkeypatched onto the Speedwire V2
        device class by ``_speedwire2_patch``. It is resolved defensively with
        ``getattr``: for any device type that does not provide it (webconnect,
        ennexos, em, shm2, speedwire) this is a safe no-op -- those device types
        already discover their full sensor set up front. The accessor performs
        no network I/O; it just reflects the mapping last refreshed by
        ``read()`` on each coordinator update.

        AddEntitiesCallback here is the schedule-a-task variant; calling it
        from a @callback is intentional and non-blocking. This whole body is
        wrapped in try/except so it can never raise inside async_update_listeners
        (which has no per-listener guard) and break the coordinator.
        """
        try:
            # Do not touch a half-torn-down entry. The unsubscribe registered
            # via async_on_unload only runs AFTER async_unload_platforms, so a
            # refresh that completes during unload could otherwise fire this
            # listener against state that is being closed.
            if config_entry.state is not ConfigEntryState.LOADED:
                return

            accessor = getattr(sma, "current_sensors", None)
            if accessor is None:
                # Device type without the no-poll accessor. Safe no-op.
                return
            try:
                live_sensors = accessor()
            except Exception:  # noqa: BLE001 - defensive, never break a poll
                _LOGGER.debug(
                    "pysmaplus dynamic discovery: accessor failed", exc_info=True
                )
                return
            if not live_sensors:
                return

            new_entities: list[SMAsensor] = []
            # Snapshot the list: the library mutates the underlying mapping from
            # its polling coroutine. ``current_sensors()`` already returns a
            # fresh list, but iterate over a local copy to be safe.
            for live_sensor in list(live_sensors):
                key = getattr(live_sensor, "key", None)
                if key is None or key in known_keys:
                    continue
                name = getattr(live_sensor, "name", None)
                if not name or name not in SENSOR_ENTITIES:
                    # Unknown / unsupported channel (no entity description).
                    # Mark the key handled so it is not re-scanned every cycle.
                    if key is not None:
                        known_keys.add(key)
                    continue
                if name in known_names:
                    # Never shadow an existing entity's name (would orphan it via
                    # Sensors.add name-replacement); mark the key as handled so
                    # we do not reconsider it every cycle.
                    _LOGGER.debug(
                        "pysmaplus dynamic discovery: name %s already has an "
                        "entity; not adding key %s",
                        name,
                        key,
                    )
                    known_keys.add(key)
                    continue

                # Add a copy into the snapshot collection read() iterates, then
                # fetch the stored copy back (Sensors.add() stores a copy.copy,
                # not the object passed in) and wrap THAT exact object so the
                # entity and read() share one Sensor instance.
                #
                # ``used_sensors[key]`` (pysma __getitem__) returns the first
                # sensor matching name OR key. This is unambiguous because no
                # speedwire channel's name equals another channel's key (and the
                # known_names/known_keys guards above prevent re-adding an
                # existing one). The ``stored.key == key`` assertion below
                # converts any future violation of that invariant into a logged
                # no-op rather than a silent mis-wire to the wrong channel.
                used_sensors.add(live_sensor)
                try:
                    stored = used_sensors[key]
                except KeyError:
                    _LOGGER.debug(
                        "pysmaplus dynamic discovery: %s missing after add", key
                    )
                    continue
                if getattr(stored, "key", None) != key:
                    _LOGGER.warning(
                        "pysmaplus dynamic discovery: lookup for %s returned %s; "
                        "skipping to avoid mis-wiring an entity",
                        key,
                        getattr(stored, "key", None),
                    )
                    known_keys.add(key)
                    continue

                entity = SMAsensor(
                    coordinator,
                    unique_id,
                    SENSOR_ENTITIES.get(name),
                    device_info,
                    stored,
                )
                new_entities.append(entity)
                known_keys.add(key)
                known_names.add(name)

            if new_entities:
                _LOGGER.info(
                    "pysmaplus: discovered %d new sensor(s) at runtime: %s",
                    len(new_entities),
                    ", ".join(sorted(e._sensor.key for e in new_entities)),
                )
                # Schedule-a-task variant of AddEntitiesCallback: safe to call
                # from this @callback. New entities carry disjoint unique_ids
                # from the initial batch (guarded by known_keys), so they cannot
                # double-add.
                async_add_entities(new_entities)
                entity_list.extend(new_entities)
        except Exception:  # noqa: BLE001 - must never break coordinator updates
            _LOGGER.exception("pysmaplus dynamic sensor discovery failed")

    # Run once now so a channel already present in the first poll (but absent
    # from the snapshot due to an earlier night-time discovery) is picked up
    # without waiting for the next coordinator tick.
    _async_discover_new_sensors()

    # Re-run on every coordinator update; unsubscribe on unload/reload.
    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_discover_new_sensors)
    )


class SMAsensor(CoordinatorEntity, SensorEntity):
    """Representation of a SMA sensor."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_unique_id: str,
        description: SensorEntityDescription | None,
        device_info: DeviceInfo,
        pysma_sensor: pysma.sensor.Sensor,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        if description is not None:
            self.entity_description = description
        else:
            self._attr_name = pysma_sensor.name

        self._sensor = pysma_sensor

        self._attr_device_info = device_info
        self._attr_unique_id = (
            f"{config_entry_unique_id}-{pysma_sensor.key}_{pysma_sensor.key_idx}"
        )

        # Set sensor enabled to False.
        # Will be enabled by async_added_to_hass if actually used.
        self._sensor.enabled = False

    @property
    def name(self) -> str:
        """Return the name of the sensor prefixed with the device name."""
        if self._attr_device_info is None or not (
            name_prefix := self._attr_device_info.get("name")
        ):
            name_prefix = "SMA"

        return f"{name_prefix} {super().name}"

    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        value = self._sensor.value
        if isinstance(value, str) and value.lower() == "nan":
            return None
        if isinstance(value, float):
            if math.isnan(value) or not math.isfinite(value):
                return None
        return value

    @property
    def extra_state_attributes(self):
        return {
            "textrepr": self._sensor.mapped_value if self._sensor.mapped_value else "",
        }

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        self._sensor.enabled = True

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await super().async_will_remove_from_hass()
        self._sensor.enabled = False
