@echo off
title ExtruXY server
rem Chay tu thu muc goc du an: backend nam trong thu muc con "backend".
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:8000/
uvicorn app.main:app
