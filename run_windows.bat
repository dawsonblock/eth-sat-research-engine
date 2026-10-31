@echo off
setlocal
python -m pip install -e .
if errorlevel 1 exit /b %errorlevel%
python -m eth_sat --example simple --engine compare
exit /b %errorlevel%
