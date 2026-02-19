"""
Agent Routes - Agent configuration endpoints
"""
from fastapi import APIRouter, Query
from typing import Optional

from api.agents import get_agents, get_agent_keys
from api.config import get_config

router = APIRouter()


@router.get("/api/agents")
def get_agents_endpoint():
    """
    Get list of available agents with public information.
    Access keys are not included for security.
    
    Returns:
        Dictionary with agents info and default agent
    """
    return get_agents()


@router.get("/api/agent-keys")
def get_agent_keys_endpoint():
    """
    Get access keys for agents.
    Returns a mapping of agent IDs to their access keys.
    
    Returns:
        Dictionary with agent access keys
    """
    return get_agent_keys()


@router.get("/api/get_config")
def get_config_endpoint(agent: Optional[str] = None, access_key: Optional[str] = None):
    """
    Get configuration with optional agent-specific overrides.
    
    Args:
        agent: Optional agent ID ('nutria', 'translator', or 'common')
        access_key: Required encrypted access key for agent (not required for 'common')
        
    Returns:
        Configuration dictionary (merged if agent specified)
    """
    return get_config(agent, access_key)
