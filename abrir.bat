@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"
title Comparador de ropa
echo.
echo   COMPARADOR DE ROPA   (se actualiza solo al prender el PC, 1 vez al dia)
echo   ------------------
echo   1) Actualizar todo ahora (1-2 min)
echo   2) Actualizar pantalones
echo   3) Actualizar parte superior
echo   4) Actualizar zapatillas
echo   5) Solo abrir (Enter)
echo   6) Ver registro de la ultima actualizacion automatica
echo   7) Importar tiendas desde el navegador (Kagi, Haze...)
echo   8) Procesar catalogos guardados con el marcador
echo.
set /p op="  Opcion (1-8): "
if "%op%"=="6" (start "" notepad "%~dp0log.txt" & exit /b)
if "%op%"=="7" (python importar.py & exit /b)
if "%op%"=="8" python comparador.py importar
if "%op%"=="1" python comparador.py todo
if "%op%"=="2" python comparador.py abajo
if "%op%"=="3" python comparador.py arriba
if "%op%"=="4" python comparador.py zapatillas
if "%op%"=="5" python comparador.py ver
if "%op%"=="" python comparador.py ver
start "" "%~dp0resultados.html"
