from qgis.core import (QgsVectorLayer, QgsPointXY, QgsGeometry, 
                      QgsSpatialIndex, QgsFeatureRequest, QgsCoordinateReferenceSystem,
                      QgsCoordinateTransform, QgsProject, QgsField, QgsFeature)
from qgis.gui import QgsMapToolEmitPoint
from qgis.utils import iface
from PyQt5.QtCore import QVariant

class PointTool(QgsMapToolEmitPoint):
    def __init__(self, canvas):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.active = False
    
    def activate(self):
        self.active = True
        super().activate()
    
    def deactivate(self):
        self.active = False
        super().deactivate()
    
    def canvasReleaseEvent(self, event):
        if not self.active:
            return
            
        # Ottieni il punto cliccato
        point = self.toMapCoordinates(event.pos())
        
        # Converti le coordinate in WGS84
        source_crs = self.canvas.mapSettings().destinationCrs()
        dest_crs = QgsCoordinateReferenceSystem("EPSG:4326")  # WGS84
        transform = QgsCoordinateTransform(source_crs, dest_crs, QgsProject.instance())
        wgs84_point = transform.transform(point)
        
        # Esegui la query
        try:
            particelle, layer = query_catasto_point(wgs84_point.x(), wgs84_point.y())
            if particelle:
                print("\nRisultati della ricerca:")
                for i, particella in enumerate(particelle):
                    print_feature_details(particella, i)
                    
                if layer:
                    print(f"\nCreato layer '{layer.name()}' con {layer.featureCount()} particelle")
            else:
                print("\nNessuna particella trovata in quel punto")
        except Exception as e:
            print(f"\nErrore durante la query: {str(e)}")
            print("\nControlla:")
            print("1. La connessione internet")
            print("2. L'accessibilità del servizio WFS del Catasto")
            print("3. La validità delle credenziali (se richieste)")
        
        # Disattiva lo strumento dopo l'uso
        self.deactivate()
        iface.mapCanvas().unsetMapTool(self)

def query_catasto_point(x, y, create_layer=True):
    """
    Interroga il WFS del Catasto per un punto specificato e crea opzionalmente un layer
    Args:
        x (float): Longitudine del punto (WGS84)
        y (float): Latitudine del punto (WGS84)
        create_layer (bool): Se True, crea un layer vettoriale con i risultati
    """
    
    # URL base del servizio WFS catastale con tutti i parametri necessari
    base_url = 'https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/owfs01.php'
    
    # Costruzione dell'URI con parametri verificati
    uri = (f"pagingEnabled='true' "
           f"preferCoordinatesForWfsT11='false' "
           f"restrictToRequestBBOX='1' "
           f"srsname='EPSG:6706' "
           f"typename='CP:CadastralParcel' "
           f"url='{base_url}' "
           f"version='2.0.0' "
           f"language='ita'")
    
    print(f"\nInizio query per il punto ({x}, {y})")
    
    # Carica il layer WFS
    wfs_layer = QgsVectorLayer(uri, "catasto_query", "WFS")
    
    if not wfs_layer.isValid():
        error_msg = wfs_layer.dataProvider().error().message() if wfs_layer.dataProvider() else "Nessun dettaglio disponibile"
        raise Exception(f"Layer non valido. Dettagli: {error_msg}")
    
    print("Layer WFS caricato con successo")
    
    # Crea il filtro spaziale
    point = QgsGeometry.fromPointXY(QgsPointXY(x, y))
    
    # Imposta una request con il filtro spaziale
    request = QgsFeatureRequest().setFilterRect(point.boundingBox())
    
    # Recupera le features
    features = list(wfs_layer.getFeatures(request))
    print(f"Features trovate: {len(features)}")
    
    if create_layer and features:
        # Crea un nuovo layer vettoriale in memoria
        memory_layer = QgsVectorLayer("MultiPolygon?crs=EPSG:6706", "Particelle_Catastali", "memory")
        memory_layer.startEditing()
        
        # Aggiungi i campi al layer
        for field in wfs_layer.fields():
            memory_layer.addAttribute(field)
        memory_layer.updateFields()
        
        # Aggiungi le features al nuovo layer
        for feat in features:
            new_feat = QgsFeature(memory_layer.fields())
            # Copia gli attributi
            for field in wfs_layer.fields():
                new_feat[field.name()] = feat[field.name()]
            # Copia la geometria
            new_feat.setGeometry(feat.geometry())
            memory_layer.addFeature(new_feat)
        
        memory_layer.commitChanges()
        
        # Aggiungi il layer al progetto
        QgsProject.instance().addMapLayer(memory_layer)
        print(f"Creato nuovo layer: {memory_layer.name()}")
        
        return features, memory_layer
    
    return features, None

def print_feature_details(feature, index):
    """
    Stampa i dettagli di una feature in modo formattato
    """
    print(f"\nParticella {index + 1}:")
    print("-" * 50)
    
    # Dizionario per tradurre i nomi dei campi
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

# Inizializza e attiva lo strumento punto
canvas = iface.mapCanvas()
point_tool = PointTool(canvas)
canvas.setMapTool(point_tool)
point_tool.activate()