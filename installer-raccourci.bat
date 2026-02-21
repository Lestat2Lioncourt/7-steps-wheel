@echo off
:: Cree un raccourci "Roue CSI" sur le bureau de l'utilisateur
:: A executer une seule fois par utilisateur

set "SCRIPT_DIR=%~dp0"
set "VBS_PATH=%SCRIPT_DIR%Roue CSI.vbs"
set "SHORTCUT=%USERPROFILE%\Desktop\Roue CSI.lnk"

if not exist "%VBS_PATH%" (
    echo ERREUR : Fichier "Roue CSI.vbs" introuvable dans %SCRIPT_DIR%
    pause
    exit /b 1
)

:: Creer le raccourci via PowerShell (disponible sur tout Windows 10/11)
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Description = 'Suivi indicateurs - Roue CSI'; $s.IconLocation = 'shell32.dll,21'; $s.Save()"

if exist "%SHORTCUT%" (
    echo.
    echo Raccourci cree sur le bureau : Roue CSI
    echo Vous pouvez fermer cette fenetre.
) else (
    echo.
    echo ERREUR : Le raccourci n'a pas pu etre cree.
)

timeout /t 3 >nul
