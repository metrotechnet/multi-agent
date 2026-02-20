# Start Dok2u Frontend Server (Static Files)
Write-Host "Starting Dok2u Frontend Server..." -ForegroundColor Green
Write-Host ""

# Use the parent-level virtual environment that VS Code is configured to use
$envPath = "..\..\\.venv"

if (-Not (Test-Path "$envPath\Scripts\python.exe")) {
    Write-Host "ERROR: Parent virtual environment not found at $envPath" -ForegroundColor Red
    Write-Host "Please ensure the virtual environment is set up at the agent-factory level." -ForegroundColor Yellow
    exit 1
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
