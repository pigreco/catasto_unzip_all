from qgis.core import QgsVectorLayer, QgsProject, QgsMessageLog
from qgis.PyQt.QtWidgets import QInputDialog, QLineEdit, QFileDialog, QMessageBox
import os
import tempfile
import shutil
import urllib.request
from zipfile import ZipFile
import processing
import time
import gc
from datetime import datetime, timedelta

def log_message(msg):
    print(msg)
    QgsMessageLog.logMessage(msg, 'Elaborazione GML')

def safe_cleanup(folder_path):
    try:
        project = QgsProject.instance()
        layers_to_remove = []
        
        for layer_id, layer in project.mapLayers().items():
            source_path = layer.source()
            if source_path.startswith(folder_path):
                layer.setValid(False)
                layers_to_remove.append(layer_id)
        
        if layers_to_remove:
            project.removeMapLayers(layers_to_remove)
            time.sleep(2)
        
        gc.collect()
        
        if os.path.exists(folder_path):
            for root, dirs, files in os.walk(folder_path, topdown=False):
                for name in files:
                    file_path = os.path.join(root, name)
                    try:
                        if os.path.exists(file_path):
                            os.chmod(file_path, 0o777)
                            os.remove(file_path)
                    except Exception as e:
                        log_message(f"Impossibile rimuovere il file {name}: {str(e)}")
            
            shutil.rmtree(folder_path, ignore_errors=True)
            log_message(f"Cartella rimossa: {folder_path}")
    except Exception as e:
        log_message(f"Avviso: impossibile rimuovere {folder_path}: {str(e)}")

def collect_inputs():
    inputs = {}
    
    file_types = ['Mappe (MAP)', 'Particelle (PLE)', 'Entrambi']
    file_type, ok = QInputDialog.getItem(None, 'Tipo File', 
                                       'Seleziona il tipo di file da unire:', 
                                       file_types, 0, False)
    if not ok: return None
    inputs['file_type'] = file_type
    
    main_folder = QFileDialog.getExistingDirectory(None, 'Seleziona cartella di lavoro')
    if not main_folder: return None
    inputs['main_folder'] = main_folder
    
    url, ok = QInputDialog.getText(None, 'URL', 'Inserisci URL del file ZIP:', QLineEdit.Normal)
    if not ok or not url: return None
    inputs['url'] = url
    
    formats = {
        'GML': '.gml',
        'GPKG': '.gpkg',
        'Shapefile': '.shp',
        'GeoJSON': '.geojson'
    }
    format_name, ok = QInputDialog.getItem(None, 'Formato Output', 
                                         'Seleziona il formato di output:', 
                                         formats.keys(), 0, False)
    if not ok: return None
    inputs['format_name'] = format_name
    inputs['output_extension'] = formats[format_name]
    
    if file_type in ['Mappe (MAP)', 'Entrambi']:
        map_output = QFileDialog.getSaveFileName(None, 'Salva il file unito MAP',
                                               main_folder, f'*{formats[format_name]}')[0]
        if not map_output: return None
        if not map_output.endswith(formats[format_name]):
            map_output += formats[format_name]
        inputs['map_output'] = map_output
    
    if file_type in ['Particelle (PLE)', 'Entrambi']:
        ple_output = QFileDialog.getSaveFileName(None, 'Salva il file unito PLE',
                                               main_folder, f'*{formats[format_name]}')[0]
        if not ple_output: return None
        if not ple_output.endswith(formats[format_name]):
            ple_output += formats[format_name]
        inputs['ple_output'] = ple_output

    delete_temp, ok = QInputDialog.getItem(None, 'Pulizia', 
                                         'Vuoi eliminare le cartelle temporanee map_files e ple_files?', 
                                         ['Sì', 'No'], 0, False)
    if not ok: return None
    inputs['delete_temp'] = delete_temp == 'Sì'

    load_layers, ok = QInputDialog.getItem(None, 'Carica in QGIS', 
                                         'Vuoi caricare i file uniti in QGIS?', 
                                         ['Sì', 'No'], 0, False)
    if not ok: return None
    inputs['load_layers'] = load_layers == 'Sì'
    
    return inputs

def merge_files(source_folder, output_file, file_type, inputs):
    start_time = datetime.now()
    temp_merge = None
    try:
        source_files = [os.path.join(source_folder, f) for f in os.listdir(source_folder) 
                    if f.endswith('.gml')]
        
        if source_files:
            temp_merge = os.path.join(os.path.dirname(output_file), 
                                    f"temp_merge_{file_type}.gpkg")
            
            merge_params = {
                'LAYERS': source_files,
                'CRS': None,
                'OUTPUT': temp_merge
            }
            
            log_message(f"Unione file {file_type}...")
            processing.run("native:mergevectorlayers", merge_params)
            
            # Chiudi tutti i layer che potrebbero utilizzare il file temporaneo
            project = QgsProject.instance()
            for layer in project.mapLayers().values():
                if layer.source() == temp_merge:
                    layer.setValid(False)
            gc.collect()
            time.sleep(1)
            
            filter_params = {
                'INPUT': temp_merge,
                'FIELDS': ['fid', 'gml_id', 'ADMINISTRATIVEUNIT'],
                'OUTPUT': output_file
            }
            
            log_message(f"Filtro attributi per {file_type}...")
            result = processing.run("native:retainfields", filter_params)
            
            if inputs['load_layers']:
                merged_layer = QgsVectorLayer(output_file, f"{file_type}_Uniti", "ogr")
                if merged_layer.isValid():
                    QgsProject.instance().addMapLayer(merged_layer)
                    log_message(f"Layer {file_type} caricato in QGIS")
            
            end_time = datetime.now()
            return end_time - start_time
    finally:
        # Pulizia file temporaneo
        if temp_merge and os.path.exists(temp_merge):
            # Chiudi tutti i layer che utilizzano il file
            project = QgsProject.instance()
            for layer in project.mapLayers().values():
                if layer.source() == temp_merge:
                    project.removeMapLayer(layer.id())
            gc.collect()
            time.sleep(1)
            
            try:
                os.chmod(temp_merge, 0o777)
                os.remove(temp_merge)
            except Exception as e:
                log_message(f"Impossibile rimuovere il file temporaneo: {str(e)}")
    
    return None

def process_gml_files():
    inputs = collect_inputs()
    if not inputs:
        log_message("Operazione annullata")
        return
    
    try:
        main_folder = inputs['main_folder']
        ple_folder = os.path.join(main_folder, 'ple_files')
        map_folder = os.path.join(main_folder, 'map_files')
        os.makedirs(ple_folder, exist_ok=True)
        os.makedirs(map_folder, exist_ok=True)
        temp_dir = tempfile.mkdtemp()
        log_message(f"Cartelle create in: {main_folder}")
        
        log_message("Download del file zip...")
        zip_path = os.path.join(temp_dir, "downloaded.zip")
        urllib.request.urlretrieve(inputs['url'], zip_path)
        
        log_message("Estrazione province...")
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        province_zips = [f for f in os.listdir(temp_dir) 
                        if f.endswith('.zip') and f != "downloaded.zip"]
        for prov_zip in province_zips:
            log_message(f"Elaborazione provincia: {prov_zip}")
            prov_path = os.path.join(temp_dir, prov_zip)
            prov_dir = os.path.join(temp_dir, os.path.splitext(prov_zip)[0])
            
            with ZipFile(prov_path, 'r') as zip_ref:
                zip_ref.extractall(prov_dir)
            
            comuni_zips = [f for f in os.listdir(prov_dir) if f.endswith('.zip')]
            for com_zip in comuni_zips:
                log_message(f"Elaborazione comune: {com_zip}")
                com_path = os.path.join(prov_dir, com_zip)
                com_dir = os.path.join(prov_dir, os.path.splitext(com_zip)[0])
                with ZipFile(com_path, 'r') as zip_ref:
                    zip_ref.extractall(com_dir)
        
        ple_count = map_count = 0
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.endswith('.gml'):
                    file_path = os.path.join(root, file)
                    if '_ple' in file.lower():
                        shutil.move(file_path, os.path.join(ple_folder, file))
                        ple_count += 1
                    elif '_map' in file.lower():
                        shutil.move(file_path, os.path.join(map_folder, file))
                        map_count += 1
        
        log_message(f"File trovati: {ple_count} PLE, {map_count} MAP")
        
        processing_times = {}
        
        if inputs['file_type'] in ['Mappe (MAP)', 'Entrambi']:
            map_time = merge_files(map_folder, inputs['map_output'], 'MAP', inputs)
            if map_time:
                processing_times['MAP'] = map_time
        
        if inputs['file_type'] in ['Particelle (PLE)', 'Entrambi']:
            ple_time = merge_files(ple_folder, inputs['ple_output'], 'PLE', inputs)
            if ple_time:
                processing_times['PLE'] = ple_time
        
        if inputs['delete_temp']:
            log_message("Pulizia file temporanei...")
            safe_cleanup(temp_dir)
            safe_cleanup(map_folder)
            safe_cleanup(ple_folder)
            
            try:
                if os.path.exists(main_folder) and not os.listdir(main_folder):
                    os.rmdir(main_folder)
                    log_message("Cartella principale rimossa")
            except Exception as e:
                log_message(f"Nota: la cartella principale non è stata rimossa: {str(e)}")
        
        log_message("\nElaborazione completata!")
        if 'map_output' in inputs:
            log_message(f"File MAP salvato in: {inputs['map_output']}")
        if 'ple_output' in inputs:
            log_message(f"File PLE salvato in: {inputs['ple_output']}")
        
        log_message("\nTempi di elaborazione:")
        for file_type, proc_time in processing_times.items():
            if proc_time:
                minutes = proc_time.total_seconds() / 60
                log_message(f"Merge {file_type}: {minutes:.2f} minuti")
        
    except Exception as e:
        log_message(f"ERRORE: {str(e)}")
        try:
            safe_cleanup(temp_dir)
        except:
            pass

process_gml_files()
