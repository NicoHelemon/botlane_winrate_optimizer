@echo off
setlocal EnableExtensions

REM Build a simple Windows folder distribution for Botlane Winrate Optimizer.
REM The final executable is: dist\BotlaneWinrateOptimizer\BotlaneWinrateOptimizer.exe
REM Keep data.xlsx, champion_id_to_name.json and champion-icons\ next to the EXE.

cd /d "%~dp0"

set "APP_NAME=BotlaneWinrateOptimizer"
set "DIST_DIR=dist\%APP_NAME%"
set "BUILD_DIR=build\%APP_NAME%"

if not exist "app.py" (
  echo [ERROR] app.py introuvable. Lance ce script depuis le dossier du projet.
  exit /b 1
)
if not exist "data.xlsx" (
  echo [ERROR] data.xlsx introuvable.
  exit /b 1
)
if not exist "champion_id_to_name.json" (
  echo [ERROR] champion_id_to_name.json introuvable.
  exit /b 1
)
if not exist "champion-icons\" (
  echo [ERROR] Dossier champion-icons introuvable.
  exit /b 1
)

python -m pip install --upgrade pyinstaller openpyxl
if errorlevel 1 (
  echo [ERROR] Impossible d'installer PyInstaller/openpyxl.
  exit /b 1
)

REM Start from a clean PyInstaller output so old files cannot mask build issues.
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"

python -m PyInstaller --noconfirm --clean --windowed --onedir --name "%APP_NAME%" ^
  --distpath "dist" ^
  --workpath "%BUILD_DIR%" ^
  --specpath "%BUILD_DIR%" ^
  --add-data "data.xlsx;." ^
  --add-data "champion_id_to_name.json;." ^
  --add-data "champion-icons;champion-icons" ^
  app.py
if errorlevel 1 (
  echo [ERROR] Le build PyInstaller a echoue.
  exit /b 1
)

REM Also expose editable data/resources next to the EXE. The app prefers these files
REM and falls back to PyInstaller's bundled copies if they are absent.
copy /y "data.xlsx" "%DIST_DIR%\data.xlsx" >nul
if errorlevel 1 (
  echo [ERROR] Impossible de copier data.xlsx dans %DIST_DIR%.
  exit /b 1
)
copy /y "champion_id_to_name.json" "%DIST_DIR%\champion_id_to_name.json" >nul
if errorlevel 1 (
  echo [ERROR] Impossible de copier champion_id_to_name.json dans %DIST_DIR%.
  exit /b 1
)
if exist "%DIST_DIR%\champion-icons" rmdir /s /q "%DIST_DIR%\champion-icons"
xcopy /e /i /y "champion-icons" "%DIST_DIR%\champion-icons" >nul
if errorlevel 1 (
  echo [ERROR] Impossible de copier champion-icons dans %DIST_DIR%.
  exit /b 1
)

if not exist "%DIST_DIR%\%APP_NAME%.exe" (
  echo [ERROR] Build termine sans executable attendu: %DIST_DIR%\%APP_NAME%.exe
  exit /b 1
)

echo.
echo Build termine avec succes.
echo Lance: %DIST_DIR%\%APP_NAME%.exe
echo Garde data.xlsx, champion_id_to_name.json et champion-icons\ dans ce meme dossier.
endlocal
