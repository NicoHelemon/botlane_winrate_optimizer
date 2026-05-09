@echo off
setlocal EnableExtensions

REM Build Windows: dist\BotlaneWinrateOptimizer\BotlaneWinrateOptimizer.exe
REM The build\ directory is only PyInstaller temporary output; never launch files from build\.

cd /d "%~dp0"

set "APP_NAME=BotlaneWinrateOptimizer"
set "DIST_ROOT=dist"
set "BUILD_ROOT=build"
set "DIST_DIR=%DIST_ROOT%\%APP_NAME%"
set "EXE_PATH=%DIST_DIR%\%APP_NAME%.exe"

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

python -c "import PyInstaller, openpyxl" >nul 2>nul
if errorlevel 1 (
  echo [INFO] Installation des dependances de build manquantes...
  python -m pip install pyinstaller openpyxl
  if errorlevel 1 (
    echo [ERROR] Impossible d'installer PyInstaller/openpyxl.
    exit /b 1
  )
)

REM Nettoyage complet: on repart toujours de zero.
if exist "%DIST_ROOT%" rmdir /s /q "%DIST_ROOT%"
if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%"

python -m PyInstaller --noconfirm --clean --windowed --onedir --name "%APP_NAME%" ^
  --add-data "data.xlsx;." ^
  --add-data "champion_id_to_name.json;." ^
  --add-data "champion-icons;champion-icons" ^
  app.py
if errorlevel 1 (
  echo [ERROR] Le build PyInstaller a echoue.
  exit /b 1
)

if not exist "%EXE_PATH%" (
  echo [ERROR] Executable attendu introuvable: %EXE_PATH%
  echo [INFO] Contenu genere par PyInstaller:
  if exist "%DIST_ROOT%" dir /s /b "%DIST_ROOT%"
  if exist "%BUILD_ROOT%" dir /s /b "%BUILD_ROOT%"
  exit /b 1
)

REM Fichiers editables a cote du .exe. L'app les utilise en priorite.
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

echo.
echo Build termine avec succes.
echo Lance ce fichier:
echo   %EXE_PATH%
echo.
echo Le dossier build\ est normal: c'est un dossier temporaire PyInstaller.
echo Le dossier a distribuer/lancer est uniquement:
echo   %DIST_DIR%
echo.
echo Contenu direct du dossier final:
dir /b "%DIST_DIR%"
endlocal
