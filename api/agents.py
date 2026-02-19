"""
Agent Management - Agent configuration and access control
"""
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_CONFIG_PATH = PROJECT_ROOT / "knowledge-bases" / "agents.json"
_agents_cache = None


def load_agents_config():
    """Load and cache agents configuration"""
    global _agents_cache
    if _agents_cache is None:
        try:
            with open(AGENTS_CONFIG_PATH, 'r', encoding='utf-8') as f:
                _agents_cache = json.load(f)
        except Exception as e:
            print(f"Error loading agents config: {e}")
            _agents_cache = {"agents": {}, "default": "nutria"}
    return _agents_cache


def validate_agent_access(agent_id: str, access_key: str) -> bool:
    """Validate agent access key"""
    agents_config = load_agents_config()
    agent = agents_config.get("agents", {}).get(agent_id)
    if not agent:
        return False
    return agent.get("accessKey") == access_key


def get_agent_by_id(agent_id: str):
    """Get agent configuration by ID"""
    agents_config = load_agents_config()
    return agents_config.get("agents", {}).get(agent_id)


def get_agents():
    """
    Get list of available agents with public information.
    Access keys are not included for security.
    
    Returns:
        Dictionary with agents info and default agent
    """
    try:
        agents_config = load_agents_config()
        
        # Return agents without access keys (security)
        public_agents = {}
        for agent_id, agent_data in agents_config.get("agents", {}).items():
            public_agents[agent_id] = {
                "id": agent_data.get("id"),
                "name": agent_data.get("name"),
                "description": agent_data.get("description"),
                "logo": agent_data.get("logo")
            }
        
        return {
            "agents": public_agents,
            "default": agents_config.get("default", "nutria")
        }
    except Exception as e:
        return {"error": f"Error loading agents: {str(e)}"}


def get_agent_keys():
    """
    Get access keys for agents.
    Returns a mapping of agent IDs to their access keys.
    
    Returns:
        Dictionary with agent access keys
    """
    try:
        agents_config = load_agents_config()
        
        # Return access keys for each agent
        agent_keys = {}
        for agent_id, agent_data in agents_config.get("agents", {}).items():
            access_key = agent_data.get("accessKey")
            if access_key:
                agent_keys[agent_id] = access_key
        
        return agent_keys
    except Exception as e:
        return {"error": f"Error loading agents: {str(e)}"}
