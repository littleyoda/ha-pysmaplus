With enneox-OS based devices, it is possible to change selected parameters via Service Call.

<img valign="top" src="images/set_parameter.png" width="50%"/><img valign="top" src="images/get_settings.png" width="50%"/>

Currently supported parameters:

| Interface | Sensor  | SMA-Name / Description |
|---|---|--|
| ennexos  | Inverter Power Limit | Set active power limit<br> Parameter.Inverter.WMax<br>same as Modbus 30233
| webconnect  | Active Power Limitation | Set active power limit<br> Parameter.Inverter.WMax<br>same as Modbus 30233
| webconnect  | Operating Mode | Switching the system on and off

As a Tripower X device has over 400 parameters, I will not implement all of them. For additional parameters, please open an issue and briefly describe what you need the parameter for. 

Devices via Speedwire cannot be changed due to the lack of a specification. Here I refer to the use of Modbus.
