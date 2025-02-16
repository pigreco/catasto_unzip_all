#© totò fiandaca - 16/02/2025

from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import (QgsVectorLayer, QgsProject, QgsGeometry, 
                      QgsFeature, QgsPointXY, QgsWkbTypes)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import gzip
import re

class ParcelDownloader:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.rubber_band = None
        self.drawing = False
        self.points = []
        self.map_tool = None
        
    def extract_info_from_id(self, inspireid):
        """Estrae comune e foglio dall'inspireid_localid"""
        if not inspireid:
            return None, None
            
        # L'ID è nel formato IT.AGE.PLA.C342_004000.101
        try:
            # Estrai il codice belfiore (comune)
            comune_match = re.search(r'\.([A-Z]\d{3})[_A-Z]', inspireid)
            comune = comune_match.group(1) if comune_match else ""
            
            # Estrai il numero del foglio (caratteri 17-20)
            foglio = inspireid[16:20] if len(inspireid) >= 20 else ""
            
            return comune, foglio
        except:
            return "", ""
        
    def start_drawing(self):
        self.rubber_band = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.rubber_band.setColor(QColor(255, 0, 0, 128))
        self.rubber_band.setWidth(2)
        
        self.map_tool = QgsMapToolEmitPoint(self.canvas)
        self.map_tool.canvasClicked.connect(self.handle_click)
        self.canvas.setMapTool(self.map_tool)
        self.drawing = True
        
    def handle_click(self, point, button):
        if button == Qt.LeftButton:
            self.points.append(point)
            if len(self.points) == 1:
                self.rubber_band.reset(QgsWkbTypes.PolygonGeometry)
            self.rubber_band.addPoint(point)
            
        elif button == Qt.RightButton and len(self.points) >= 3:
            self.drawing = False
            self.canvas.unsetMapTool(self.map_tool)
            self.download_parcels()
            
    def download_chunk(self, bbox, start_index=0, chunk_size=1000):
        base_url = "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php"
        params = {
            'language': 'ita',
            'SERVICE': 'WFS',
            'REQUEST': 'GetFeature',
            'VERSION': '2.0.0',
            'TYPENAMES': 'CP:CadastralParcel',
            'STARTINDEX': str(start_index),
            'COUNT': str(chunk_size),
            'SRSNAME': 'urn:ogc:def:crs:EPSG::6706',
            'BBOX': f"{bbox.yMinimum()},{bbox.xMinimum()},{bbox.yMaximum()},{bbox.xMaximum()},urn:ogc:def:crs:EPSG::6706"
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        print(f"Scaricamento chunk {start_index}-{start_index + chunk_size}, URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 QGIS/33415/Windows 11 Version 2009',
            'Accept-Encoding': 'gzip',
            'Accept': '*/*'
        }
        
        request = urllib.request.Request(url, headers=headers)
        response = urllib.request.urlopen(request)
        
        if response.info().get('Content-Encoding') == 'gzip':
            data = gzip.decompress(response.read())
        else:
            data = response.read()
            
        return data.decode('utf-8')
            
    def download_parcels(self):
        geometry = self.rubber_band.asGeometry()
        bbox = geometry.boundingBox()
        
        try:
            # Crea il layer con i campi nell'ordine richiesto
            uri = ("Polygon?crs=EPSG:6706"
                  "&field=inspireid_localid:string"
                  "&field=comune:string"
                  "&field=foglio:string"
                  "&field=particella:string")
            
            temp_layer = QgsVectorLayer(uri, "Particelle Catastali", "memory")
            
            if not temp_layer.isValid():
                raise Exception("Layer non valido")
            
            temp_layer.startEditing()
            
            chunk_size = 1000
            start_index = 0
            total_processed = 0
            has_more = True
            
            namespaces = {
                'wfs': 'http://www.opengis.net/wfs/2.0',
                'gml': 'http://www.opengis.net/gml/3.2',
                'CP': 'http://mapserver.gis.umn.edu/mapserver'
            }
            
            while has_more:
                try:
                    chunk_data = self.download_chunk(bbox, start_index, chunk_size)
                    chunk_root = ET.fromstring(chunk_data)
                    features = chunk_root.findall('.//CP:CadastralParcel', namespaces)
                    
                    num_features = len(features)
                    if num_features == 0:
                        has_more = False
                        break
                        
                    print(f"Features trovate in questo chunk: {num_features}")
                    processed = self.process_features(features, temp_layer, namespaces)
                    total_processed += processed
                    print(f"Processate {processed} features nel chunk {start_index}-{start_index + chunk_size}")
                    print(f"Totale features processate: {total_processed}")
                    
                    if num_features < chunk_size:
                        has_more = False
                    else:
                        start_index += chunk_size
                        
                except Exception as e:
                    print(f"Errore nel processare il chunk {start_index}: {str(e)}")
                    has_more = False
            
            temp_layer.commitChanges()
            
            if temp_layer.featureCount() > 0:
                QgsProject.instance().addMapLayer(temp_layer)
                QMessageBox.information(None, "Successo", f"Scaricate {temp_layer.featureCount()} particelle catastali!")
            else:
                QMessageBox.warning(None, "Attenzione", "Nessuna particella trovata nell'area selezionata")
            
        except Exception as e:
            QMessageBox.critical(None, "Errore", f"Errore durante il download: {str(e)}")
            print(f"Errore dettagliato: {str(e)}")
        
        finally:
            if self.rubber_band:
                self.canvas.scene().removeItem(self.rubber_band)
                self.rubber_band = None
            self.points = []
            
    def process_features(self, features, layer, namespaces):
        processed = 0
        for i, feature in enumerate(features, 1):
            try:
                geom_elem = feature.find('.//gml:posList', namespaces)
                if geom_elem is not None and geom_elem.text:
                    coords_text = geom_elem.text.strip()
                    coords_list = coords_text.split()
                    
                    coords_pairs = []
                    for i in range(0, len(coords_list), 2):
                        lat = coords_list[i]
                        lon = coords_list[i+1]
                        coords_pairs.append(f"{lon} {lat}")
                    
                    wkt = f"POLYGON(({', '.join(coords_pairs)}))"
                    
                    feat = QgsFeature(layer.fields())
                    geom = QgsGeometry.fromWkt(wkt)
                    if not geom.isGeosValid():
                        geom = geom.makeValid()
                    feat.setGeometry(geom)
                    
                    # Estrai i campi
                    label = feature.find('.//CP:LABEL', namespaces)
                    inspireid = feature.find('.//CP:INSPIREID_LOCALID', namespaces)
                    
                    # Imposta i valori nell'ordine corretto
                    inspireid_value = inspireid.text if inspireid is not None else ""
                    feat.setAttribute('inspireid_localid', inspireid_value)
                    
                    # Estrai e imposta comune e foglio
                    comune, foglio = self.extract_info_from_id(inspireid_value)
                    feat.setAttribute('comune', comune)
                    feat.setAttribute('foglio', foglio)
                    
                    # Imposta la particella (ex label)
                    feat.setAttribute('particella', label.text if label is not None else "")
                    
                    success = layer.addFeature(feat)
                    if success:
                        processed += 1
                        if processed % 100 == 0:
                            print(f"Aggiunte {processed} features al layer")
                    else:
                        print(f"Errore nell'aggiunta della feature")
            
            except Exception as e:
                print(f"Errore nel processare una feature: {str(e)}")
                continue
                
        return processed

# Per utilizzare lo script:
downloader = ParcelDownloader(iface)
downloader.start_drawing()