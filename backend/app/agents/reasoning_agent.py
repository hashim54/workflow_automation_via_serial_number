"""Reasoning agent configuration for Microsoft Foundry.

STUB IMPLEMENTATION - NOT CURRENTLY USED
This module provides configuration for programmatically creating the reasoning
agent in Microsoft Foundry. Currently, agents are pre-created in Foundry portal and
referenced by ID in settings.

To enable programmatic agent creation:
1. Uncomment AgentManager usage in startup
2. Call agent_manager.ensure_agents() on application startup
3. Use returned agent IDs instead of config-based IDs
"""

from typing import Dict, Any

from prompts.templates import ReasoningPrompts


class ReasoningAgentConfig:
    """Configuration for reasoning agent.
    
    This agent performs final analysis over collected FSG and Phoenix data,
    providing recommendations and insights based on warranty status, service
    history, and enrichment data.
    """
    
    NAME = "reasoning-agent"
    DESCRIPTION = "Analyzes warranty, service data and provides recommendations"
    MODEL = "gpt-4o"
    
    @staticmethod
    def get_instructions() -> str:
        """Get agent system instructions from prompt templates.
        
        Returns:
            System prompt for reasoning and analysis.
        """
        return ReasoningPrompts.REASONING_SYSTEM_PROMPT
    
    @staticmethod
    def get_agent_config() -> Dict[str, Any]:
        """Get complete agent configuration for Microsoft Foundry.
        
        Returns:
            Agent configuration dict for AIProjectClient.agents.create_agent()
            
        Example:
            >>> config = ReasoningAgentConfig.get_agent_config()
            >>> agent = await client.agents.create_agent(**config)
        """
        return {
            "model": ReasoningAgentConfig.MODEL,
            "name": ReasoningAgentConfig.NAME,
            "description": ReasoningAgentConfig.DESCRIPTION,
            "instructions": ReasoningAgentConfig.get_instructions(),
            "tools": [],  # Add function tools if needed for structured output
            "temperature": 0.3,  # Higher than extraction for reasoning creativity
            "top_p": 0.95,
        }
