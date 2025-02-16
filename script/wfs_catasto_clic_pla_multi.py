#© totò fiandaca - 13/02/2025

from qgis.core import (QgsVectorLayer, QgsPointXY, QgsGeometry, 
                      QgsSpatialIndex, QgsFeatureRequest, QgsCoordinateReferenceSystem,
                      QgsCoordinateTransform, QgsProject, QgsField, QgsFeature)
from qgis.gui import QgsMapToolEmitPoint
from qgis.utils import iface
from PyQt5.QtCore import Qt, QVariant

class CatastoQueryTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.active = False
        self.memory_layer = None
        self.initialize_memory_layer()
    
    def initialize_memory_layer(self):
        """Inizializza il layer di memoria per la sessione"""
        self.memory_layer = QgsVectorLayer("MultiPolygon?crs=EPSG:6706", "Particelle_Catastali_Sessione", "memory")
        # Aggiungeremo i campi quando riceviamo la prima feature
        self.memory_layer.startEditing()
        QgsProject.instance().addMapLayer(self.memory_layer)
        print("\nCreato nuovo layer per la sessione: Particelle_Catastali_Sessione")
    
    def activate(self):
        self.active = True
        print("\nStrumento attivo. Clicca sulla mappa per interrogare il catasto. Premi ESC per uscire.")
        super().activate()
    
    def deactivate(self):
        self.active = False
        if self.memory_layer and self.memory_layer.featureCount() == 0:
            # Rimuovi il layer se vuoto
            QgsProject.instance().removeMapLayer(self.memory_layer.id())
        super().deactivate()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            print("\nStrumento disattivato.")
            self.deactivate()
            iface.mapCanvas().unsetMapTool(self)
            
    def canvasReleaseEvent(self, event):
        if not self.active:
            return
            
        point = self.toMapCoordinates(event.pos())
        
        # Converti in WGS84
        source_crs = self.canvas.mapSettings().destinationCrs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        wgs84_point = transform.transform(point)
        
        try:
            particelle = query_catasto_point(wgs84_point.x(), wgs84_point.y(), self.memory_layer)
            if particelle:
                print("\nRisultati della ricerca:")
                for i, particella in enumerate(particelle):
                    print_feature_details(particella, i)
                print(f"\nLayer aggiornato: {self.memory_layer.featureCount()} particelle totali")
            else:
                print("\nNessuna particella trovata in quel punto")
        except Exception as e:
            print(f"\nErrore durante la query: {str(e)}")
            print("\nControlla:")
            print("1. La connessione internet")
            print("2. L'accessibilità del servizio WFS del Catasto")
            print("3. La validità delle credenziali (se richieste)")
        
        print("\nClicca per una nuova ricerca o premi ESC per uscire.")

def query_catasto_point(x, y, memory_layer):
    """
    Interroga il WFS del Catasto per un punto specificato e aggiunge i risultati al layer della sessione
    Args:
        x (float): Longitudine del punto (WGS84)
        y (float): Latitudine del punto (WGS84)
        memory_layer: Layer vettoriale dove salvare i risultati
    """
    base_url = 'https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php'
    
    uri = (f"pagingEnabled='true' "
           f"preferCoordinatesForWfsT11='false' "
           f"restrictToRequestBBOX='1' "
           f"srsname='EPSG:6706' "
           f"typename='CP:CadastralParcel' "
           f"url='{base_url}' "
           f"version='2.0.0' "
           f"language='ita'")
    
    print(f"\nInizio query per il punto ({x}, {y})")
    
    wfs_layer = QgsVectorLayer(uri, "catasto_query", "WFS")
    
    if not wfs_layer.isValid():
        error_msg = wfs_layer.dataProvider().error().message() if wfs_layer.dataProvider() else "Nessun dettaglio disponibile"
        raise Exception(f"Layer non valido. Dettagli: {error_msg}")
    
    print("Layer WFS caricato con successo")
    
    point = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    request = QgsFeatureRequest().setFilterRect(point.boundingBox())
    features = list(wfs_layer.getFeatures(request))
    print(f"Features trovate: {len(features)}")
    
    if features:
        # Se è la prima feature, inizializza i campi del layer
        if memory_layer.fields().count() == 0:
            memory_layer.addAttribute(QgsField('NATIONALCADASTRALREFERENCE', QVariant.String))
            memory_layer.addAttribute(QgsField('ADMIN', QVariant.String))
            memory_layer.addAttribute(QgsField('SEZIONE', QVariant.String))
            memory_layer.addAttribute(QgsField('FOGLIO', QVariant.String))
            memory_layer.addAttribute(QgsField('PARTICELLA', QVariant.String))
            memory_layer.updateFields()
        
        # Aggiungi le features al layer della sessione
        memory_layer.startEditing()
        features_to_add = []
        existing_refs = set(feat['NATIONALCADASTRALREFERENCE'] for feat in memory_layer.getFeatures())
        
        for feat in features:
            ref_catastale = feat['NATIONALCADASTRALREFERENCE']
            if ref_catastale not in existing_refs:
                new_feat = QgsFeature(memory_layer.fields())
                # Copia e elabora il riferimento catastale
                ref_catastale = feat['NATIONALCADASTRALREFERENCE']
                new_feat['NATIONALCADASTRALREFERENCE'] = ref_catastale
                
                # Estrai i componenti usando la regex
                new_feat['ADMIN'] = ref_catastale[:4]
                new_feat['SEZIONE'] = ref_catastale[4:5]
                new_feat['FOGLIO'] = ref_catastale[5:9]
                new_feat['PARTICELLA'] = ref_catastale.split('.')[-1]
                # Copia geometria
                new_feat.setGeometry(feat.geometry())
                features_to_add.append(new_feat)
                existing_refs.add(ref_catastale)
        
        # Aggiungi tutte le features in una volta
        if features_to_add:
            memory_layer.addFeatures(features_to_add)
            memory_layer.commitChanges()
            memory_layer.updateExtents()
            memory_layer.triggerRepaint()
            print(f"Aggiunte {len(features_to_add)} nuove particelle al layer")
    
    return features

def print_feature_details(feature, index):
    """
    Stampa i dettagli di una feature in modo formattato
    """
    print(f"\nParticella {index + 1}:")
    print("-" * 50)
    
    field_translations = {
        'INSPIREID_LOCALID': 'ID Locale',
        'INSPIREID_NAMESPACE': 'Namespace',
        'LABEL': 'Etichetta',
        'NATIONALCADASTRALREFERENCE': 'Riferimento Catastale',
        'ADMINISTRATIVEUNIT': 'Unità Amministrativa',
        'AREAVALUE': 'Superficie (mq)',
        'BEGINLIFESPANVERSION': 'Data di inizio validità',
        'ENDLIFESPANVERSION': 'Data di fine validità',
        'QUALITY': 'Qualità',
        'SOURCE': 'Fonte'
    }
    
    for field_name in feature.fields().names():
        value = feature[field_name]
        if value:  # Stampa solo i campi non vuoti
            display_name = field_translations.get(field_name, field_name)
            print(f"{display_name}: {value}")
    print("-" * 50)

# Inizializza e attiva lo strumento
canvas = iface.mapCanvas()
point_tool = CatastoQueryTool(canvas)
canvas.setMapTool(point_tool)
point_tool.activate()