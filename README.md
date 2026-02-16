The SMA integration currently available in Home Assistant only supports devices that use the Webconnect standard.

This integration supports almost all SMA devices like inverters, hybrid inverters, battery inverters and energy meters.


# Supported Devices
* (as before) Webconnect devices
* EnnexOS-based devices (currently e.g. Tripower X)
* Devices with a Speedwire-Interface
* Energy Meter (EMETER-10 + 20) and Sunny Home Manager 2

A list of devices that have been successfully tested can be found [here](https://github.com/littleyoda/pysma/blob/master/README.md)

Please see also the [Frequently Asked Questions](https://github.com/littleyoda/ha-pysmaplus/blob/main/docs/faq.md) of this integration, but also the 
[Frequently Asked Questions](https://github.com/littleyoda/pysma/blob/master/doc/faq_DE.md) of the underlying library.

# Installation
*   [HACS](https://www.hacs.xyz/) must be installed
* Then add the following integration via HACS "SMA Devices Plus"
* Restart HA
* Add your SMA devices based on the SMA Device Plus integration.
    (Settings / Devices & Services / Integrations)
* The Webconnect or Enneox options should be used for inverters. Speedwire can be used for older devices. Speedwire V2 is a fallback solution if all other solutions fail. 
* Not all entities are enabled automatically. You may have to enable them manually.

The Speedwire option does not work with every inverter.


