@echo off
rem VMU PlotterPen - cap nhat. Chep file .zip ban moi vao thu muc nay roi bam dup file nay.
rem Chi thay backend, frontend, launcher; giu nguyen Python va data (ban thao, macro, sao luu).
title VMU PlotterPen - Cap nhat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\cap_nhat.ps1"
echo.
pause
