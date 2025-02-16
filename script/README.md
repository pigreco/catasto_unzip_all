
# Descrizione contenuto cartella

## file pyQGIS

- catasto_unzip_merge_prov.py
- console_qgis_download.py
- download_fogli_bbox.py
- download_particelle_bbox.py
- get_parcel_info_wfs.py
- get_particella_by_codes.py
- particella_clic.py
- wfs_catasto_clic_pla_multi.py
- wfs_catasto_clic_pla.py

### catasto_unzip_merge_prov

lo script `catasto_unzip_merg_prov.py` modifica lo script `console_qgis_download.py`, inserendo la possibilità di scegliere se procedere per singola regione o singola provincia (dando la possibilità di scelta). 
L'output è limitato al formato `*.gpkg`.
Lo script cancella sempre i file temporanei creati nelle elaborazioni.


### console_qgis_download

lo script console permette di scaricare e mergiare i dati catastali rilasciati tramite cartelle zip

### download_fogli_bbox

Script da console, avviare script e tracciare un poligono in mappa, scarica i fogli dentro il bbox del poligono disegnato

### download_fogli_particelle

Script da console, avviare script e tracciare un poligono in mappa, scarica le particelle dentro il bbox del poligono disegnato

### get_parcel_info_wfs

funzione personalizzata per il field calc

### get_particella_by_codes

funzione personalizzata per il field calc: dato belfiore, foglio e particella dovrebbe stampare codice particella

### particella_clic

script console che scarica singola particella per ogni clic sulla mappa

### wfs_catasto_clic_pla_multi

script da console, avviandolo chiede di cliccare sulla mappa, ogni clic scarica la particella catastale sottostante e la aggiunge allo stesso layer

### wfs_catasto_clic_pla

script da console, avviandolo chiede di cliccare sulla mappa, ogni clic scarica la particella catastale sottostante.