# Supported Devices

see [Supported Devices Page](supported_devices.md)

# entities

# How can I change the refresh rate?

By default, the values are retrieved every 5 seconds. This time can be reduced to one second.

However, the HA developers warn against low refresh rates, as they can overload older or slower systems. The update speed should only be reduced gradually and carefully.

# How can create dashboard?
see [Dashboard Page](dashboard.md)


# Can I also change the inverter setting? 
see [Set Parameter Page](set_parameter.md)

# EM/SHM2: I do not receive multicast packets
see [SHM2 Multicast](shm2_multicast.md)

# Speedwire (Inverter and battery storage)
SMA does not provide any freely available documentation for speedwire in connection with inverters and battery storage. Therefore, the entire implementation has been created by reverse engineering and cannot cover all cases.

## No measured values overnight
Some inverters do not respond to Speedwire requests at night and the integration reports an error. Actually, the error management of HA should ensure that the queries continue to run and that everything works normally again after sunrise.
But sometimes the integration has to be restarted in the morning manually.

Cause: unclear

## No connection via Speedwire
Sometimes inverters that support Speedwire cannot be queried at all. 

Cause: unclear

## Lost connections
Sometimes the integration does not deliver any measured values until the integration is restarted. This can happen during the day, but more often after an HA restart.

Cause: unclear


# Ennexos Interface: No sensors
If a device is successfully added via the enneox-interface but no sensors are displayed, it is probably a new device for which the sensor information has not yet been stored.
In this case, please send the [diagnostic information](diagnosticsinformation.md) for the device to the author.

# Current consumption
There is no sensor for the current consumption of the house.
However, the value can be calculated using a [template sensor](https://www.home-assistant.io/integrations/template/) in Home Assistant.

The general formula (without battery) is: production + grid consumption - grid feed-in.

The sensors for this are named as follows
pv/grid_power + metering_power_absorbed - metering_power_supplied

An example could look like this:
```
template:
  - sensor:
      - name: "power_total_usage"
        state: "{{ (states('sensor.sunny_tripower_x_15_pv_power')|int(0) -  states('sensor.sunny_home_manager_2_metering_power_supplied')|int(0) + states('sensor.sunny_home_manager_2_metering_power_absorbed')|int(0)) }}"
        unit_of_measurement: "W"
        state_class: measurement
```
