"""
Configuration Management - Configuration loading and merging
"""
from pathlib import Path
import json
from typing import Optional
from api.agents import validate_agent_access, get_agent_by_id


PROJECT_ROOT = Path(__file__).parent.parent


def deep_merge(base_config: dict, override_config: dict) -> dict:
    """
    Deep merge two configuration dictionaries.
    Override values take precedence over base values.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Merged configuration dictionary
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Override value
            result[key] = value
    
    return result


def get_config(agent: Optional[str] = None, access_key: Optional[str] = None):
    """
    Get configuration with optional agent-specific overrides.
    
    Args:
        agent: Optional agent ID ('nutria', 'translator', or 'common')
        access_key: Required encrypted access key for agent (not required for 'common')
        
    Returns:
        Configuration dictionary (merged if agent specified)
    """
    try:
        # Load the main shared configuration
        main_config_path = PROJECT_ROOT / "knowledge-bases" / "common" / "common.json"
        main_config = {}
        if main_config_path.exists():
            with open(main_config_path, 'r', encoding='utf-8') as f:
                main_config = json.load(f)

        # If no agent specified, return shared config
        if not agent:
            return main_config
        
        # 'common' agent doesn't require access key validation
        if agent != 'common':
            # Validate access key for specific agents
            if not access_key or not validate_agent_access(agent, access_key):
                return {"error": "invalid access key"}
            
            # Get agent info
            agent_info = get_agent_by_id(agent)
            if not agent_info:
                return {"error": "agent not found"}
        
        # Load agent-specific configuration
        agent_config_path = None
        # Load shared configuration
        if agent == "common":
            agent_config_path = PROJECT_ROOT / "knowledge-bases" / "common" / "config.json"
        elif agent == "nutria":
            agent_config_path = PROJECT_ROOT / "knowledge-bases" / "nutria" / "config.json"
        elif agent == "translator":
            agent_config_path = PROJECT_ROOT / "knowledge-bases" / "translator" / "config.json"
        else:
            # Unknown agent, return error
            return {"error": "agent not found"}
        
        # Load and merge agent config
        if agent_config_path and agent_config_path.exists():
            with open(agent_config_path, 'r', encoding='utf-8') as f:
                agent_config = json.load(f)
            merged_config = deep_merge(main_config, agent_config)
            return merged_config
        
        return {"error": "config not found"}
        
    except FileNotFoundError:
        return {"error": "config not found"}
    except Exception as e:
        return {"error": f"Error loading config: {str(e)}"}
