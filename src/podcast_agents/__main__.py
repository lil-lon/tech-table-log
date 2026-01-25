"""
Interactive workflow orchestrator for Tech Table Log podcast production.

Usage:
    uv run python -m podcast_agents
"""

import asyncio
from pathlib import Path

from podcast_agents import config
from podcast_agents.agent import build_planner_agent, build_workflow_agent, run_agent
from podcast_agents.utils.logger import setup_logging

logger = setup_logging(__name__)


async def run_interactive_workflow(user_prompt: str) -> None:
    """
    Interactive usual workflow with planning and execution phases.

    1. Run planner agent to create execution plan
    2. Display plan and get user approval
    3. Run workflow agent to execute the plan
    """
    print("\n" + "=" * 60)
    print("Tech Table Log - Interactive Workflow")
    print("=" * 60)

    # Phase 1: Planning
    print("Analyzing request and creating plan...\n")

    options = build_planner_agent()
    written_files = await run_agent(options, user_prompt)

    plan_file_path = written_files[0] if written_files else None
    if not plan_file_path:
        print("Failed to create execution plan. Please try again.")
        return

    # Validate plan file path
    plans_dir = config.PLANS_DIR.resolve()
    resolved_plan_path = Path(plan_file_path).resolve()
    if resolved_plan_path.parent != plans_dir:
        print(f"Error: Plan path is outside allowed directory: {plan_file_path}")
        return

    # Read and display the plan file
    try:
        with open(resolved_plan_path, "r", encoding="utf-8") as f:
            plan_content = f.read()
    except FileNotFoundError:
        print(f"Error: Plan file not found at {resolved_plan_path}")
        return

    print(f"Plan saved to: {resolved_plan_path}")
    print("\nTODO List:")
    print("-" * 60)
    print(plan_content)
    print("-" * 60)

    # Phase 2: Approval
    approval = input("Proceed with execution? (y/n): ")
    if approval.lower() != "y":
        print("Cancelled")
        return

    # Phase 3: Execution
    print("\n" + "=" * 60)
    print("Executing tasks...")
    print("=" * 60 + "\n")

    try:
        options = build_workflow_agent()
        await run_agent(options, f"Please execute the plan at {resolved_plan_path}")
        print("\n" + "=" * 60)
        print("All tasks completed successfully!")
        print("=" * 60 + "\n")
    except Exception as e:
        print(f"\nWorkflow failed: {e}\n")
        logger.error(f"Workflow execution failed: {e}", exc_info=True)


async def main():
    """Main entry point for interactive workflow CLI."""
    print("\n" + "=" * 60)
    print("Tech Table Log - Interactive Podcast Production")
    print("=" * 60)
    print("\nExamples:")
    print("  - 'Process episode 12 completely'")
    print("  - 'Transcribe and modify episode 13'")
    print("  - 'Review episode 14'")
    print("  - 'Transcribe episodes 10, 11, and 12'")
    print()

    user_request = input("Enter your request: ").strip()

    if not user_request:
        print("No request provided. Exiting.")
        return

    await run_interactive_workflow(user_request)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nCancelled by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        raise
