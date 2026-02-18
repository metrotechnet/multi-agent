# Firebase Frontend Deployment Guide

This guide explains how to deploy the IMX Multi Agent frontend to Firebase Hosting.

## Prerequisites

1. **Node.js and npm** installed
2. **Firebase CLI** installed:
   ```bash
   npm install -g firebase-tools
   ```
3. **Firebase project** created at [Firebase Console](https://console.firebase.google.com/)

## Initial Setup

### 1. Login to Firebase

```bash
firebase login
```

### 2. Initialize Firebase Project (First time only)

If you haven't created a Firebase project yet:

```bash
firebase projects:list
```

To link to a specific project, update `.firebaserc` with your project ID:

```json
{
  "projects": {
    "default": "your-project-id"
  }
}
```

Or run:
```bash
firebase use --add
```

### 3. Configure Backend URL

Add the backend URL to your `.env` file:

```
BACKEND_URL=https://your-backend-url.run.app
```

If deploying to Google Cloud Run, use the Cloud Run service URL.

## Deployment

### Option 1: Windows Batch Script

```cmd
deploy-frontend.bat
```

This script will:
1. Check for Firebase CLI installation
2. Copy frontend files to `public/` directory
3. Update file paths for Firebase hosting
4. Prompt you to deploy or preview locally

### Option 2: PowerShell Script

```powershell
.\deploy-frontend.ps1
```

Same functionality as the batch script but with better cross-platform support.

### Option 3: Manual Deployment

```bash
# Prepare files
mkdir public
mkdir public\static
copy templates\index.html public\index.html
xcopy static\* public\static\ /E /Y

# Deploy
firebase deploy --only hosting
```

## Testing Locally

Preview your site locally before deploying:

```bash
firebase emulators:start --only hosting
```

This will start a local server at `http://localhost:5000`

## Project Structure

```
imx-multi-agent/
├── static/              # Static assets (CSS, JS, images)
│   ├── script.js
│   ├── style.css
│   ├── favicon.ico
│   └── logo-imx.png
├── templates/           # HTML templates
│   └── index.html
├── public/             # Generated directory for Firebase (gitignored)
│   ├── index.html
│   └── static/
├── firebase.json       # Firebase configuration
├── .firebaserc        # Firebase project reference
└── deploy-frontend.bat # Deployment script
```

## Firebase Configuration

The `firebase.json` file includes:

- **Public directory**: `public/`
- **Rewrites**: Routes API calls and serves SPA
- **Cache headers**: Optimizes static asset caching
- **Ignore patterns**: Excludes Python files and directories

## Updating the Frontend

After making changes to `static/` or `templates/`:

1. Run the deployment script
2. Or manually copy files and deploy:
   ```bash
   # Update public directory
   copy templates\index.html public\index.html
   xcopy static\* public\static\ /E /Y
   
   # Deploy
   firebase deploy --only hosting
   ```

## Connecting Frontend to Backend

The frontend needs to know where the backend API is located. This is configured via:

1. **BACKEND_URL** in `.env` file
2. Automatically injected into `public/static/config.js` during deployment

The deployment script (`deploy-frontend.bat`) automatically:
- Reads `BACKEND_URL` from `.env`
- Creates `public/static/config.js` with the backend URL
- Updates `index.html` to use relative paths for Firebase

Your `script.js` should load the backend URL:

```javascript
// Load backend URL from config if available
const BACKEND_URL = window.BACKEND_URL || 'http://localhost:8080';

// Use in API calls
fetch(`${BACKEND_URL}/query`, {
  method: 'POST',
  // ...
});
```

## CORS Configuration

The backend must allow requests from your Firebase domain. In `app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imx-multi-agent.web.app",
        "https://imx-multi-agent.firebaseapp.com",
        "http://localhost:8080"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

After updating CORS settings, redeploy the backend:
```bash
.\deploy-backend.bat
```

## Troubleshooting

### Firebase CLI not found
```bash
npm install -g firebase-tools
```

### Permission denied
```bash
firebase login --reauth
```

### Deployment fails
- Check `.firebaserc` has correct project ID
- Ensure you're logged in: `firebase login`
- Verify project exists: `firebase projects:list`

### API calls not working
- Check `BACKEND_URL` in `.env`
- Verify CORS settings on backend (should include Firebase domains)
- Check browser console for errors
- Verify backend is deployed and accessible
- Test backend URL directly: `curl https://your-backend.run.app/api/get_config`

## Production Checklist

Before deploying to production:

- [ ] Update `BACKEND_URL` in `.env` to production backend
- [ ] Test locally with `firebase emulators:start`
- [ ] Verify all static assets load correctly
- [ ] Check API endpoints are accessible
- [ ] Test on multiple browsers
- [ ] Enable HTTPS (automatic with Firebase)
- [ ] Set up custom domain (optional)

## Custom Domain

To use a custom domain:

1. Go to Firebase Console → Hosting
2. Click "Add custom domain"
3. Follow the DNS configuration steps
4. Wait for SSL certificate provisioning (can take up to 24 hours)

## Monitoring

View deployment history and analytics:

```bash
firebase hosting:channel:list
```

Or visit: https://console.firebase.google.com/project/YOUR_PROJECT/hosting

## CI/CD Integration

For automated deployments, add to your CI/CD pipeline:

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Deploy using service account
firebase deploy --only hosting --token "$FIREBASE_TOKEN"
```

Get token: `firebase login:ci`
