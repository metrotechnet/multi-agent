# Start Dok2u Backend Server (FastAPI)
Write-Host "Starting Dok2u Backend Server..." -ForegroundColor Green
Write-Host ""

# Use the parent-level virtual environment that VS Code is configured to use
$envPath = "..\..\\.venv"

if (-Not (Test-Path "$envPath\Scripts\python.exe")) {
    Write-Host "ERROR: Parent virtual environment not found at $envPath" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment is set up at the agent-factory level." -ForegroundColor Yellow
    exit 1
}

Write-Host "Using virtual environment: $envPath" -ForegroundColor Cyan

# Check if dependencies are installed
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$uvicornCheck = & "$envPath\Scripts\python.exe" -c "import uvicorn; print('OK')" 2>$null
if ($uvicornCheck -ne "OK") {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    & "$envPath\Scripts\python.exe" -m pip install -r requirements.txt
    Write-Host "Dependencies installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Backend Server (FastAPI)..." -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:  http://localhost:8080" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# Start the backend server
& "$envPath\Scripts\python.exe" app.py

Write-Host ""
Write-Host "Backend server stopped." -ForegroundColor Yellow
