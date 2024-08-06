If the SHM2 is not automatically recognized, the multicast packets of the SHM2 are usually not receive

What you can check:

* You could try the following add-on as a countercheck:
    https://github.com/kellerza/hassio-sma-em
* Check whether the SHM2 is set to multicast and not to unicast:
    Sunny Portal -- Configuration -- Device overview -- Parameters of the SHM2 ---Properties -- Edit
    The Unicast fields must be empty.


Three problem clusters have been observed so far:
* SHM2 is in a different subnet than Home Assistant
* Incorrect installation of HA in a Docker instance where the multicast packets are not forwarded.<br>I have not yet had any final feedback from users as to which option has helped them.
    Inadequate cabling

Possible solutions:
* Take care that Homeassisstnat is in the same subnet as the SHM/EM. 
* (Expert) Configure Docker appropriately
* (Expert) Use the SHM-Grid Code Interface.<br>However, I do not recommend it, as it provides significantly less information than the multicast variant.
* (Expert) Switch from multicast to unicast.<br>It must be ensured that every device that requires the information from the EM/SHM2 appears in the list. If more than 3 devices (including Home Assistant) require the information, this path is not possible.