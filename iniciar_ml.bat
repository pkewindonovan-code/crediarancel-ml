@echo off
title CrediArancel ML Mejorado
echo ==========================================
echo  CrediArancel - Sistema ML Mejorado
echo ==========================================
echo.
echo Instalando dependencias...
pip install -r requirements.txt
echo.
echo Iniciando sistema...
streamlit run app.py
pause
