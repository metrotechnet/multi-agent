"""
Update Routes - Google Drive document indexing endpoint with multi-agent support
"""
from fastapi import APIRouter, Request, Query
from datetime import datetime
from typing import Optional

from core.update_gdrive import run_pipeline

router = APIRouter()


@router.post("/update")
def update_pipeline(request: Request, agent: Optional[str] = Query(default="nutria", description="Agent/Knowledge base to update")):
    """
    Endpoint to trigger Google Drive document indexing pipeline.
    Called by Cloud Scheduler daily at 3 AM.
    
    Args:
        agent: Agent/knowledge base identifier (default: nutria)
    """
    try:
        print(f"[{datetime.now().isoformat()}] Pipeline update triggered for agent: {agent}")
        print(f"User-Agent: {request.headers.get('user-agent', 'Unknown')}")
        
        result = run_pipeline(agent=agent)
        
        if result.get("error"):
            print(f"❌ Pipeline error: {result['error']}")
            return {
                "status": "error",
                "message": result['error'],
                "authenticated": result.get("authenticated", False)
            }
        
        processed = result.get("processed", 0)
        total = result.get("total", 0)
        
        print(f"✅ Pipeline completed for {agent}: {processed}/{total} documents processed")
        
        return {
            "status": "success",
            "message": f"Pipeline executed successfully for {agent}",
            "agent": agent,
            "processed": processed,
            "total": total,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Pipeline exception: {str(e)}")
        return {
            "status": "error",
            "message": f"Pipeline failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }
