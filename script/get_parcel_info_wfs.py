# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WMF Catasto Agenzia delle Entrate CC BY 4.0
                              -------------------
        copyright            : (C) 2025 by Totò Fiandaca
        email                : pigrecoinfinito@gmail.com
 ***************************************************************************/
"""

from qgis.core import *
from qgis.utils import qgsfunction
import urllib.request
import urllib.parse
from xml.etree import ElementTree as ET

def format_wkt(wkt, decimals=6):
    """
    Formatta una stringa WKT con il numero specificato di decimali.
    """
    import re
    
    def format_number(match):
        num = float(match.group(0))
        return f"{num:.{decimals}f}"
    
    formatted = re.sub(r'\d+\.\d+', format_number, wkt)
    formatted = formatted.replace(",", ", ")
    formatted = formatted.replace("), ", "),\n")
    
    return formatted

@qgsfunction(args='auto', group='Catasto', usesgeometry=True)
def get_particella_infoWFS(geom, feature, parent):
    """
    <h1>Catasto Agenzia delle Entrate CC BY 4.0:</h1>    
    La funzione restituisce le informazioni WFS Catasto disponibili nella particella sottostante.

    <h2>Parametri</h2>
    <ul>
      <li>geometry: geometria del punto (viene passata automaticamente)</li>
    </ul>
    
    <h2>Returns</h2>
    <ul>
      <li>ARRAY: informazioni della particella</li>
    </ul>
    
    <h2>Esempio</h2>
        <pre>get_particella_info($geometry)[0]--> M011_0019C0.131</pre>
        <pre>get_particella_info($geometry)[1]--> 0019</pre>
        <pre>get_particella_info($geometry)[2]--> 131</pre>
        <pre>get_particella_info($geometry)[3]--> M011</pre>
        <pre>get_particella_info($geometry)[4]--> geometria WKT</pre>
    """
    try:
        # Verifica che la geometria sia un punto
        if geom.type() != QgsWkbTypes.PointGeometry:
            return ['ERROR', 'ERROR', 'ERROR', 'ERROR', 'ERROR']
            
        # Prendi le coordinate del punto
        point = geom.asPoint()
        x = point.x()
        y = point.y()
        
        # Base URL con i parametri base che sappiamo funzionare
        uri = (f"pagingEnabled='true' "
               f"preferCoordinatesForWfsT11='false' "
               f"restrictToRequestBBOX='1' "
               f"srsname='EPSG:6706' "
               f"typename='CP:CadastralParcel' "
               f"url='https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php' "
               f"version='2.0.0' "
               f"language='ita'")
               
        # Crea un layer temporaneo per la richiesta
        layer = QgsVectorLayer(uri, "catasto_query", "WFS")
        
        if not layer.isValid():
            return ['ERROR', 'ERROR', 'ERROR', 'ERROR', 'ERROR']
            
        # Crea il punto per il filtro spaziale
        point_geom = QgsGeometry.fromPointXY(QgsPointXY(x, y))
        request = QgsFeatureRequest().setFilterRect(point_geom.boundingBox())
        
        # Recupera le features
        features = list(layer.getFeatures(request))
        
        if features:
            # Prendi la prima particella trovata
            feat = features[0]
            ref = feat['NATIONALCADASTRALREFERENCE']
            admin = feat['ADMINISTRATIVEUNIT']
            label = feat['LABEL']
            foglio = ref[5:9] if len(ref) > 9 else 'N/D'
            
            # Ottieni la geometria WKT e formattala
            geom_wkt = 'N/D'
            if feat.hasGeometry():
                geom_wkt = format_wkt(feat.geometry().asWkt())
            
            # Restituisci la lista
            return [ref, foglio, label, admin, geom_wkt]
        else:
            return ['N/D', 'N/D', 'N/D', 'N/D', 'N/D']
                
    except Exception as e:
        return ['ERROR', 'ERROR', 'ERROR', 'ERROR', 'ERROR']

# Esempio di utilizzo nel calcolatore di campi:
# get_particella_info($geometry)[0]  # per il riferimento catastale
# get_particella_info($geometry)[4]  # per la geometria WKT
