@echo off
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo ERROR: venv was not found.
    echo Keep this file inside MSME_AI_Project.
    echo.
    pause
    exit /b 1
)

echo.
echo Installing the local OCR engine and PDF renderer...
echo This may take several minutes.
echo.

venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install rapidocr==3.9.2 onnxruntime==1.28.0 pypdfium2

echo.
echo Checking the OCR installation...
venv\Scripts\python.exe -c "from rapidocr import RapidOCR; import onnxruntime; import pypdfium2; print('OCR installation successful')"

echo.
echo Installation finished.
echo Double-click run_app.bat to reopen the application.
echo.
pause
