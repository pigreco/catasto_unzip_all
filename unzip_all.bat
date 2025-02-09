@echo off
echo Inizio elaborazione file...
echo.

:: Crea le cartelle di destinazione
mkdir ple_files 2>nul
mkdir map_files 2>nul

:: Crea cartella temporanea per le estrazioni
mkdir temp_extract 2>nul
cd temp_extract

:: Copia ed estrai tutti i file zip
echo Copiando e estraendo i file ZIP...
for /r ".." %%X in (*.zip) do (
    echo Elaborando: %%X
    copy "%%X" . > nul
)

:: Estrai tutti i file zip
for %%F in (*.zip) do (
    echo Estraendo: %%F
    powershell -command "Expand-Archive -Path '%%F' -DestinationPath '%%~nF' -Force"
)

:: Sposta i file nelle cartelle appropriate
echo.
echo Organizzando i file...
cd ..

:: Sposta i file che terminano in _ple
for /r "temp_extract" %%G in (*_ple.*) do (
    echo Spostando file PLE: %%~nxG
    move "%%G" "ple_files\" > nul
)

:: Sposta i file che terminano in _map
for /r "temp_extract" %%G in (*_map.*) do (
    echo Spostando file MAP: %%~nxG
    move "%%G" "map_files\" > nul
)

:: Pulizia
echo.
echo Pulizia file temporanei...
rmdir /s /q temp_extract

echo.
echo Elaborazione completata!
echo I file "_ple" si trovano nella cartella 'ple_files'
echo I file "_map" si trovano nella cartella 'map_files'
echo.

:: Mostra il conteggio dei file in ogni cartella
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