# Shared Google Drive Setup Guide

## Overview
This guide walks you through setting up a shared Google Drive folder to automatically sync and index documents for your multi-agent application.

## What You'll Need
- A Google account
- Access to Google Cloud Console
- The documents you want to share in a Google Drive folder

## Step-by-Step Setup

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top
3. Click **"New Project"**
4. Enter a project name (e.g., "Multi-Agent-Docs")
5. Click **"Create"**
6. Wait for the project to be created (this takes a few seconds)

### Step 2: Enable Google Drive API

1. Make sure your new project is selected in the project dropdown
2. Go to **"APIs & Services"** > **"Library"** (left sidebar)
3. Search for **"Google Drive API"**
4. Click on the Google Drive API result
5. Click the blue **"Enable"** button
6. Wait for the API to be enabled

### Step 3: Create a Service Account

A service account is like a robot account that your application will use to access Google Drive.

1. Go to **"APIs & Services"** > **"Credentials"**
2. Click **"Create Credentials"** > **"Service Account"**
3. Fill in the details:
   - **Service account name**: `gdrive-reader` (or any name you prefer)
   - **Service account description**: "Service account for reading shared drive documents"
4. Click **"Create and Continue"**
5. Skip the optional permissions (click **"Continue"**)
6. Skip granting user access (click **"Done"**)

### Step 4: Create Service Account Key

1. On the Credentials page, find your newly created service account under **"Service Accounts"**
2. Click on the service account email
3. Go to the **"Keys"** tab
4. Click **"Add Key"** > **"Create new key"**
5. Select **"JSON"** format
6. Click **"Create"**
7. A JSON file will automatically download to your computer
   - **IMPORTANT**: Keep this file secure - it's like a password!
   - Rename it to something memorable like `gdrive-credentials.json`

### Step 5: Find Your Service Account Email

1. Open the downloaded JSON file with a text editor
2. Look for the line with `"client_email"`:
   ```json
   "client_email": "gdrive-reader@your-project.iam.gserviceaccount.com"
   ```
3. **Copy this email address** - you'll need it in the next step

### Step 6: Share Your Google Drive Folder

1. Go to [Google Drive](https://drive.google.com/)
2. Create a new folder or navigate to an existing folder with your documents
3. Right-click the folder and select **"Share"**
4. In the share dialog:
   - **Paste the service account email** you copied in Step 5
   - Set the permission to **"Viewer"** (or "Editor" if you want the app to modify files)
   - **Uncheck** "Notify people" (service accounts don't receive emails)
5. Click **"Share"** or **"Send"**

### Step 7: Get Your Folder ID

1. While the folder is open in Google Drive, look at the URL in your browser
2. The URL looks like this:
   ```
   https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
   ```
3. **Copy the folder ID** - it's the long string after `/folders/`
   - In the example above: `1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456`

### Step 8: Configure Your Application

1. **Move the credentials file**:
   - Create a folder named `config` in your project if it doesn't exist
   - Move your `gdrive-credentials.json` file into the `config` folder

2. **Update your `.env` file**:
   ```env
   # Google Drive Configuration
   GDRIVE_FOLDER_ID=1aBcDeFgHiJkLmNoPqRsTuVwXyZ123456
   GDRIVE_CREDENTIALS_PATH=./config/gdrive-credentials.json
   ```
   Replace the folder ID with your actual ID from Step 7

### Step 9: Test the Connection

Run this command to test if everything is working:

```powershell
python -c "from core.update_gdrive import get_gdrive_status; print(get_gdrive_status())"
```

You should see a success message with the number of files found.

## Supported File Types

Your application can process these file types:
- PDF files (`.pdf`)
- Google Docs (automatically exported as PDF)
- Microsoft Word documents (`.docx`)
- Text files (`.txt`)

## Security Best Practices

### ✅ DO:
- Keep your `gdrive-credentials.json` file secure
- Add `gdrive-credentials.json` to your `.gitignore` file
- Give the service account only "Viewer" permissions unless it needs to edit
- Regularly review which service accounts have access to your folders

### ❌ DON'T:
- Share your credentials file publicly
- Commit the credentials file to version control
- Give more permissions than necessary
- Use your personal Google account credentials

## Troubleshooting

### "Permission denied" error
- Double-check that you shared the folder with the exact service account email
- Verify the email address in your JSON credentials matches what you shared
- Make sure you didn't accidentally revoke access

### "Folder not found" error
- Verify the folder ID in your `.env` file is correct
- Make sure you're using the folder ID, not the file ID
- Check that the folder wasn't deleted or moved

### "API not enabled" error
- Go back to Google Cloud Console
- Navigate to APIs & Services > Library
- Search for "Google Drive API" and make sure it's enabled

### No files found
- Make sure there are actually files in the shared folder
- Check that the file types are supported (PDF, DOCX, TXT)
- Verify the service account has "Viewer" permission or higher

## Adding More Folders

To index multiple folders:

1. Share each folder with the same service account email
2. Get each folder's ID from the URL
3. You can either:
   - Update `GDRIVE_FOLDER_ID` to switch between folders
   - Modify the code to process multiple folders
   - Call the pipeline with different folder IDs programmatically

## Next Steps

Once your Google Drive is connected:

1. **Index your documents**:
   ```python
   from core.update_gdrive import run_pipeline
   result = run_pipeline()
   ```

2. **Check indexed documents**:
   ```python
   from core.update_gdrive import get_indexed_documents
   docs = get_indexed_documents()
   ```

3. **Update via API**:
   ```bash
   curl -X POST "http://localhost:8080/update"
   ```

## Need Help?

If you're stuck:
1. Check the error message carefully
2. Review each step in this guide
3. Verify your credentials file is in the right location
4. Make sure the Google Drive API is enabled
5. Confirm the service account has access to your folder

---

**Remember**: Treat your service account credentials like a password - keep them secure and never share them publicly!
