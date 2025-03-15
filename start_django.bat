@echo off
cd /d F:\employee_management
call .venv\Scripts\activate.bat
start /b python manage.py runserver 0.0.0.0:3333 > logs.txt 2>&1
