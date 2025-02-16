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

class CadastralDownloader:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.rubber_band = None
        self.drawing = False
        self.points = []
        self.map_tool = None
        
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
            self.download_cadastral_data()
            
    def download_cadastral_data(self):
        geometry = self.rubber_band.asGeometry()
        bbox = geometry.boundingBox()
        
        base_url = "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php"
        params = {
            'language': 'ita',
            'SERVICE': 'WFS',
            'REQUEST': 'GetFeature',
            'VERSION': '2.0.0',
            'TYPENAMES': 'CP:CadastralZoning',
            'STARTINDEX': '0',
            'COUNT': '1000',
            'SRSNAME': 'urn:ogc:def:crs:EPSG::6706',
            'BBOX': f"{bbox.yMinimum()},{bbox.xMinimum()},{bbox.yMaximum()},{bbox.xMaximum()},urn:ogc:def:crs:EPSG::6706"
        }
        
        url = f"{base_url}?{urllib.parse.urlencode(params)}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 QGIS/33415/Windows 11 Version 2009'
            }
            request = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(request)
            data = response.read()
            
            # Crea il layer con i campi corretti basati sulla risposta XML
            uri = ("Polygon?crs=EPSG:6706"
                  "&field=label:string"
                  "&field=inspireid_localid:string"
                  "&field=inspireid_namespace:string"
                  "&field=nationalcadastralref:string"
                  "&field=beginlifespanversion:string"
                  "&field=level:string"
                  "&field=levelname:string"
                  "&field=originalscale:integer"
                  "&field=administrativeunit:string")
            
            temp_layer = QgsVectorLayer(uri, "Catasto", "memory")
            
            if not temp_layer.isValid():
                raise Exception("Layer non valido")
            
            temp_layer.startEditing()
            
            # Parse XML con i namespace corretti
            namespaces = {
                'wfs': 'http://www.opengis.net/wfs/2.0',
                'gml': 'http://www.opengis.net/gml/3.2',
                'CP': 'http://mapserver.gis.umn.edu/mapserver'
            }
            
            root = ET.fromstring(data)
            features = root.findall('.//CP:CadastralZoning', namespaces)
            
            for feature in features:
                try:
                    # Cerca la geometria
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
                        
                        # Crea la feature
                        feat = QgsFeature(temp_layer.fields())
                        geom = QgsGeometry.fromWkt(wkt)
                        if not geom.isGeosValid():
                            geom = geom.makeValid()
                        feat.setGeometry(geom)
                        
                        # Estrai attributi usando i tag corretti
                        attributes = {
                            'label': feature.find('.//CP:LABEL', namespaces),
                            'inspireid_localid': feature.find('.//CP:INSPIREID_LOCALID', namespaces),
                            'inspireid_namespace': feature.find('.//CP:INSPIREID_NAMESPACE', namespaces),
                            'nationalcadastralref': feature.find('.//CP:NATIONALCADASTRALZONINGREFERENCE', namespaces),
                            'beginlifespanversion': feature.find('.//CP:BEGINLIFESPANVERSION', namespaces),
                            'level': feature.find('.//CP:LEVEL', namespaces),
                            'levelname': feature.find('.//CP:LEVELNAME', namespaces),
                            'originalscale': feature.find('.//CP:ORIGINALMAPSCALEDENOMINATOR', namespaces),
                            'administrativeunit': feature.find('.//CP:ADMINISTRATIVEUNIT', namespaces)
                        }
                        
                        # Imposta gli attributi
                        for field_name, elem in attributes.items():
                            if elem is not None and elem.text:
                                if field_name == 'originalscale':
                                    feat.setAttribute(field_name, int(elem.text))
                                else:
                                    feat.setAttribute(field_name, elem.text)
                                print(f"Attributo {field_name}: {elem.text}")  # Debug
                        
                        # Aggiungi la feature
                        success = temp_layer.addFeature(feat)
                        if not success:
                            print(f"Errore nell'aggiunta della feature")
                
                except Exception as e:
                    print(f"Errore nel processare una feature: {str(e)}")
                    continue
            
            temp_layer.commitChanges()
            
            if temp_layer.featureCount() > 0:
                QgsProject.instance().addMapLayer(temp_layer)
                QMessageBox.information(None, "Successo", f"Scaricate {temp_layer.featureCount()} geometrie catastali!")
            else:
                QMessageBox.warning(None, "Attenzione", "Nessuna geometria trovata nell'area selezionata")
            
        except Exception as e:
            QMessageBox.critical(None, "Errore", f"Errore durante il download: {str(e)}")
            print(f"Errore dettagliato: {str(e)}")
        
        finally:
            if self.rubber_band:
                self.canvas.scene().removeItem(self.rubber_band)
                self.rubber_band = None
            self.points = []

# Per utilizzare lo script:
downloader = CadastralDownloader(iface)
downloader.start_drawing()