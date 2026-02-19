
# =====================================================
# Imports - Main application imports
# =====================================================
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pathlib import Path

# Import route modules
from api.routes import query, translation, tts, admin, agents, sessions, update

# =====================================================
# Configuration & Application Setup
# =====================================================
PROJECT_ROOT = Path(__file__).parent
env_path = PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=env_path)

app = FastAPI(title="IMX Multi Agent")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://imx-multi-agent.web.app",
        "https://imx-multi-agent.firebaseapp.com",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "templates"))

# =====================================================
# Include API Routes
# =====================================================
app.include_router(query.router, tags=["query"])
app.include_router(translation.router, tags=["translation"])
app.include_router(tts.router, tags=["tts"])
app.include_router(admin.router, tags=["admin"])
app.include_router(agents.router, tags=["agents"])
app.include_router(sessions.router, tags=["sessions"])
app.include_router(update.router, tags=["update"])

# =====================================================
# Main Routes
# =====================================================
@app.get("/")
def home():
    """API root endpoint - frontend is hosted on Firebase"""
    return {"status": "ok", "message": "IMX Multi Agent API"}


@app.get("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok"}


# =====================================================
# Run Application
# =====================================================
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

