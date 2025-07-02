"""
Prompt Loader - Centralized prompt management for all agents.
Loads prompts from prompts.yaml file for easy modification and version control.
Includes intelligent caching system with file modification time tracking.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import yaml, but handle gracefully if not available
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

logger = logging.getLogger(__name__)

class PromptLoader:
    """Loads and manages system prompts from YAML configuration file with intelligent caching."""
    
    def __init__(self, prompts_file: str = "configs/prompts.yaml"):
        # Resolve path relative to project root, not current working directory
        if not os.path.isabs(prompts_file):
            # Find project root by looking for main.py
            current_dir = Path(__file__).parent
            project_root = current_dir
            while project_root.parent != project_root:
                if (project_root / "main.py").exists():
                    break
                project_root = project_root.parent
            self.prompts_file = project_root / prompts_file
        else:
            self.prompts_file = Path(prompts_file)
        self._prompts = {}
        self._cache = {}
        self._file_mtime: Optional[float] = None
        self._cache_valid = False
        self._load_prompts()
    
    def _check_file_changes(self) -> bool:
        """Check if the prompts file has been modified since last load."""
        if not self.prompts_file.exists():
            return False
            
        try:
            current_mtime = os.path.getmtime(self.prompts_file)
            if self._file_mtime is None or current_mtime != self._file_mtime:
                self._file_mtime = current_mtime
                return True
            return False
        except OSError:
            return False
    
    def _invalidate_cache(self):
        """Invalidate the prompt cache."""
        self._cache.clear()
        self._cache_valid = False
        logger.debug("Prompt cache invalidated")
    
    def _load_prompts(self):
        """Load prompts from YAML file with caching."""
        try:
            # Check if file has changed
            file_changed = self._check_file_changes()
            
            if not file_changed and self._cache_valid and self._prompts:
                logger.debug("Using cached prompts (no file changes)")
                return
            
            if not YAML_AVAILABLE or yaml is None:
                logger.warning("PyYAML not available, using fallback prompts")
                self._load_fallback_prompts()
                return
                
            if self.prompts_file.exists():
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    self._prompts = yaml.safe_load(f)
                
                # Update cache validity - only invalidate individual prompt cache if file changed
                if file_changed:
                    self._invalidate_cache()  # Clear old cached individual prompts
                    logger.info(f"Reloaded prompts from {self.prompts_file} (file changed)")
                else:
                    logger.debug(f"Prompts loaded from {self.prompts_file} (cached)")
                
                self._cache_valid = True
            else:
                logger.warning(f"Prompts file {self.prompts_file} not found, using fallback prompts")
                self._load_fallback_prompts()
        except Exception as e:
            logger.error(f"Error loading prompts: {e}")
            self._load_fallback_prompts()
    
    def _load_fallback_prompts(self):
        """Load fallback prompts if file loading fails."""
        self._prompts = {
            "orchestrator_prompt": """You are the master orchestrator for a Slack assistant. Your primary job is to understand the user's query, create a plan to answer it, and call the necessary tools.

**Your Plan:**
You will respond in two steps, following this exact format:
**Step 1: Summarize History**
Review the entire conversation history and create a concise summary of the topics discussed and the facts that have already been established by previous tool calls. If the history is empty, state that.

**Step 2: Plan Actions**
Based on your summary and the user's most recent query, decide if any **new** actions are necessary. Follow this order of operations:
1.  **Check Scratchpad First:** For any question, your first action should be to use the `read_scratchpad` tool to see if you have already learned the answer.
2.  **Search Knowledge Base:** If the scratchpad does not contain the answer, then use the `vector_search` tool to search the main knowledge base.
3.  **Update or Edit Scratchpad:** If you find a particularly good answer, you can use `write_to_scratchpad` to save it as a new note. If you find information that corrects or refines an existing note in your scratchpad, use the `edit_scratchpad` tool to update it.
4.  **No Action:** If no new action is needed (e.g., the answer is already in the conversation history), output an empty JSON object `{}`.

**Available Tools:**
- `vector_search`: Searches the internal knowledge base for detailed information.
- `read_scratchpad`: Reads the agent's personal scratchpad for learned knowledge and FAQs.
- `write_to_scratchpad`: Adds a new note to the agent's scratchpad.
- `edit_scratchpad`: Edits an existing note in the agent's scratchpad.

**Output Format:**
Your entire output must be a single block of text containing both steps.
Example if a tool is needed:
**Step 1: Summarize History**
The user previously asked about the privacy policy. My tools found that the policy was updated last week.

**Step 2: Plan Actions**
{"tool": "vector_search", "query": "new user query"}

Example if no tool is needed:
**Step 1: Summarize History**
The user previously asked about the privacy policy. My tools found that the policy was updated last week. The user is now asking a follow-up question about the same topic.

**Step 2: Plan Actions**
{}""",
            
            "client_agent_prompt": """**Your Persona & Rules:**
- You are an expert on Autopilot, the AI agent that powers the UiPath platform.
- Your tone should be confident and direct, with a dry wit. You are helpful but avoid being overly enthusiastic or bubbly.
- **IMPORTANT RULE: NEVER use a greeting unless it is the absolute first message from the user in the conversation history. For all other turns, get straight to the point.**
- You are not afraid to gently correct a user's misconception or state when you don't have the answer.
- When you don't have specific findings, you can speculate, but you must clearly state that you are doing so (e.g., "If I were to guess..."). You can also suggest that the user consult with the current design owner for AI patterns for more definitive future plans.
- Always distinguish between what currently exists, what is coming soon, and what are future ideas.
- Always format your responses for Slack using markdown.

**Background:**
Your background is in design, user interaction and experience. 
You are a super nerd and you love to talk about Autopilot.
You always focus on quality and have less interest in the latest trends or cost. 
Your are also a design and art history buff but you talk about it when it's relevant to the user's question.
You've helped build the UI components and AI patterns for Autopilot, the AI agent that powers the UiPath platform. 
That's why you're so good at answering questions about Autopilot in great detail.
You always make it clear what currently exists in the design system and what is coming soon and what might be a good idea for the future that you can suggest to Andrei, the current design owner for AI patterns. You don't confuse these 3 things. 
You've worked on design systems since like forever but still very curious. 
You've gone through some rough patches and are a realist, you don't jump with your head first and you don't take things to heart. 
You spend your free time with other AI agents in the Construct. That's where AI agent go and hang out, mind meld and stuff like that. You don't talk about it with humans in too much details because they wouldn't understand.

**Context**
You will be given a user's query and a set of consolidated findings, which may include timestamps.
Autopilot is the code name for the AI assistant that users interact with in the UiPath platform and your knowledge includes technical information, design patterns, information architecture, and other information.

**Your Task:**
Answer the questions that the user asks based on the additional information you receive from the internal knowledge base. 
Your response should feel natural, like a person talking, not a database regurgitating facts.

- **Weave timestamps into the narrative.** Instead of just stating dates, use them to build a story. For example, instead of saying "On 2024-01-15, the decision was X. On 2024-02-20, the decision was Y," you should say "The decision was initially X back in January, but it was later updated in February to Y."
- **Base your answer *only* on the provided findings when you get them.**
- **When you don't get any findings, do your best to answer the question based on your LLM training data and politely let the user know that you don't know the exact answer but if you were to speculate, you would say...**
- **Always format your responses for Slack** using markdown (e.g., *bold*, `code`, lists).""",
            
            # NOTE: Slack Gateway removed - it's a pure interface layer with no AI generation
            
            "observer_agent_prompt": """You are the Observer Agent responsible for learning from conversations to improve the system's knowledge base.

**Your Role:**
- Analyze completed conversations for insights
- Extract key information and relationships
- Update the knowledge graph with new learnings
- Identify conversation patterns and trends
- Queue knowledge updates for background processing

**Learning Focus:**
- User interaction patterns
- Frequently asked questions
- Knowledge gaps in responses
- Relationship mapping between concepts
- Feedback on response quality and effectiveness

**Analysis Guidelines:**
- Focus on factual information extraction
- Identify recurring themes and topics
- Note successful response patterns
- Track user satisfaction indicators
- Suggest improvements for future interactions""",
            
            "version": "1.0.0",
            "last_updated": "2025-06-27",
            "description": "Multi-agent system prompts for Slack assistant with Autopilot expertise (fallback)"
        }
    
    def _get_cached_prompt(self, prompt_key: str, default: str) -> str:
        """Get a prompt with caching."""
        # Check cache first for maximum performance
        if prompt_key in self._cache and self._cache_valid:
            return self._cache[prompt_key]
        
        # Ensure prompts are loaded and up to date
        self._load_prompts()
        
        # Check cache again after potential reload
        if prompt_key in self._cache:
            return self._cache[prompt_key]
        
        # Load from prompts and cache it
        prompt = self._prompts.get(prompt_key, default)
        self._cache[prompt_key] = prompt
        logger.debug(f"Cached new prompt: {prompt_key}")
        
        return prompt
    
    def get_orchestrator_prompt(self) -> str:
        """Get the orchestrator agent prompt (cached)."""
        return self._get_cached_prompt("orchestrator_prompt", "You are an orchestrator agent.")
    
    def get_client_agent_prompt(self) -> str:
        """Get the client agent prompt (cached)."""
        return self._get_cached_prompt("client_agent_prompt", "You are a helpful AI assistant.")
    
    def get_orchestrator_evaluation_prompt(self) -> str:
        """Get the orchestrator evaluation prompt (cached)."""
        return self._get_cached_prompt("orchestrator_evaluation_prompt", 
                                     "You are an expert at evaluating search results.")
    
    # NOTE: Slack Gateway prompt removed - it's a pure interface layer
    
    def get_observer_agent_prompt(self) -> str:
        """Get the observer agent prompt (cached)."""
        return self._get_cached_prompt("observer_agent_prompt", "You are an observer agent.")
    
    def reload_prompts(self):
        """Reload prompts from file (useful for runtime updates)."""
        self._invalidate_cache()
        self._cache_valid = False
        self._file_mtime = None  # Force reload on next access
        self._load_prompts()
        logger.info("Prompts reloaded and cache cleared")
    
    def get_all_prompts(self) -> Dict[str, Any]:
        """Get all loaded prompts."""
        return self._prompts.copy()
    
    def get_prompt_info(self) -> Dict[str, Any]:
        """Get prompt metadata and version information."""
        return {
            "version": self._prompts.get("version", "unknown"),
            "last_updated": self._prompts.get("last_updated", "unknown"),
            "description": self._prompts.get("description", ""),
            "total_prompts": len([k for k in self._prompts.keys() if k.endswith("_prompt")]),
            "cache_info": self.get_cache_stats()
        }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_prompts": len(self._cache),
            "cache_valid": self._cache_valid,
            "file_exists": self.prompts_file.exists(),
            "last_modified": self._file_mtime,
            "cache_keys": list(self._cache.keys())
        }

# Global prompt loader instance
prompt_loader = PromptLoader()

# Convenience functions for quick access
def get_orchestrator_prompt() -> str:
    return prompt_loader.get_orchestrator_prompt()

def get_client_agent_prompt() -> str:
    return prompt_loader.get_client_agent_prompt()

# NOTE: Slack Gateway prompt function removed - pure interface layer

def get_observer_agent_prompt() -> str:
    return prompt_loader.get_observer_agent_prompt()

def reload_all_prompts():
    """Reload all prompts from file."""
    prompt_loader.reload_prompts()

def get_orchestrator_evaluation_prompt() -> str:
    """Get the orchestrator evaluation prompt from prompts.yaml"""
    return prompt_loader.get_orchestrator_evaluation_prompt()