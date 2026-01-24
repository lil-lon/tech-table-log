"""
Core Podcast agents definition
"""

from pathlib import Path
from typing import Literal

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    HookContext,
    HookInput,
    HookJSONOutput,
    HookMatcher,
)

from podcast_agents import config
from podcast_agents.utils.logger import setup_logging

# HookEvent type matches SDK's internal definition
HookEvent = Literal[
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
]

logger = setup_logging(__name__)
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(agent_name: str) -> str:
    """Load a prompt from the prompts directory.

    Args:
        agent_name: Name of the prompt file (without .md extension)

    Returns:
        The prompt content with podcast context prepended
    """
    prompt_path = PROMPTS_DIR / f"{agent_name}.md"
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read().strip()

    # Add podcast context
    context_path = PROMPTS_DIR / "about_podcast.md"
    with open(context_path, "r", encoding="utf-8") as f:
        context = f.read().strip()
    return f"About this Podcast: {context}\n\n---\n\n{prompt}"


def build_workflow_agent() -> ClaudeAgentOptions:
    """
    Build usual podcast workflow agent.

    This function creates a master agent with three specialized subagents:
    - transcribe: Audio transcription using Whisper
    - review: Technical accuracy and risk review
    - modify: Transcript correction and formatting

    """
    # Ensure output directories exist
    config.TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    config.MODIFIED_TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    config.REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    # Load prompts from markdown files (about_podcast context is auto-included)
    transcribe_prompt = load_prompt("transcribe")
    modify_prompt = load_prompt("modify")
    review_prompt = load_prompt("review")

    # Define bash validation hooks
    hooks: dict[HookEvent, list[HookMatcher]] = {
        "PreToolUse": [
            HookMatcher(
                matcher="Bash",
                hooks=[_validate_bash_command],
            )
        ]
    }

    # Define all subagents using AgentDefinition
    agents = {
        "transcribe": AgentDefinition(
            description=(
                "Audio transcription specialist. Use for transcribing podcast audio files "
                "to text using Whisper model. You MUST pass target episode number to this agent. "
                f"Audio directory: {config.AUDIO_DIR}, "
                f"Output directory: {config.TRANSCRIPTS_DIR}"
            ),
            prompt=transcribe_prompt,
            tools=["Read", "Write", "Bash", "Glob", "Grep", "TaskOutput"],
            model="opus",
        ),
        "modify": AgentDefinition(
            description=(
                "Transcript correction and formatting specialist. Use for correcting transcription "
                "errors, identifying speakers, and formatting transcripts. "
                "Handles: typo correction, speaker identification, formatting. "
                f"Input directory: {config.TRANSCRIPTS_DIR}, "
                f"Output directory: {config.MODIFIED_TRANSCRIPTS_DIR}"
            ),
            prompt=modify_prompt,
            tools=["Read", "Write", "Glob", "Grep"],
            model="opus",
        ),
        "review": AgentDefinition(
            description=(
                "Technical podcast review specialist. Use for reviewing podcast transcripts "
                "for technical accuracy, terminology issues, and reputational risks. "
                "Handles: technical accuracy review, fact-checking, controversy detection. "
                f"Input directory: {config.MODIFIED_TRANSCRIPTS_DIR}, "
                f"Output directory: {config.REVIEWS_DIR}, "
                "Episode assets: ./episode-assets/"
            ),
            prompt=review_prompt,
            tools=["Read", "Write", "Glob", "Grep", "WebSearch"],
            model="opus",
        ),
    }

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Glob", "Grep", "TaskOutput", "Task"],
        permission_mode="acceptEdits",
        cwd=str(Path.cwd()),
        hooks=hooks,
        agents=agents,
        system_prompt=(load_prompt("master")),
    )

    return options


def build_planner_agent() -> ClaudeAgentOptions:
    """
    Build planner agent to create execution plan from user request.

    Returns:
        planner agent definition (ClaudeAgentOptions)
    """
    planner_prompt = load_prompt("planner")

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Glob"],
        permission_mode="acceptEdits",
        cwd=str(Path.cwd()),
        system_prompt=planner_prompt,
    )
    return options


async def _validate_bash_command(
    input_data: HookInput, _tool_use_id: str | None, _context: HookContext
) -> HookJSONOutput:
    """
    Validate that Bash commands only execute Python scripts.

    Args:
        input_data: Hook input data containing tool information
        _tool_use_id: Tool use ID (unused)
        _context: Hook context (unused)

    Returns:
        HookJSONOutput: Hook output with permission decision
    """
    if input_data.get("hook_event_name") != "PreToolUse":
        return {}

    # Get the command from tool input (PreToolUseHookInput has tool_input)
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""

    # Empty command check
    if not command:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Empty command is not allowed",
            }
        }

    # Check if command starts with allowed prefixes
    allowed_prefixes = "uv run python "
    if not command.startswith(allowed_prefixes):
        logger.warning(f"[BLOCKED] Command: {command}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Security violation: Only 'python' or 'uv run python' commands are allowed. "
                    f"Attempted command: {command}"
                ),
            }
        }

    # Additional validation for the specific module
    if "podcast_agents.tools.transcribe" not in command:
        logger.warning(f"[BLOCKED] Non-transcribe command: {command}")
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Only podcast_agents.tools.transcribe module is allowed. "
                    f"Attempted command: {command}"
                ),
            }
        }

    # Command is valid
    logger.info(f"[ALLOWED] Command: {command}")
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Command validated successfully",
        }
    }
