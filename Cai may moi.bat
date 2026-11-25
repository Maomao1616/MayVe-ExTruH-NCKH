@echo off
rem VMU PlotterPen - cai may moi: tao lai moi truong Python (backend\.venv) bang Python 3.12 cua may nay. Can Internet.
rem Dung khi sang may khac hoac bao "Khong co Python chay duoc". Dang chay duoc thi khong lam gi.
title VMU PlotterPen - Cai may moi
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\cai_may_moi.ps1"
echo.
pause
