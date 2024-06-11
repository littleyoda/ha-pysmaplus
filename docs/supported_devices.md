# Supported Devices
This integration enables access to various devices (inverters, battery storage systems) from SMA.

As each device provides different interfaces, the interface to be used must be selected for this integration.

## Webconnect
This is the access type used in the current SMA integration of Home Assistant. The values are retrieved via the web interface of the device from the webconnect generation.

Devices: e.g. Sunny Tripower Smart Energy , Sunny Boy Storage


# EnnexOS
The new devices (Tripower X and EVCharger) from SMA primarily use the Ennex operating system. A web server that supplies the values is available. As the web interface has changed completely compared to Webconnect, a new adapter had to be written to retrieve the data.

Devices: Tripower X and EVCharger


# Speedwire EM
The SHM2 and the Engerymeter transmit the data automatically via multicast in Speedwire format. The programs only have to listen to the network traffic and can then decode the values. SMA has now disclosed the format for this one message format.

Devices: Energymeter + Sunny Home Manager 2


# Speedwire
Almost all(?) SMA devices support communication via Speedwire as standard. However, this protocol is not disclosed and a few people have tried to decode at least the unencrypted version of the protocol.

Requirements: The Speedwire encryption must be n