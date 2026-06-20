@echo off
setlocal
set "PORT=5000"
echo Stopping Flask service on port %PORT% ...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
  taskkill /PID %%a /F
)
echo Done.
