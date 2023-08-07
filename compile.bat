echo off

rem current directory
echo Dir: %cd%
echo Start compiling project

rem get cmd argument


rem run prebuild task (git rev-parse --short HEAD)
rem .\builder.py %1

pyinstaller --noconfirm --onefile --windowed --icon "./data/icon.ico" --name "ReNode" --hidden-import "NodeGraphQt" --additional-hooks-dir "./NodeGraphQt-0.6.11" --paths "."  "./main.py"

echo Build done. Copy source to workdir

copy "%cd%\dist\ReNode.exe" "%cd%\ReNode.exe" /Y

echo Done