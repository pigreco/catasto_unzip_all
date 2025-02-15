
# Descrizione contenuto cartella

## file pyQGIS

- catasto_unzip_merge_prov.py
- console_qgis_download.py
- get_parcel_info_wfs.py
- get_particella_by_codes.py
- particella_clic.py

### catasto_unzip_merge_prov

lo script `catasto_unzip_merg_prov.py` modifica lo script `console_qgis_download.py`, inserendo la possibilità di scegliere se procedere per singola regione o singola provincia (dando la possibilità di scelta). 
L'output è limitato al formato `*.gpkg`.
Lo script cancella sempre i file temporanei creati nelle elaborazioni.


### console_qgis_download

lo script console permette di scaricare e mergiare i dati catastali rilasciati tramite cartelle zip

### get_parcel_info_wfs

funzione personalizzata per il field calc

### get_particella_by_codes

funzione personalizzata per il field calc

### particella_clic

script console che scarica singola particella per ogni clic sulla mappa

