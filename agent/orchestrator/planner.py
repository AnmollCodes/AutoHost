"""AI Task Planner for AutoHost.

Breaks complex user goals into ordered, actionable steps before
handing them to the ReAct execution engine.
"""

from typing import Any

import structlog

from agent.llm.client import call_llm_json_async
from agent.llm.prompts import PLANNER_PROMPT

logger = structlog.get_logger(__name__)

# Tools the executor actually supports
_VALID_TOOLS = frozenset(
    {
        "shell",
        "python",
        "codebase_analyzer",
        "web_search",
        "fetch_webpage",
        "crawl_internal",
    }
)

_MAX_PLAN_STEPS = 10


class TaskPlanner:
    """AI Task Planner that decomposes complex goals into actionable steps."""

    @staticmethod
    async def create_plan(
        goal: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Generate a structured JSON plan from a user goal.

        Args:
            goal: The user's natural-language request.
            conversation_history: Optional list of prior messages.

        Returns:
            Dict with "goal" and "steps" keys. Steps may be empty
            if the task is simple or planning fails.
        """
        hist_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in (conversation_history or [])
        )

        prompt = PLANNER_PROMPT.format(
            goal=goal,
            conversation_history=hist_text or "No previous history.",
        )

        try:
            plan = await call_llm_json_async(prompt)

            # Ensure required keys exist
            if "steps" not in plan:
                plan["steps"] = []
            if "goal" not in plan:
                plan["goal"] = goal

            # Enforce step limit
            plan["steps"] = plan["steps"][:_MAX_PLAN_STEPS]

            # Validate each step
            validated = []
            for step in plan["steps"]:
                if not isinstance(step, dict):
                    continue
                if "task" not in step:
                    continue
                if step.get("tool") not in _VALID_TOOLS:
                    step["tool"] = "shell"
                validated.append(step)

            plan["steps"] = validated
            return plan

        except Exception as e:
            logger.error("planner_failed", error=str(e))
            # Return empty plan so the ReAct agent handles it normally
            return {"goal": goal, "steps": []}
