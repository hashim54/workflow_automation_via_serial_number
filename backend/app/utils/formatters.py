"""Formatting utilities for workflow data."""


def format_thought_process_summary(thought_process: list[dict]) -> str:
    """
    Format thought process list into human-readable summary.
    
    Args:
        thought_process: List of workflow step details from WorkflowState
        
    Returns:
        Formatted summary string for display or storage
        
    Example:
        >>> thought_process = [
        ...     {"step": "fsg_lookup", "details": {"status": "success"}},
        ...     {"step": "phoenix_enrichment", "details": {"records_found": 3}}
        ... ]
        >>> print(format_thought_process_summary(thought_process))
        Workflow Execution Summary:
        
        1. Fsg Lookup
           - status: success
        
        2. Phoenix Enrichment
           - records_found: 3
    """
    if not thought_process:
        return "No workflow steps recorded."
    
    summary_lines = ["Workflow Execution Summary:", ""]
    
    for i, step in enumerate(thought_process, 1):
        step_name = step.get("step", "unknown")
        details = step.get("details", {})
        
        summary_lines.append(f"{i}. {step_name.replace('_', ' ').title()}")
        
        for key, value in details.items():
            if key != "serial_number":  # Don't repeat serial number
                summary_lines.append(f"   - {key}: {value}")
        
        summary_lines.append("")
    
    return "\n".join(summary_lines)
