@echo off
REM Download question_log.json from the server using curl

set SERVER_URL=https://bennutritioniste-ai-206155864266.us-east4.run.app/api/download_log?key=dboubou363
set OUTPUT_FILE=question_log.json

curl -o %OUTPUT_FILE% "%SERVER_URL%"

if %ERRORLEVEL%==0 (
    echo Download successful: %OUTPUT_FILE%
) else (
    echo Download failed.
)
