@echo off
setlocal

REM Build a Windows executable for Botlane Winrate Optimizer.
REM Usage: double-click this file or run it from cmd.

python -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo [ERROR] Impossible d'installer PyInstaller.
  exit /b 1
)

python -m PyInstaller --noconfirm --clean --windowed --name BotlaneWinrateOptimizer ^
  --add-data "champion-icons;champion-icons" ^
  --add-data "champion_id_to_name.json;." ^
  --add-data "data.xlsx;." ^
  app.py
if errorlevel 1 (
  echo [ERROR] Le build a echoue.
  exit /b 1
)

echo.
echo Build termine. Executable: dist\BotlaneWinrateOptimizer\BotlaneWinrateOptimizer.exe
echo Tu peux faire un raccourci Windows vers ce .exe.
endlocal
