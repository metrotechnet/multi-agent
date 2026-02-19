# Start IMX Frontend Server (Static Files)
Write-Host "Starting IMX Frontend Server..." -ForegroundColor Green
Write-Host ""

# Use local virtual environment
$envPath = ".venv"

if (-Not (Test-Path "$envPath\Scripts\python.exe")) {
    Write-Host "Virtual environment not found. Creating one..." -ForegroundColor Yellow
    python -m venv .venv
    if (-Not (Test-Path "$envPath\Scripts\python.exe")) {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        Write-Host "Please ensure Python is installed and accessible." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
}

Write-Host "Using virtual environment: $envPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting Frontend Server (Static Files)..." -ForegroundColor Green
Write-Host ""
Write-Host "Frontend UI:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NOTE: Make sure the backend is running at http://localhost:8080" -ForegroundColor Yellow
Write-Host ""

# Start the frontend server using custom Python server
& "$envPath\Scripts\python.exe" serve_frontend.py

Write-Host ""
Write-Host "Frontend server stopped." -ForegroundColor Yellow
