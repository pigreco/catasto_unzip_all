from qgis.core import *
from qgis.utils import qgsfunction
import urllib.request
import urllib.parse
from xml.etree import ElementTree as ET

@qgsfunction(args='auto', group='Catasto')
def get_particella_by_codes(admin, foglio, particella, feature, parent):
    """
    Esplora i codici amministrativi disponibili nel servizio WFS.
    """
    try:
        # Base URL con i parametri base
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
            return 'ERROR: Layer WFS non valido'
        
        # Cerchiamo le prime features disponibili nel servizio
        request = QgsFeatureRequest().setLimit(20)  # Limita a 20 risultati
        features = list(layer.getFeatures(request))
        
        debug_info = [
            f"Features trovate: {len(features)}",
            "\nPrimi esempi di particelle disponibili:"
        ]
        
        if features:
            # Raccoglie i codici amministrativi unici
            admin_codes = set()
            refs = []
            
            for feat in features:
                admin_code = feat['ADMINISTRATIVEUNIT']
                ref = feat['NATIONALCADASTRALREFERENCE']
                admin_codes.add(admin_code)
                refs.append(f"Admin: {admin_code}, Ref: {ref}")
            
            debug_info.append("\nCodici amministrativi trovati:")
            debug_info.extend(sorted(list(admin_codes)))
            
            debug_info.append("\nEsempi di riferimenti:")
            debug_info.extend(refs)
            
            # Aggiungi dettagli del codice cercato
            debug_info.append(f"\nStavi cercando il codice admin: {admin}")
            return '\n'.join(debug_info)
        else:
            return '\n'.join(debug_info + ['\nNessuna particella trovata nel servizio'])
                
    except Exception as e:
        return f'ERROR: {str(e)}'