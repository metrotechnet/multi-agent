@echo off
echo ====================================
echo Deploying Dok2u Frontend to Firebase
echo ====================================
echo.

REM Check if Firebase CLI is installed
where firebase >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Firebase CLI is not installed!
    echo Please install it using: npm install -g firebase-tools
    pause
    exit /b 1
)

REM Check if .env file exists for backend URL configuration
if not exist ".env" (
    echo WARNING: .env file not found! Using default backend URL.
    set BACKEND_URL=http://localhost:8080
) else (
    REM Load backend URL from .env
    for /f "tokens=1,2 delims==" %%a in ('findstr /b "BACKEND_URL=" .env') do set BACKEND_URL=%%b
    if "!BACKEND_URL!"=="" (
        echo WARNING: BACKEND_URL not found in .env. Using default.
        set BACKEND_URL=http://localhost:8080
    )
)

echo Backend URL: %BACKEND_URL%
echo.

REM Create public directory if it doesn't exist
if not exist "public" mkdir public
if not exist "public\static" mkdir public\static

echo Copying frontend files...

REM Copy index.html from templates
copy /Y "templates\index.html" "public\index.html" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy index.html
    pause
    exit /b 1
)

REM Copy all static files
xcopy /Y /E /I "static\*" "public\static\" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy static files
    pause
    exit /b 1
)

REM Update index.html to use correct paths for Firebase hosting
echo Updating file paths for Firebase hosting...
powershell -Command "(Get-Content 'public\index.html') -replace '/static/', 'static/' | Set-Content 'public\index.html'"

REM Create a config.js file with backend URL if needed
echo window.BACKEND_URL = '%BACKEND_URL%'; > "public\static\config.js"

echo.
echo Files prepared successfully!
echo.
echo Deploying to Firebase Hosting...
firebase deploy --only hosting
if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo Deployment successful!
    echo ====================================
) else (
    echo.
    echo ERROR: Deployment failed!
    exit /b 1
)

echo.
