# Start Personal AI Agent Server
Write-Host "Starting Ben Boulanger AI Agent Server..." -ForegroundColor Green
Write-Host ""

# Use the parent-level virtual environment that VS Code is configured to use
$envPath = "..\..\\.venv"

if (-Not (Test-Path "$envPath\Scripts\python.exe")) {
    Write-Host "❌ Parent virtual environment not found at $envPath" -ForegroundColor Red
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
    Write-Host "✅ Dependencies installed." -ForegroundColor Green
}

# Start the server
Write-Host "Starting uvicorn server on http://localhost:8080..." -ForegroundColor Cyan
Write-Host ""
& "$envPath\Scripts\python.exe" app.py

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
