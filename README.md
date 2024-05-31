# ha-pysmaplus
Diese Intergration ermöglicht den Zugriff auf verschiedene Geräte (Wechselrichter, Batteriespeicher) von SMA.

Da jedes Geräte unterschiedliche Intnerfaces zur Verfügung stellt, muss bei dieser Integration ausgewählt werden, welches Interface gentutzw erden soll.

# Webconnect
Ist die Zugriffsart die in der aktuellen SMA Integration von Home Assistant genutzt wird. Hierbei werden die Werte über das Webinterface des Gerätes abgerufen.

Geräte: z.B. Sunny Tripower Smart Energy , Sunny Boy Storage


# EnnexOS
Die neuen Geräte (Tripower X und EVCharger) von SMA nutzen primär das Ennex-Betriebssystem. Ein Webserver, der die Werte liefert, ist vorhanden. Da das Webinterface sich im Vergleich zum Webconnect komplett geändert hat, musste ein neuer Adapter geschrieben werden, um die Daten abzurufen.

Geräte: Tripower X und EVCharger


# Speedwire EM
Der SHM2 und die Engerymeter übermittelt von sich aus die Daten per Multicast im Speedwire Format. Die Programme müssen hierbei nur auf den Netzwerktraffik lauschen und können die Werte dann dekodieren. Das Format für dieses eine Nachrichten Format hat SMA mittlerweile offen gelegt.

Geräte: Energymeter + Sunny Home Manager 2


# Speedwire
Fast alle(?) SMA Geräte unterstützen standardmäßig die Kommunikation per Speedwire. Dieses Protokoll ist aber nicht offen gelegt und ein paar Personen haben versucht, zumindest die unverschlüsselte Version des Protokolls zu dekodieren.

Voraussetzungen: Die Speedwire-Verschlüsselung darf nicht aktiviert werden. Defaultmäßig ist dieser für die Gruppe User auf 0000 und für die Grupper Installer auf 1111 eingestellt.

Geräte: alle, insbesondere Geräte, die von den anderen Interfaces nicht unterstützt werden z.B. Sunny Island


# Einschränkungen:

Da alle Interfaces, außer Energy Meter, ohne offizielle Unterlagen von SMA enträtselt wurden, kann es immer sein, dass etwas falsch interpretiert wurde. Außerdem sind die Interfaces im Zweifelsfall nicht vollständig. Gerade die Speedwire Implementierung ist noch unvollständig.

Speedwire hat aktuell den kleinsten Umfang an Sensoren, so dass EnnexOS oder Speedwire bevorzugt genutzt werden sollte.
Speedwire ist für die Geräte, die kein anderes Interface unterstützen, oder als Fallback.



