# Known problems
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
