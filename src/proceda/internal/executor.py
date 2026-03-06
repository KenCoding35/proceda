"""Core executor: drives step-by-step skill execution."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from proceda.events import EventType, RunEvent
from proceda.exceptions import ApprovalRejectedError, ExecutionError
from proceda.human import HumanInterface
from proceda.internal.context import ContextManager
from proceda.internal.tool_executor import ToolExecutor
from proceda.llm.prompts import build_step_prompt, build_system_prompt
from proceda.llm.runtime import LLMRuntime
from proceda.llm.tool_schemas import get_control_tool_schemas, is_control_tool
from proceda.session import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ClarificationRequest,
    ErrorContext,
    RunMessage,
    RunSession,
    RunStatus,
    ToolCall,
)
from proceda.skill import Skill

logger = logging.getLogger(__name__)

# Guard-rail constants
MAX_TEXT_ONLY_ITERATIONS = 5
MAX_TOOL_CALL_ITERATIONS = 50

EmitFn = Callable[[RunEvent], Coroutine[Any, Any, None]]


class Executor:
    """Executes a skill step-by-step, driving the LLM and handling human interactions."""

    def __init__(
        self,
        skill: Skill,
        session: RunSession,
        llm: LLMRuntime,
        tool_executor: ToolExecutor | None,
        human: HumanInterface,
        emit: EmitFn,
        context_manager: ContextManager | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
    ) -> None:
        self._skill = skill
        self._session = session
        self._llm = llm
        self._tool_executor = tool_executor
        self._human = human
        self._emit = emit
        self._context = context_manager or ContextManager()
        self._app_tool_schemas = tool_schemas or []

    async def execute(self) -> None:
        """Run the full skill from current step to completion."""
        session = self._session

        # Initialize with system prompt
        system_prompt = build_system_prompt(self._skill, session.variables)
        session.add_message(RunMessage.create("system", system_prompt))

        await self._emit(
            RunEvent.create(session.id, EventType.MESSAGE_SYSTEM, {"content": system_prompt[:200]})
        )

        session.set_status(RunStatus.RUNNING)
        await self._emit(
            RunEvent.create(session.id, EventType.RUN_STARTED, {"skill_name": self._skill.name})
        )
        await self._emit_status_change(RunStatus.RUNNING)

        try:
            while session.current_step <= self._skill.step_count:
                step = self._skill.get_step(session.current_step)

                await self._emit(
                    RunEvent.create(
                        session.id,
                        EventType.STEP_STARTED,
                        {"step_index": step.index, "step_title": step.title},
                    )
                )

                # Handle pre-approval
                if step.requires_pre_approval:
                    decision = await self._request_approval(
                        step.index,
                        step.title,
                        "pre_step",
                        f"Step {step.index}: {step.title}\n\n{step.content}",
                    )
                    if decision == ApprovalDecision.REJECT:
                        raise ApprovalRejectedError(f"Pre-approval rejected for step {step.index}")
                    if decision == ApprovalDecision.SKIP:
                        session.skipped_steps.append(step.index)
                        await self._emit(
                            RunEvent.create(
                                session.id,
                                EventType.STEP_SKIPPED,
                                {"step_index": step.index, "reason": "pre-approval skipped"},
                            )
                        )
                        session.advance_step()
                        continue

                # Execute step via LLM loop
                await self._execute_step(step.index)

                # Handle post-approval
                if step.requires_post_approval:
                    decision = await self._request_approval(
                        step.index,
                        step.title,
                        "post_step",
                        f"Step {step.index} completed. Approval required before advancing.",
                    )
                    if decision == ApprovalDecision.REJECT:
                        raise ApprovalRejectedError(f"Post-approval rejected for step {step.index}")

                session.complete_current_step()
                await self._emit(
                    RunEvent.create(
                        session.id,
                        EventType.STEP_COMPLETED,
                        {"step_index": step.index, "step_title": step.title},
                    )
                )
                session.advance_step()

            session.set_status(RunStatus.COMPLETED)
            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.RUN_COMPLETED,
                    {
                        "completed_steps": len(session.completed_steps),
                        "total_steps": self._skill.step_count,
                    },
                )
            )
            await self._emit_status_change(RunStatus.COMPLETED)

        except ApprovalRejectedError:
            session.set_status(RunStatus.CANCELLED)
            await self._emit(
                RunEvent.create(
                    session.id, EventType.RUN_CANCELLED, {"reason": "approval_rejected"}
                )
            )
            await self._emit_status_change(RunStatus.CANCELLED)
        except Exception as e:
            logger.exception("Execution failed")
            session.pending_error = ErrorContext(
                error_type=type(e).__name__,
                message=str(e),
                step_index=session.current_step,
            )
            session.set_status(RunStatus.FAILED)
            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.RUN_FAILED,
                    {"error": str(e), "step_index": session.current_step},
                )
            )
            await self._emit_status_change(RunStatus.FAILED)

    async def _execute_step(self, step_index: int) -> None:
        """Execute a single step via the LLM loop."""
        step = self._skill.get_step(step_index)
        session = self._session

        step_prompt = build_step_prompt(step)
        session.add_message(RunMessage.create("user", step_prompt))

        text_only_count = 0
        iteration_count = 0

        while iteration_count < MAX_TOOL_CALL_ITERATIONS:
            iteration_count += 1

            # Build tools list: control tools + app tools
            all_tools = get_control_tool_schemas() + self._app_tool_schemas

            # Trim context and get LLM response
            trimmed = self._context.trim_messages(session.messages)
            formatted = self._llm.format_messages(trimmed)

            response = await self._llm.complete(formatted, tools=all_tools)

            # Handle reasoning
            if response.reasoning:
                await self._emit(
                    RunEvent.create(
                        session.id,
                        EventType.MESSAGE_REASONING,
                        {"content": response.reasoning},
                    )
                )

            # Handle text content
            if response.content:
                session.add_message(
                    RunMessage.create("assistant", response.content, tool_calls=response.tool_calls)
                )
                await self._emit(
                    RunEvent.create(
                        session.id,
                        EventType.MESSAGE_ASSISTANT,
                        {"content": response.content},
                    )
                )

            # No tool calls - just text
            if not response.tool_calls:
                text_only_count += 1
                if text_only_count >= MAX_TEXT_ONLY_ITERATIONS:
                    # Force step completion after too many text-only responses
                    session.add_message(
                        RunMessage.create(
                            "user",
                            "You seem to be stuck. Please call `complete_step` if the step "
                            "is done, or use a tool to make progress.",
                        )
                    )
                    text_only_count = 0
                continue

            text_only_count = 0

            # If there's content with tool calls, record the assistant message with tool calls
            if not response.content:
                session.add_message(
                    RunMessage.create("assistant", "", tool_calls=response.tool_calls)
                )

            # Process tool calls
            for tc in response.tool_calls:
                if is_control_tool(tc.name):
                    result = await self._handle_control_tool(tc)
                    if result == "step_complete":
                        return
                else:
                    await self._handle_app_tool(tc)

        raise ExecutionError(
            f"Step {step_index} exhausted {MAX_TOOL_CALL_ITERATIONS} iterations "
            "without calling complete_step"
        )

    async def _handle_control_tool(self, tool_call: ToolCall) -> str | None:
        """Handle a control tool call. Returns 'step_complete' if step is done."""
        session = self._session

        if tool_call.name == "complete_step":
            summary = tool_call.arguments.get("summary", "Step completed.")
            session.add_message(RunMessage.create("tool", summary, tool_call_id=tool_call.id))
            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.SUMMARY_GENERATED,
                    {"step_index": session.current_step, "summary": summary},
                )
            )
            return "step_complete"

        elif tool_call.name == "request_clarification":
            question = tool_call.arguments.get("question", "")
            options = tool_call.arguments.get("options", [])

            request = ClarificationRequest(question=question, options=options, context=None)

            session.pending_clarification = request
            session.set_status(RunStatus.AWAITING_INPUT)
            await self._emit_status_change(RunStatus.AWAITING_INPUT)

            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.CLARIFICATION_REQUESTED,
                    {"question": question, "options": options},
                )
            )

            answer = await self._human.request_clarification(request)

            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.CLARIFICATION_RESPONDED,
                    {"answer": answer},
                )
            )

            session.pending_clarification = None
            session.set_status(RunStatus.RUNNING)
            await self._emit_status_change(RunStatus.RUNNING)

            # Feed answer back as tool result
            session.add_message(RunMessage.create("tool", answer, tool_call_id=tool_call.id))

        return None

    async def _handle_app_tool(self, tool_call: ToolCall) -> None:
        """Handle an app (MCP) tool call."""
        session = self._session

        if self._tool_executor:
            result = await self._tool_executor.execute(tool_call, self._emit)
            content = result.get("content", "")
            session.add_message(
                RunMessage.create(
                    "tool",
                    content,
                    tool_call_id=tool_call.id,
                    app_name=result.get("tool_name"),
                )
            )
            session.step_tool_results.append(result)
        else:
            # No tool executor - return error
            error_msg = f"Tool '{tool_call.name}' is not available (no MCP apps configured)."
            session.add_message(RunMessage.create("tool", error_msg, tool_call_id=tool_call.id))
            await self._emit(
                RunEvent.create(
                    session.id,
                    EventType.TOOL_FAILED,
                    {
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "error": error_msg,
                    },
                )
            )

    async def _request_approval(
        self,
        step_index: int,
        step_title: str,
        approval_type: str,
        context: str,
    ) -> ApprovalDecision:
        """Request approval from the human interface."""
        session = self._session

        request = ApprovalRequest(
            step_index=step_index,
            step_title=step_title,
            approval_type=approval_type,  # type: ignore
            context=context,
            pending_tool_calls=list(session.pending_tool_calls),
            tool_results=list(session.step_tool_results),
        )

        session.pending_approval = request
        session.set_status(RunStatus.AWAITING_APPROVAL)
        await self._emit_status_change(RunStatus.AWAITING_APPROVAL)

        await self._emit(
            RunEvent.create(
                session.id,
                EventType.APPROVAL_REQUESTED,
                {
                    "step_index": step_index,
                    "step_title": step_title,
                    "approval_type": approval_type,
                },
            )
        )

        decision = await self._human.request_approval(request)

        await self._emit(
            RunEvent.create(
                session.id,
                EventType.APPROVAL_RESPONDED,
                {
                    "step_index": step_index,
                    "decision": decision.value,
                },
            )
        )

        session.approval_records.append(
            ApprovalRecord(
                step_index=step_index,
                approval_type=approval_type,  # type: ignore
                decision=decision,
                timestamp=datetime.now(UTC),
            )
        )

        session.pending_approval = None
        session.set_status(RunStatus.RUNNING)
        await self._emit_status_change(RunStatus.RUNNING)

        return decision

    async def _emit_status_change(self, status: RunStatus) -> None:
        await self._emit(
            RunEvent.create(
                self._session.id,
                EventType.STATUS_CHANGED,
                {"status": status.value},
            )
        )
