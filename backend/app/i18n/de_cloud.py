"""German for cloud storage (doc 147) and exports (docs 138, 142-146): the messages a
user reads in the error envelope, a connection test, or an export's refusal."""

from __future__ import annotations

ENTRIES: dict[str, str] = {
    "The credentials were refused for {where}. Check the key and secret. ({*detail})": (
        "Die Zugangsdaten wurden für {where} abgelehnt. Prüf Schlüssel und Secret. ({*detail})"
    ),
    "The credentials work but may not read {where}. ({*detail})": (
        "Die Zugangsdaten funktionieren, dürfen {where} aber nicht lesen. ({*detail})"
    ),
    "{where} does not exist, or this account cannot see it. ({*detail})": (
        "{where} gibt es nicht, oder dieses Konto sieht es nicht. ({*detail})"
    ),
    "{where} changed since it was last read. ({*detail})": (
        "{where} hat sich seit dem letzten Lesen geändert. ({*detail})"
    ),
    "The storage could not be reached. Check the endpoint and the network. ({*detail})": (
        "Der Speicher war nicht erreichbar. Prüf Endpunkt und Netzwerk. ({*detail})"
    ),
    "{where} is in another region than the connection says. ({*detail})": (
        "{where} liegt in einer anderen Region, als die Verbindung angibt. ({*detail})"
    ),
    "The storage refused the request for {where}. ({*detail})": (
        "Der Speicher hat die Anfrage für {where} abgelehnt. ({*detail})"
    ),
    "Connected to {where}: it holds files (for example {key}).": (
        "Verbunden mit {where}: Es enthält Dateien (zum Beispiel {key})."
    ),
    "Connected to {where}; it is empty.": "Verbunden mit {where}; es ist leer.",
    "The connection's settings were refused: {*error}": (
        "Die Einstellungen der Verbindung wurden abgelehnt: {*error}"
    ),
    "A {kind} connection has no {parts}.": "Eine {kind}-Verbindung hat kein {parts}.",
    "Azure needs the storage account's name.": "Azure braucht den Namen des Speicherkontos.",
    "The endpoint must start with http:// or https://.": (
        "Der Endpunkt muss mit http:// oder https:// beginnen."
    ),
    "The service account key is neither JSON nor base64 of it.": (
        "Der Service-Account-Schlüssel ist weder JSON noch dessen Base64."
    ),
    "The service account key is not valid JSON.": (
        "Der Service-Account-Schlüssel ist kein gültiges JSON."
    ),
    'This JSON is not a service account key (its "type" is not service_account).': (
        'Dieses JSON ist kein Service-Account-Schlüssel (sein "type" ist nicht service_account).'
    ),
    "A connection keeps its kind; add a new one instead.": (
        "Eine Verbindung behält ihre Art; leg stattdessen eine neue an."
    ),
    "No cloud connection {connection}": "Keine Cloud-Verbindung {connection}",
    "Cannot write to {target}: {*error}": "In {target} kann nicht geschrieben werden: {*error}",
    "This dataset has no export target yet. Choose where it goes first.": (
        "Dieser Datensatz hat noch kein Exportziel. Leg zuerst fest, wohin er geht."
    ),
    (
        "This dataset's pictures live inside the app, so 'with the data' would be removed with it. "
        "Choose a folder."
    ): (
        "Die Bilder dieses Datensatzes liegen in der App; „bei den Daten“ würde mit ihr "
        "entfernt. Wähle einen Ordner."
    ),
    "Choose the folder to export to.": "Wähle den Ordner, in den exportiert wird.",
    "'With the data' is not available for this dataset any more.": (
        "„Bei den Daten“ gibt es für diesen Datensatz nicht mehr."
    ),
    "Choose a full folder path, not {path}.": (
        "Gib einen vollständigen Ordnerpfad an, nicht {path}."
    ),
    "{file} is not a V-Rex export.": "{file} ist kein V-Rex-Export.",
    "The export names a picture outside its folder: {path}.": (
        "Der Export nennt ein Bild außerhalb seines Ordners: {path}."
    ),
    "The export is damaged: {table} points at a missing {target} row.": (
        "Der Export ist beschädigt: {table} verweist auf eine fehlende Zeile in {target}."
    ),
    "Not enough free disk space: {#needed} MB needed, {#free} MB free.": (
        "Nicht genug freier Speicherplatz: {#needed} MB nötig, {#free} MB frei."
    ),
    (
        "The download server answered {#code}. Download it by hand from the portal and import the "
        "folder."
    ): (
        "Der Download-Server hat mit {#code} geantwortet. Lade den Datensatz von Hand im Portal"
        " und importiere den Ordner."
    ),
    "The download broke off ({*error}). Try again.": (
        "Der Download ist abgebrochen ({*error}). Versuch es noch einmal."
    ),
    "The download ended in the middle of the archive.": "Der Download endete mitten im Archiv.",
    # Doc 149: a linked picture neither cached nor reachable
    "{name} is not in the cache, and {bucket} could not be read: {*error}": (
        "{name} liegt nicht im Cache, und {bucket} konnte nicht gelesen werden: {*error}"
    ),
    # Doc 150: a save-back that met a newer export
    (
        "Someone else saved annotations to {where} since your last export. "
        "Nothing was overwritten: yours is at {copy}."
    ): (
        "Jemand anderes hat seit deinem letzten Export Annotationen nach {where} gespeichert. "
        "Nichts wurde überschrieben: Deine liegen unter {copy}."
    ),
}
