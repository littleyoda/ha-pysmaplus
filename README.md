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

# Optional global settings (configuration.yaml)

To bypass Home Assistant's network adapter selection for Energy Meter / Sunny Home Manager 2 multicast connections (`speedwireem`), add:

```yaml
pysmaplus:
  energy_meter_bind_to_all_interfaces: true
```

This omits the `bindingaddr` option and uses the library's default binding to all interfaces. The setting applies to all Energy Meter / SHM2 multicast connections, including when adding devices. Restart Home Assistant after changing it. If omitted or set to `false`, only network adapters enabled in Home Assistant are used.


