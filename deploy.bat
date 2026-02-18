@echo off
echo ====================================
echo Deploying IMX Multi Agent to Cloud Run
echo ====================================
echo.

echo Loading deployment configuration from .env file...

REM Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    pause
    exit /b 1
)

REM Load all configuration from .env file
for /f "tokens=1,2 delims==" %%a in ('findstr /b "OPENAI_API_KEY=" .env') do set CONFIG_OPENAI_KEY=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GEMINI_API_KEY=" .env') do set CONFIG_GEMINI_KEY=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GDRIVE_FOLDER_ID=" .env') do set GDRIVE_FOLDER_ID=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GDRIVE_CREDENTIALS_PATH=" .env') do set GDRIVE_CREDS_PATH=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GCP_PROJECT_ID=" .env') do set GCP_PROJECT=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GCP_REGION=" .env') do set GCP_REGION=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GCP_SERVICE_NAME=" .env') do set SERVICE_NAME=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "GCP_IMAGE_NAME=" .env') do set IMAGE_NAME=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "MEMORY=" .env') do set MEMORY=%%b
for /f "tokens=1,2 delims==" %%a in ('findstr /b "TIMEOUT=" .env') do set TIMEOUT=%%b

REM Validate configuration
if "%GCP_PROJECT%"=="" (
    echo ERROR: GCP_PROJECT_ID not found in .env file!
    pause
    exit /b 1
)
if "%GCP_REGION%"=="" (
    echo ERROR: GCP_REGION not found in .env file!
    pause
    exit /b 1
)
if "%CONFIG_OPENAI_KEY%"=="" (
    echo ERROR: OPENAI_API_KEY not found in .env file!
    pause
    exit /b 1
)
if "%CONFIG_GEMINI_KEY%"=="" (
    echo ERROR: GEMINI_API_KEY not found in .env file!
    pause
    exit /b 1
)
if "%SERVICE_NAME%"=="" (
    echo ERROR: GCP_SERVICE_NAME not found in .env file!
    pause
    exit /b 1
)
if "%IMAGE_NAME%"=="" (
    echo ERROR: GCP_IMAGE_NAME not found in .env file!
    pause
    exit /b 1
)

echo.
echo Deploying to Cloud Run...
echo Project: %GCP_PROJECT%
echo Region: %GCP_REGION%
echo Service: %SERVICE_NAME%
echo Image: %IMAGE_NAME%
echo Memory: %MEMORY%
echo Timeout: %TIMEOUT%s

REM Use API keys from configuration file
set OPENAI_API_KEY=%CONFIG_OPENAI_KEY%
set GEMINI_API_KEY=%CONFIG_GEMINI_KEY%

echo Deploying with Cloud Run...
gcloud run deploy %SERVICE_NAME% --image %IMAGE_NAME% --platform managed --region %GCP_REGION% --allow-unauthenticated --set-env-vars OPENAI_API_KEY=%OPENAI_API_KEY%,GEMINI_API_KEY=%GEMINI_API_KEY%,GCP_PROJECT_ID=%GCP_PROJECT%,GCP_REGION=%GCP_REGION%,GDRIVE_FOLDER_ID=%GDRIVE_FOLDER_ID%,GDRIVE_CREDENTIALS_PATH=/secrets/gdrive/credentials.json --update-secrets /secrets/gdrive/credentials.json=gdrive-credentials:latest --memory %MEMORY% --timeout %TIMEOUT%s --min-instances 1 --max-instances 10 --cpu 1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Cloud Run deployment failed!
    pause
    exit /b 1
)

echo.
echo SUCCESS: Deployment completed!
echo.
echo Getting service URL...
for /f "tokens=2 delims= " %%i in ('gcloud run services describe %SERVICE_NAME% --region=%GCP_REGION% --format="value(status.url)"') do set SERVICE_URL=%%i
echo Service URL: %SERVICE_URL%
echo.
echo 🚀 Your application is now live!
echo.
pause