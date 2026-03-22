# ABOUTME: CLI `convert` command that transforms arbitrary SOP text into SKILL.md format.
# ABOUTME: Reads from file or stdin, calls LLM converter, writes validated output.

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console

from proceda.config import LLMConfig, ProcedaConfig
from proceda.exceptions import ConversionError
from proceda.skills.converter import convert_sop
from proceda.skills.parser import lint_skill

console = Console()


def convert(
    input_path: str = typer.Argument(
        ...,
        help="Path to SOP file, or '-' to read from stdin",
    ),
    output: str = typer.Option(
        "SKILL.md",
        "--output",
        "-o",
        help="Output file path",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Suggested skill name (kebab-case)",
    ),
    tools: str | None = typer.Option(
        None,
        "--tools",
        help="Path to JSON file with tool schemas (list of {name, description})",
    ),
    output_fields: str | None = typer.Option(
        None,
        "--output-fields",
        help="Comma-separated expected output field names (e.g., 'final_decision,score')",
    ),
    stdout: bool = typer.Option(
        False,
        "--stdout",
        help="Print to stdout instead of writing a file",
    ),
) -> None:
    """Convert an arbitrary SOP document into Proceda's SKILL.md format."""
    try:
        # Read input
        if input_path == "-":
            sop_text = sys.stdin.read()
        else:
            resolved = Path(input_path).resolve()
            if not resolved.is_file():
                console.print(f"[red]File not found: {resolved}[/red]")
                raise typer.Exit(code=2)
            sop_text = resolved.read_text(encoding="utf-8")

        if not sop_text.strip():
            console.print("[red]Input is empty[/red]")
            raise typer.Exit(code=2)

        # Load LLM config
        try:
            config = ProcedaConfig.load()
            llm_config = config.llm
        except Exception:
            llm_config = LLMConfig()

        # Derive name hint from filename if not provided
        effective_name = name
        if not effective_name and input_path != "-":
            stem = Path(input_path).stem.lower()
            if stem not in ("sop", "procedure", "process", "document", "doc"):
                effective_name = stem.replace("_", "-").replace(" ", "-")

        # Load tool context if provided
        tool_context = None
        if tools:
            import json as _json

            tools_path = Path(tools).resolve()
            if not tools_path.is_file():
                console.print(f"[red]Tools file not found: {tools_path}[/red]")
                raise typer.Exit(code=2)
            raw_tools = _json.loads(tools_path.read_text(encoding="utf-8"))
            # Support Bedrock format (with toolSpec wrapper) or plain list
            tool_context = []
            for spec in raw_tools:
                if "toolSpec" in spec:
                    ts = spec["toolSpec"]
                    input_schema = ts.get("inputSchema", {})
                    if "json" in input_schema:
                        input_schema = input_schema["json"]
                    tool_context.append(
                        {
                            "name": ts["name"],
                            "description": ts.get("description", ""),
                            "parameters": input_schema,
                        }
                    )
                else:
                    tool_context.append(
                        {
                            "name": spec["name"],
                            "description": spec.get("description", ""),
                            "parameters": spec.get("parameters", spec.get("inputSchema", {})),
                        }
                    )

        # Parse output fields
        parsed_output_fields = None
        if output_fields:
            parsed_output_fields = [f.strip() for f in output_fields.split(",") if f.strip()]

        # Convert
        console.print("[dim]Converting SOP to SKILL.md...[/dim]")
        result = asyncio.run(
            convert_sop(
                sop_text,
                llm_config,
                name_hint=effective_name,
                tool_context=tool_context,
                output_fields=parsed_output_fields,
            )
        )

        # Lint the result
        lint_result = lint_skill(result)
        for issue in lint_result.warnings:
            console.print(f"[yellow]WARNING:[/yellow] {issue.message}")

        if stdout:
            sys.stdout.write(result)
            if not result.endswith("\n"):
                sys.stdout.write("\n")
        else:
            out_path = Path(output)
            out_path.write_text(result, encoding="utf-8")
            console.print(f"[green]Wrote {out_path}[/green]")

        # Summary
        if lint_result.skill:
            skill = lint_result.skill
            console.print(f"  Name: {skill.name}")
            console.print(f"  Steps: {skill.step_count}")
            titles = skill.step_titles()
            for i, title in enumerate(titles, 1):
                console.print(f"    {i}. {title}")

    except ConversionError as e:
        console.print(f"[red]Conversion failed: {e}[/red]")
        raise typer.Exit(code=1)
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=2)
