The SMA integration currently available in Home Assistant only supports devices that use the Webconnect standard.

This integration supports almost all SMA devices like inverters, hybrid inverters, battery inverters and energy meters.


# Supported Devices
* (as before) Webconnect devices
* EnnexOS-based devices (currently e.g. Tripower X)
* Devices with a Speedwire-Interface
* Energy Meter (EMETER-10 + 20) and Sunny Home Manager 2

A list of devices that have been successfully tested can be found [here](https://github.com/littleyoda/pysma/blob/master/README.md)

Please see also the [Frequently Asked Questions](https://github.com/littleyoda/ha-pysmaplus/blob/main/docs/faq.md).

# Installation
*   HACS must be installed
*   You have to add my repository in HACS.
    https://github.com/littleyoda/ha-pysmaplus
* Then add the following integration via HACS
    SMA Devices Plus
* Restart HA
*  Add your SMA devices based on the SMA Device Plus integration.
    (Settings / Devices & Services / Integrations)
*   Not all entities are enabled
*    automatically. You may have to enable them manually.
