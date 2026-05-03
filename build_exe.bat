@echo off
setlocal

REM Build a Windows executable for Botlane Winrate Optimizer.
REM IMPORTANT: run the EXE from dist\, not from build\ (build\ is temporary).

python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo [ERROR] Impossible d'installer PyInstaller.
  exit /b 1
)

python -m PyInstaller --noconfirm --clean --windowed --onefile --name BotlaneWinrateOptimizer ^
  --add-data "champion-icons;champion-icons" ^
  --add-data "champion_id_to_name.json;." ^
  --add-data "data.xlsx;." ^
  app.py
if errorlevel 1 (
  echo [ERROR] Le build a echoue.
  exit /b 1
)

echo.
echo Build termine.
echo Lance uniquement: dist\BotlaneWinrateOptimizer.exe
echo Ne pas lancer le fichier dans build\ (dossier temporaire de compilation).
echo Tu peux faire un raccourci Windows vers dist\BotlaneWinrateOptimizer.exe
endlocal
