"""
Prompt Loader - Centralized prompt management for all agents.
Loads prompts from prompts.yaml file for easy modification and version control.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PromptLoader:
    """Loads and manages system prompts from YAML configuration file."""
    
    def __init__(self, prompts_file: str = "prompts.yaml"):
        self.prompts_file = Path(prompts_file)
        self._prompts = {}
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from YAML file."""
        try:
            if self.prompts_file.exists():
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self._prompts = yaml.safe_load(f)
                logger.info(f"Loaded prompts from {self.prompts_file}")
            else:
                logger.warning(f"Prompts file {self.prompts_file} not found, using fallback prompts")
                self._load_fallback_prompts()
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            self._load_fallback_prompts()
    
    def _load_fallback_prompts(self):
        """Load fallback prompts if file loading fails."""
        self._prompts = {
            "orchestrator_prompt": "You are an orchestrator agent for a Slack assistant.",
            "client_agent_prompt": "You are a helpful AI assistant.",
            "slack_gateway_prompt": "You are a Slack gateway agent.",
            "observer_agent_prompt": "You are an observer agent that learns from conversations."
        }
    
    def get_orchestrator_prompt(self) -> str:
        """Get the orchestrator agent prompt."""
        return self._prompts.get("orchestrator_prompt", "You are an orchestrator agent.")
    
    def get_client_agent_prompt(self) -> str:
        """Get the client agent prompt."""
        return self._prompts.get("client_agent_prompt", "You are a helpful AI assistant.")
    
    def get_slack_gateway_prompt(self) -> str:
        """Get the Slack gateway agent prompt."""
        return self._prompts.get("slack_gateway_prompt", "You are a Slack gateway agent.")
    
    def get_observer_agent_prompt(self) -> str:
        """Get the observer agent prompt."""
        return self._prompts.get("observer_agent_prompt", "You are an observer agent.")
    
    def reload_prompts(self):
        """Reload prompts from file (useful for runtime updates)."""
        self._load_prompts()
        logger.info("Prompts reloaded")
    
    def get_all_prompts(self) -> Dict[str, Any]:
        """Get all loaded prompts."""
        return self._prompts.copy()
    
    def get_prompt_info(self) -> Dict[str, Any]:
        """Get prompt metadata and version information."""
        return {
            "version": self._prompts.get("version", "unknown"),
            "last_updated": self._prompts.get("last_updated", "unknown"),
            "description": self._prompts.get("description", ""),
            "total_prompts": len([k for k in self._prompts.keys() if k.endswith("_prompt")])
        }

# Global prompt loader instance
prompt_loader = PromptLoader()

# Convenience functions for quick access
def get_orchestrator_prompt() -> str:
    return prompt_loader.get_orchestrator_prompt()

def get_client_agent_prompt() -> str:
    return prompt_loader.get_client_agent_prompt()

def get_slack_gateway_prompt() -> str:
    return prompt_loader.get_slack_gateway_prompt()

def get_observer_agent_prompt() -> str:
    return prompt_loader.get_observer_agent_prompt()

def reload_all_prompts():
    """Reload all prompts from file."""
    prompt_loader.reload_prompts()