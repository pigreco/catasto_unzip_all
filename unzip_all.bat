@echo off
setlocal enabledelayedexpansion

echo Inizio elaborazione dei file zip nidificati...
echo.

:: Crea le cartelle di destinazione
mkdir ple_files 2>nul
mkdir map_files 2>nul
mkdir temp_extract 2>nul

:: Primo livello - estrai i zip delle province
echo Elaborazione zip di primo livello...
for %%Z in (*.zip) do (
    echo Estraendo provincia: %%Z
    powershell -command "Expand-Archive -Path '%%Z' -DestinationPath 'temp_extract\%%~nZ' -Force"
)

:: Secondo livello - estrai i zip dei comuni
echo.
echo Elaborazione zip di secondo livello...
for /r "temp_extract" %%F in (*.zip) do (
    echo Estraendo comune: %%~nxF
    powershell -command "Expand-Archive -Path '%%F' -DestinationPath '%%~dpnF_extracted' -Force"
)

:: Sposta tutti i file GML trovati
echo.
echo Spostamento file GML...
for /r "temp_extract" %%G in (*.gml) do (
    set "filename=%%~nxG"
    echo Analizzando: !filename!
    
    if "!filename:_ple=!" neq "!filename!" (
        echo Spostando PLE: %%~nxG
        move "%%G" "ple_files\" > nul
    ) else if "!filename:_map=!" neq "!filename!" (
        echo Spostando MAP: %%~nxG
        move "%%G" "map_files\" > nul
    )
)

:: Pulisci le cartelle temporanee
echo.
echo Pulizia file temporanei...
rmdir /s /q temp_extract

:: Mostra riepilogo con conteggio
echo.
echo Elaborazione completata!
echo.
echo Riepilogo:
echo ------------
dir /b /a-d "ple_files\*.*" 2>nul | find /c /v "" > temp.txt
set /p PLE_COUNT=<temp.txt
echo File in ple_files: %PLE_COUNT%

dir /b /a-d "map_files\*.*" 2>nul | find /c /v "" > temp.txt
set /p MAP_COUNT=<temp.txt
echo File in map_files: %MAP_COUNT%
del temp.txt

pause