# Known problems
## No measured values overnight
Some inverters do not respond to Speedwire requests at night and the integration reports an error. Actually, the error management of HA should ensure that the queries continue to run and that everything works normally again after sunrise.
But sometimes the integration has to be restarted in the morning manually.

Cause: unclear

## No connection via Speedwire
Sometimes inverters that support Speedwire cannot be queried at all. 
In other cases, the problem suddenly appears after a restart or an update. It can also suddenly disappear again.


Cause: unclear

Approaches to solutions: To debug the problem, I would need access to an affected inverter. (Linux VM that is accessible via SSH)


## Lost connections
Sometimes the integration does not deliver any measured values until the integration is restarted. This can happen during the day, but more often after an HA restart.

Cause: unclear
