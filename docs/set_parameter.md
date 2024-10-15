With some devices, it is possible to change selected parameters via Service Call.


Before changing a value, you should first check which values are allowed:
<img valign="top" src="images/get_settings.png" width="50%"/>

After that, you can change the parameter at your own risk:
<img valign="top" src="images/set_parameter.png" width="50%"/>

# Temporary zero feed-in
The following parameters have been successfully used by people to control the feed-in. This is helpful, for example, if the feed-in tariff is  negative at certain times. 


| Interface | Sensor  | SMA-Name / Description |
|---|---|--|
| ennexos  | Inverter Power Limit | Set active power limit<br> Parameter.Inverter.WMax<br>same as Modbus 30233
| webconnect  | Active Power Limitation | Set active power limit<br>Webconnect Code: 6802_00832B00<br>Parameter.Inverter.WMax<br>same as Modbus 30233
| webconnect  | Operating Mode | Switching the system on and off<br>Webconnect Code: 6800_08831E00<br>Operation.OpMod<br>same as Modbus 40009<br>Value 381: Stopp<br>1467: Start 
| webconnect  | Active Power Limitation GCP | Active Power limit at grid connection point<br>Webconnect Code 6800_0092D70<br>PCC.WMax

# Remark
As a Tripower X device or a webconnect device has over 400, some of them over 900, parameters, I will not implement all of them. For additional parameters, please open an issue and briefly describe what you need the parameter for. It is helpful if the webconnect code (e.g. 6802_00832B00) or enneoxos sensor name (e.g. Parameter.Inverter.WMax) is provided.
Devices via Speedwire cannot be changed due to the lack of a specification. Here I refer to the use of Modbus.
