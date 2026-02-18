#!/usr/bin/env pwsh
# Script to create a new knowledge base structure

param(
    [Parameter(Mandatory=$true)]
    [string]$Name
)

Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Creating Knowledge Base: $Name" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Validate name format
if ($Name -notmatch '^[a-z0-9-]+$') {
    Write-Host "ERROR: Knowledge base name must be lowercase with hyphens only" -ForegroundColor Red
    Write-Host "Example: nutria, medical-kb, fitness-data" -ForegroundColor Yellow
    exit 1
}

$kbPath = "knowledge-bases\$Name"

# Check if knowledge base already exists
if (Test-Path $kbPath) {
    Write-Host "ERROR: Knowledge base '$Name' already exists!" -ForegroundColor Red
    exit 1
}

# Create folder structure
Write-Host "Creating folder structure..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $kbPath | Out-Null
New-Item -ItemType Directory -Path "$kbPath\transcripts" | Out-Null
New-Item -ItemType Directory -Path "$kbPath\documents" | Out-Null
New-Item -ItemType Directory -Path "$kbPath\extracted_texts" | Out-Null
Write-Host "✓ Folders created" -ForegroundColor Green

# Copy prompts.json from nutria as template
Write-Host "Copying prompts template..." -ForegroundColor Cyan
if (Test-Path "knowledge-bases\nutria\prompts.json") {
    Copy-Item "knowledge-bases\nutria\prompts.json" "$kbPath\prompts.json"
    Write-Host "✓ prompts.json copied (you can customize it for this KB)" -ForegroundColor Green
} else {
    Write-Host "⚠ prompts.json not found in nutria, skipping..." -ForegroundColor Yellow
}

# Create a README for the knowledge base
$readmeContent = @"
# $Name Knowledge Base

Created: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Contents

- **transcripts/**: Audio transcription files (.txt)
- **documents/**: Source documents (PDF, DOCX, JSON, etc.)
- **extracted_texts/**: Extracted and processed text files (.txt)
- **chroma_db/**: Vector database (created after indexing)
- **prompts.json**: Knowledge base-specific prompts and AI instructions

## Customizing Prompts

The `prompts.json` file controls how the AI responds for this knowledge base. You can customize:
- System prompts and instructions
- Communication style and tone
- Behavioral constraints
- Language-specific responses

Edit this file to match your knowledge base's domain and requirements.

## Usage

### Add Documents

Place your text files in one of the folders:
- Transcripts: `transcripts/`
- Extracted texts: `extracted_texts/`
- Source documents: `documents/`

### Index Documents

``````bash
# Index extracted texts
python scripts/index_chromadb.py $Name extracted_texts

# Or index transcripts
python scripts/index_chromadb.py $Name transcripts
``````

### Use This Knowledge Base

Update `.env` file:
``````env
KNOWLEDGE_BASE=$Name
``````

Then restart the application.

## Statistics

- Documents: 0 (not indexed yet)
- Created: $(Get-Date -Format "yyyy-MM-dd")
- Last indexed: Never

"@

Set-Content -Path "$kbPath\README.md" -Value $readmeContent -Encoding UTF8
Write-Host "✓ README.md created" -ForegroundColor Green

Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "Knowledge Base Created Successfully!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Location: $kbPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Add your documents to: $kbPath\extracted_texts\" -ForegroundColor White
Write-Host "2. Index the documents: python scripts\index_chromadb.py $Name extracted_texts" -ForegroundColor White
Write-Host "3. Update .env: KNOWLEDGE_BASE=$Name" -ForegroundColor White
Write-Host "4. Restart the application" -ForegroundColor White
Write-Host ""
