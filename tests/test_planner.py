"""Tests for the AI Task Planner."""

import pytest
from unittest.mock import AsyncMock, patch

from agent.orchestrator.planner import TaskPlanner


@pytest.mark.asyncio
async def test_planner_creates_valid_plan():
    """Planner should return a well-structured plan."""
    with patch(
        "agent.orchestrator.planner.call_llm_json_async",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = {
            "goal": "Test goal",
            "steps": [
                {"id": 1, "task": "Load data", "tool": "python"},
                {"id": 2, "task": "List files", "tool": "shell"},
            ],
        }

        plan = await TaskPlanner.create_plan("Do something complex")

        assert "steps" in plan
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["tool"] == "python"
        assert plan["steps"][1]["tool"] == "shell"


@pytest.mark.asyncio
async def test_planner_handles_errors_gracefully():
    """Planner should return empty steps on LLM failure."""
    with patch(
        "agent.orchestrator.planner.call_llm_json_async",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.side_effect = Exception("LLM Error")

        plan = await TaskPlanner.create_plan("Do something complex")

        assert plan["goal"] == "Do something complex"
        assert plan["steps"] == []


@pytest.mark.asyncio
async def test_planner_fixes_invalid_tools():
    """Planner should default unknown tools to 'shell'."""
    with patch(
        "agent.orchestrator.planner.call_llm_json_async",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = {
            "goal": "Test goal",
            "steps": [
                {"id": 1, "task": "Do some magic", "tool": "invalid_tool"},
            ],
        }

        plan = await TaskPlanner.create_plan("Do something complex")

        assert plan["steps"][0]["tool"] == "shell"


@pytest.mark.asyncio
async def test_planner_limits_steps():
    """Planner should enforce max 10 steps."""
    with patch(
        "agent.orchestrator.planner.call_llm_json_async",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = {
            "goal": "Huge task",
            "steps": [
                {"id": i, "task": f"Step {i}", "tool": "shell"}
                for i in range(20)
            ],
        }

        plan = await TaskPlanner.create_plan("Huge task")

        assert len(plan["steps"]) <= 10


@pytest.mark.asyncio
async def test_planner_skips_malformed_steps():
    """Planner should skip steps without a 'task' key."""
    with patch(
        "agent.orchestrator.planner.call_llm_json_async",
        new_callable=AsyncMock,
    ) as mock_llm:
        mock_llm.return_value = {
            "goal": "Test",
            "steps": [
                {"id": 1, "tool": "shell"},  # missing "task"
                {"id": 2, "task": "Valid step", "tool": "python"},
                "not a dict",  # invalid
            ],
        }

        plan = await TaskPlanner.create_plan("Test")

        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["task"] == "Valid step"
