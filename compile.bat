echo off

rem current directory
echo Dir: %cd%
echo Start compiling project



pyinstaller --noconfirm --onefile --windowed --icon "./data/icon.ico" --name "ReNode" --hidden-import "NodeGraphQt" --additional-hooks-dir "./NodeGraphQt-0.6.11" --paths "."  "./main.py"

echo Done