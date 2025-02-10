# catasto_unzip_all

Unzippa le cartelle e crea due cartelle separate per le map e ple, tutto da windows!!!

## Strutture cartelle
```
cartella_principale/
    ├── provincia1.zip
    │   ├── comune1.zip
    │   │   ├── file_ple.gml
    │   │   └── file_map.gml
    │   └── comune2.zip
    │       ├── file_ple.gml
    │       └── file_map.gml
    └── provincia2.zip
        └── ...
```

## Come usarlo

![](./img/img_00.png)

- scaricare il file *.bat
- copiarlo dentro la cartella che contiene tutte le sottocartelle da unzippare
- doppio clic sul file *.bat
- aspettare la conclusione dello script che vi informerà dei file unzippati

![](./img/img_01.png)

## script creato con l'ausilio di Claude AI

## QGIS

Usare l'algoritmo di Processing [Fondi](https://docs.qgis.org/3.34/it/docs/user_manual/processing_algs/qgis/vectorgeneral.html#qgismergevectorlayers) per fondere tutte le particelle o le mappe.


![](./img/fondi.png)

## test su Sicilia

![](./img/img_02.png)

## video

## Guarda il video

[![Video](https://img.youtube.com/vi/ZlKiz5jQMOI/0.jpg)](https://youtu.be/ZlKiz5jQMOI)
