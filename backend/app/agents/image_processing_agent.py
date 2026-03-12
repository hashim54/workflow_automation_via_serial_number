"""Image processing agent configuration for Microsoft Foundry.

STUB IMPLEMENTATION - NOT CURRENTLY USED
This module provides configuration for programmatically creating the image processing
agent in Microsoft Foundry. Currently, agents are pre-created in Foundry portal and
referenced by ID in settings.

To enable programmatic agent creation:
1. Uncomment AgentManager usage in startup
2. Call agent_manager.ensure_agents() on application startup
3. Use returned agent IDs instead of config-based IDs
"""

from typing import Dict, Any

from prompts.templates import ImageAnalysisPrompts


class ImageProcessingAgentConfig:
    """Configuration for image processing agent.
    
    This agent uses vision-capable models to extract serial numbers and device
    information from uploaded images.
    """
    
    NAME = "image-processing-agent"
    DESCRIPTION = "Extracts serial numbers from device images using vision models"
    MODEL = "gpt-4o"  # Vision-capable model required
    
    @staticmethod
    def get_instructions() -> str:
        """Get agent system instructions from prompt templates.
        
        Returns:
            System prompt for serial number extraction.
        """
        return ImageAnalysisPrompts.SERIAL_NUMBER_EXTRACTION_SYSTEM_PROMPT
    
    @staticmethod
    def get_agent_config() -> Dict[str, Any]:
        """Get complete agent configuration for Microsoft Foundry.
        
        Returns:
            Agent configuration dict for AIProjectClient.agents.create_agent()
            
        Example:
            >>> config = ImageProcessingAgentConfig.get_agent_config()
            >>> agent = await client.agents.create_agent(**config)
        """
        return {
            "model": ImageProcessingAgentConfig.MODEL,
            "name": ImageProcessingAgentConfig.NAME,
            "description": ImageProcessingAgentConfig.DESCRIPTION,
            "instructions": ImageProcessingAgentConfig.get_instructions(),
            "tools": [],  # Add tools if needed (code_interpreter, file_search, etc.)
            "temperature": 0.1,  # Low temperature for deterministic extraction
            "top_p": 0.95,
        }
