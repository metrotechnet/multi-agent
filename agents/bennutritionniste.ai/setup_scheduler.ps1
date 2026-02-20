Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Setting up Cloud Scheduler Job" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Load .env file
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Parse .env file
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        $envVars[$matches[1]] = $matches[2]
    }
}

$GCP_PROJECT = $envVars['GCP_PROJECT_ID']
$GCP_REGION = $envVars['GCP_REGION']
$SERVICE_NAME = $envVars['GCP_SERVICE_NAME']

# Validate configuration
if (-not $GCP_PROJECT) {
    Write-Host "ERROR: GCP_PROJECT_ID not found in .env file!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not $GCP_REGION) {
    Write-Host "ERROR: GCP_REGION not found in .env file!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
if (-not $SERVICE_NAME) {
    Write-Host "ERROR: GCP_SERVICE_NAME not found in .env file!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "Project: $GCP_PROJECT"
Write-Host "Region: $GCP_REGION"
Write-Host "Service: $SERVICE_NAME"
Write-Host ""

# Get the service URL
Write-Host "Getting Cloud Run service URL..." -ForegroundColor Yellow
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region=$GCP_REGION --format="value(status.url)" --project=$GCP_PROJECT 2>$null

if (-not $SERVICE_URL) {
    Write-Host "ERROR: Could not retrieve service URL. Make sure the service is deployed." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Service URL: $SERVICE_URL" -ForegroundColor Green
Write-Host ""

# Check if job exists
Write-Host "Checking if job already exists..." -ForegroundColor Yellow
$null = gcloud scheduler jobs describe gdrive-daily-update --location=$GCP_REGION --project=$GCP_PROJECT 2>&1
$jobExists = $LASTEXITCODE -eq 0

if ($jobExists) {
    Write-Host "Job already exists, updating..." -ForegroundColor Yellow
    gcloud scheduler jobs update http gdrive-daily-update `
        --location=$GCP_REGION `
        --schedule="0 3 * * *" `
        --time-zone="America/Toronto" `
        --uri="$SERVICE_URL/update" `
        --http-method=POST `
        --project=$GCP_PROJECT `
        --description="Daily Google Drive document indexing at 3 AM"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Cloud Scheduler job updated successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ ERROR: Failed to update Cloud Scheduler job" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "Creating new Cloud Scheduler job..." -ForegroundColor Yellow
    Write-Host "Schedule: Daily at 3:00 AM (America/Toronto timezone)"
    Write-Host "Target: POST $SERVICE_URL/update"
    Write-Host ""
    
    gcloud scheduler jobs create http gdrive-daily-update `
        --location=$GCP_REGION `
        --schedule="0 3 * * *" `
        --time-zone="America/Toronto" `
        --uri="$SERVICE_URL/update" `
        --http-method=POST `
        --project=$GCP_PROJECT `
        --description="Daily Google Drive document indexing at 3 AM"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Cloud Scheduler job created successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ ERROR: Failed to create Cloud Scheduler job" -ForegroundColor Red
        Write-Host "Exit code: $LASTEXITCODE" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Job Details:" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
gcloud scheduler jobs describe gdrive-daily-update --location=$GCP_REGION --project=$GCP_PROJECT

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "The job will run daily at 3:00 AM (Toronto time)" -ForegroundColor Green
Write-Host ""
Write-Host "To test the job immediately, run:" -ForegroundColor Yellow
Write-Host "gcloud scheduler jobs run gdrive-daily-update --location=$GCP_REGION --project=$GCP_PROJECT"
Write-Host ""
Write-Host "To view job history:" -ForegroundColor Yellow
Write-Host "gcloud scheduler jobs describe gdrive-daily-update --location=$GCP_REGION --project=$GCP_PROJECT"
Write-Host ""
Read-Host "Press Enter to exit"
