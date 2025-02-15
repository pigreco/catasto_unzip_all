from qgis.gui import QgsMapToolEmitPoint
from qgis.core import QgsPointXY
from qgis.utils import iface

def query_catasto_point(lon, lat):
    # URL del servizio WFS pubblico
    url = 'https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs'
    
    # Parametri di connessione senza autenticazione
    uri = (f"{url}?"
           f"SERVICE=WFS&"
           f"VERSION=2.0.0&"
           f"REQUEST=GetFeature&"
           f"TYPENAME=cp:CadastralParcel&"
           f"SRSNAME=EPSG:4326&"
           f"BBOX={lon-0.001},{lat-0.001},{lon+0.001},{lat+0.001}")
    
    # Crea il layer
    layer = QgsVectorLayer(uri, "Particelle", "WFS")
    
    if not layer.isValid():
        raise Exception("Layer WFS non valido")
    
    return layer.getFeatures(), layer

def on_map_click(point: QgsPointXY):
    # Converte le coordinate del punto cliccato in WGS84
    source_crs = iface.mapCanvas().mapSettings().destinationCrs()
    target_crs = QgsCoordinateReferenceSystem('EPSG:4326')
    transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance())
    wgs84_point = transform.transform(point)
    
    lon = wgs84_point.x()
    lat = wgs84_point.y()
    
    try:
        particelle, layer = query_catasto_point(lon, lat)
        
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

# Crea e attiva il map tool per il click
canvas = iface.mapCanvas()
map_tool = QgsMapToolEmitPoint(canvas)
map_tool.canvasClicked.connect(on_map_click)
canvas.setMapTool(map_tool)