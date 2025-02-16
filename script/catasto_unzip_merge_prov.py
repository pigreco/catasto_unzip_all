#© totò fiandaca - 14/02/2025

from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit, QFileDialog, QMessageBox, QProgressDialog
import os
import tempfile
import shutil
import urllib.request
from zipfile import ZipFile
import processing
import time
import gc
from datetime import datetime

def log_message(msg):
    print(msg)
    QgsMessageLog.logMessage(msg, 'Elaborazione GML')

def cleanup_temp_dir(temp_dir):
    """Pulisce la directory temporanea"""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            log_message(f"Directory temporanea rimossa: {temp_dir}")
    except Exception as e:
        log_message(f"Errore nella pulizia della directory temporanea: {str(e)}")

def download_file_with_progress(url, dest_path):
    response = urllib.request.urlopen(url)
    total_size = int(response.info().get('Content-Length', 0))
    block_size = 8192
    downloaded_size = 0
    
    progress = QProgressDialog("Download in corso...", "Annulla", 0, 100)
    progress.setWindowModality(2)
    progress.show()
    
    with open(dest_path, 'wb') as f:
        while True:
            buffer = response.read(block_size)
            if not buffer:
                break
            f.write(buffer)
            downloaded_size += len(buffer)
            progress.setValue(int((downloaded_size / total_size) * 100))
            if progress.wasCanceled():
                log_message("Download annullato.")
                return False
    
    return True

def collect_inputs():
    inputs = {}
    REGIONS = [
        'ABRUZZO', 'BASILICATA', 'CALABRIA', 'CAMPANIA', 'EMILIA-ROMAGNA', 
        'FRIULI-VENEZIA-GIULIA', 'LAZIO', 'LIGURIA', 'LOMBARDIA', 'MARCHE', 
        'MOLISE', 'PIEMONTE', 'PUGLIA', 'SARDEGNA', 'SICILIA', 
        'TOSCANA', 'UMBRIA', 'VENETO'
    ]
    region, ok = QInputDialog.getItem(None, 'Seleziona Regione', 'Scegli la regione:', REGIONS, 0, False)
    if not ok: return None
    inputs['region'] = region
    
    base_url = "https://wfs.cartografia.agenziaentrate.gov.it/inspire/wfs/GetDataset.php?dataset="
    inputs['url'] = f"{base_url}{region.lower()}.zip"
    
    main_folder = QFileDialog.getExistingDirectory(None, 'Seleziona cartella di lavoro')
    if not main_folder: return None
    inputs['main_folder'] = main_folder
    
    return inputs

def extract_all_gml(zip_folder, extract_to):
    """ Estrae ricorsivamente tutti i file ZIP fino a ottenere i file GML."""
    for root, _, files in os.walk(zip_folder):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                with ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                    log_message(f"Estratto: {zip_path}")
    
    # Separa i file MAP e PLE
    map_files = []
    ple_files = []
    
    for root, _, files in os.walk(extract_to):
        for file in files:
            if file.endswith('_map.gml'):
                map_files.append(os.path.join(root, file))
            elif file.endswith('_ple.gml'):
                ple_files.append(os.path.join(root, file))
    
    log_message(f"Trovati {len(map_files)} file MAP e {len(ple_files)} file PLE")
    return map_files, ple_files

def merge_gml_files(gml_files, output_file):
    if not gml_files:
        log_message(f"Nessun file GML trovato per {output_file}")
        return
    
    try:
        # Se il file esiste già, lo elimina
        if os.path.exists(output_file):
            os.remove(output_file)
            log_message(f"File esistente rimosso: {output_file}")
        
        # Verifica permessi di scrittura nella directory
        output_dir = os.path.dirname(output_file)
        if not os.access(output_dir, os.W_OK):
            raise Exception(f"Permessi di scrittura mancanti nella directory: {output_dir}")
        
        # Crea una lista di percorsi validi per i layer
        valid_paths = []
        for gml_file in gml_files:
            if os.path.exists(gml_file):
                valid_paths.append(gml_file)
            else:
                log_message(f"File non trovato: {gml_file}")
        
        if not valid_paths:
            raise Exception("Nessun file GML valido trovato")
        
        log_message(f"Trovati {len(valid_paths)} file GML validi")
        
        # Forza la pulizia della memoria prima del merge
        gc.collect()
        time.sleep(1)
        
        # Prova a eseguire il merge diretto
        try:
            processing.run("gdal:mergevectorlayers", {
                'INPUT': valid_paths,
                'CRS': None,
                'OUTPUT': output_file
            })
        except:
            # Se fallisce, prova con l'algoritmo nativo
            processing.run("native:mergevectorlayers", {
                'LAYERS': valid_paths,
                'CRS': None,
                'OUTPUT': output_file
            })
        
        if not os.path.exists(output_file):
            raise Exception("File di output non creato")
            
        # Verifica la validità del file creato
        check_layer = QgsVectorLayer(output_file, "check", "ogr")
        if not check_layer.isValid():
            raise Exception("File di output non valido")
            
        log_message(f"File unito salvato con successo in: {output_file}")
        
    except Exception as e:
        error_msg = f"Errore durante il merge dei file: {str(e)}"
        log_message(error_msg)
        raise Exception(error_msg)
    finally:
        # Libera la memoria
        gc.collect()

def process_gml_files():
    inputs = collect_inputs()
    if not inputs:
        log_message("Operazione annullata")
        return
    
    temp_dir = tempfile.mkdtemp()
    try:
        main_folder = inputs['main_folder']
        zip_path = os.path.join(temp_dir, "downloaded.zip")
        log_message("Download del file zip...")
        
        if not download_file_with_progress(inputs['url'], zip_path):
            return
        
        log_message("Estrazione province...")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        province_zips = [f for f in os.listdir(temp_dir) if f.endswith('.zip') and f != "downloaded.zip"]
        if not province_zips:
            log_message("Nessun file ZIP di provincia trovato.")
            return
        
        province, ok = QInputDialog.getItem(None, 'Seleziona Provincia', 'Scegli la provincia da elaborare:', ['Tutte'] + [p[:2] for p in province_zips], 0, False)
        if not ok: return
        
        for prov_zip in province_zips:
            if province != 'Tutte' and not prov_zip.startswith(province):
                continue  # Elaborare solo la provincia selezionata
            
            log_message(f"Elaborazione provincia: {prov_zip}")
            prov_path = os.path.join(temp_dir, prov_zip)
            prov_dir = os.path.join(temp_dir, os.path.splitext(prov_zip)[0])
            
            with ZipFile(prov_path, 'r') as zip_ref:
                zip_ref.extractall(prov_dir)
            
            map_files, ple_files = extract_all_gml(prov_dir, prov_dir)
            
            # Genera output separati per MAP e PLE
            if province == 'Tutte':
                prov_code = prov_zip[:2]  # Usa il codice provincia dal nome file
            else:
                prov_code = province
                
            output_map = os.path.join(main_folder, f"{prov_code}_map_unito.gpkg")
            output_ple = os.path.join(main_folder, f"{prov_code}_ple_unito.gpkg")
            
            merge_gml_files(map_files, output_map)
            merge_gml_files(ple_files, output_ple)
            
        log_message(f"Elaborazione completata per provincia: {province if province != 'Tutte' else 'tutte le province'}")
        
    except Exception as e:
        log_message(f"ERRORE: {str(e)}")
        QMessageBox.critical(None, "Errore", str(e))
    finally:
        cleanup_temp_dir(temp_dir)

# Avvia lo script
process_gml_files()

