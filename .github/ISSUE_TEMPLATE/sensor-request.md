---
name: Sensor Request
about: Add an unmapped sensor.
title: "[New Sensor]"
labels: ''
assignees: littleyoda

---

**Please describe which sensor you need and why it should be made available in HA.**

**Identifier**
EnnexOS-based: Sensor name (like Parameter.Inverter.WLim or Measurement.Coolsys.Inverter.TmpVal)
Webconnect: Sensor key (like  6380_40451F00_1)
Speedwire: Information about the structure of the Speedwire response
Energymeter: OBIS-Number


## Everything below can be deleted after reading -

Due to the sheer number of sensors, not all of them are available to Home Assistant.

Depending on the interface/access method, the unmappend sensors can be found here:
Energy Meter / SHM2: https://github.com/littleyoda/pysma/blob/master/pysma/definitions_em.py
EnnexOS-based: https://github.com/littleyoda/pysma/blob/master/pysma/definitions_ennexos.py
