# ABOUTME: Generates an HTML report from SOP-Bench evaluation results and traces.
# ABOUTME: Presents per-task traces with tool calls, results, and field comparisons.
# ruff: noqa: E501

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def load_results(domain: str) -> dict:
    results_path = RESULTS_DIR / f"{domain}_results.json"
    with open(results_path) as f:
        return json.load(f)


def load_trace(domain: str, task_id: str, status: str) -> list[dict]:
    """Load trace events for a task, trying status-specific file first."""
    traces_dir = RESULTS_DIR / "traces"
    path = traces_dir / f"{domain}_{task_id}_{status}.jsonl"
    if not path.exists():
        # Fall back to other status
        alt = "fail" if status == "success" else "success"
        path = traces_dir / f"{domain}_{task_id}_{alt}.jsonl"
    if not path.exists():
        return []
    events = []
    with open(path) as f:
        for line in f:
            events.append(json.loads(line))
    return events


def esc(s: str) -> str:
    return html.escape(str(s))


def render_tool_event(event: dict) -> str:
    t = event.get("type", "")
    payload = event.get("payload", {})
    tool_name = payload.get("tool_name", "")

    if t == "tool.called":
        args = payload.get("arguments", {})
        args_html = esc(json.dumps(args, indent=2))
        return (
            f'<div class="tool-call">'
            f'<span class="tool-label call">CALL</span> '
            f'<span class="tool-name">{esc(tool_name)}</span>'
            f'<pre class="tool-args">{args_html}</pre>'
            f"</div>"
        )
    elif t == "tool.completed":
        result = payload.get("result", "")
        try:
            result_formatted = esc(json.dumps(json.loads(result), indent=2))
        except (json.JSONDecodeError, TypeError):
            result_formatted = esc(str(result))
        return (
            f'<div class="tool-result">'
            f'<span class="tool-label success">RESULT</span> '
            f'<span class="tool-name">{esc(tool_name)}</span>'
            f'<pre class="tool-output">{result_formatted}</pre>'
            f"</div>"
        )
    elif t == "tool.failed":
        error = payload.get("error", "")
        return (
            f'<div class="tool-error">'
            f'<span class="tool-label error">ERROR</span> '
            f'<span class="tool-name">{esc(tool_name)}</span>'
            f'<pre class="tool-output">{esc(error)}</pre>'
            f"</div>"
        )
    return ""


def render_field_comparison(predicted: dict, expected: dict) -> str:
    rows = []
    all_keys = list(expected.keys())
    for key in all_keys:
        exp_val = expected.get(key, "")
        pred_val = predicted.get(key)
        if pred_val is None:
            match_class = "missing"
            pred_display = "&mdash;"
            icon = "&#x2718;"
        elif str(pred_val).lower().strip() == str(exp_val).lower().strip():
            match_class = "match"
            pred_display = esc(str(pred_val))
            icon = "&#x2714;"
        else:
            match_class = "mismatch"
            pred_display = esc(str(pred_val))
            icon = "&#x2718;"
        rows.append(
            f'<tr class="{match_class}">'
            f'<td class="field-icon">{icon}</td>'
            f'<td class="field-name">{esc(key)}</td>'
            f"<td>{esc(str(exp_val))}</td>"
            f"<td>{pred_display}</td>"
            f"</tr>"
        )
    return (
        '<table class="field-table">'
        "<thead><tr><th></th><th>Field</th><th>Expected</th><th>Predicted</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_task(task: dict, domain: str) -> str:
    task_id = task["task_id"]
    is_correct = task["is_correct"]
    success = task["success"]
    exec_time = task["execution_time"]

    status_class = "pass" if is_correct else ("error" if not success else "fail")
    status_label = "PASS" if is_correct else ("ERROR" if not success else "FAIL")
    trace_status = "success" if is_correct else ("error" if not success else "fail")

    # Load trace
    events = load_trace(domain, task_id, trace_status)

    predicted = task.get("predicted", {})
    expected = task.get("expected", {})

    # Build trace timeline
    tool_events = []
    current_step = None
    steps_html = []

    for event in events:
        if "_meta" in event:
            continue
        t = event.get("type", "")
        payload = event.get("payload", {})

        if t == "step.started":
            current_step = payload.get("step_title", f"Step {payload.get('step_index', '?')}")
            tool_events = []
        elif t in ("tool.called", "tool.completed", "tool.failed"):
            tool_events.append(event)
        elif t == "step.completed":
            tools_html = "".join(render_tool_event(e) for e in tool_events)
            if not tools_html:
                tools_html = '<div class="no-tools">No tool calls in this step</div>'
            steps_html.append(
                f'<div class="step">'
                f'<div class="step-title">{esc(current_step or "Unknown")}</div>'
                f"{tools_html}"
                f"</div>"
            )
            tool_events = []

    steps_content = (
        "".join(steps_html) if steps_html else '<div class="no-steps">No step data</div>'
    )
    fields_html = render_field_comparison(predicted, expected)

    return f"""
    <div class="task {status_class}">
        <div class="task-header" onclick="this.parentElement.classList.toggle('expanded')">
            <span class="status-badge {status_class}">{status_label}</span>
            <span class="task-id">{esc(task_id)}</span>
            <span class="exec-time">{exec_time:.1f}s</span>
            <span class="expand-icon">&#x25B6;</span>
        </div>
        <div class="task-body">
            <h4>Output Comparison</h4>
            {fields_html}
            <h4>Execution Trace</h4>
            {steps_content}
            {
        f'<div class="task-error-msg">Error: {esc(task["error"])}</div>'
        if task.get("error")
        else ""
    }
        </div>
    </div>
    """


def generate_report(domain: str) -> str:
    data = load_results(domain)
    metrics = data["metrics"]
    tasks = data["tasks"]

    num_pass = sum(1 for t in tasks if t["is_correct"])
    num_fail = sum(1 for t in tasks if t["success"] and not t["is_correct"])
    num_error = sum(1 for t in tasks if not t["success"])
    avg_time = sum(t["execution_time"] for t in tasks) / len(tasks) if tasks else 0

    # Sort: failures first, then successes
    tasks_sorted = sorted(tasks, key=lambda t: (t["is_correct"], t["task_id"]))

    tasks_html = "".join(render_task(t, domain) for t in tasks_sorted)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SOP-Bench Report: {esc(domain)}</title>
<style>
:root {{
    --bg: #0d1117;
    --surface: #161b22;
    --surface2: #21262d;
    --border: #30363d;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --green: #3fb950;
    --green-bg: #0d2818;
    --red: #f85149;
    --red-bg: #2d1214;
    --yellow: #d29922;
    --yellow-bg: #2e2312;
    --blue: #58a6ff;
    --purple: #bc8cff;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 2rem;
    max-width: 1100px;
    margin: 0 auto;
}}
h1 {{ font-size: 1.8rem; margin-bottom: 0.5rem; }}
h2 {{ font-size: 1.3rem; color: var(--text-muted); margin-bottom: 1.5rem; font-weight: 400; }}
h4 {{ font-size: 0.9rem; color: var(--text-muted); margin: 1rem 0 0.5rem; text-transform: uppercase; letter-spacing: 0.05em; }}

/* Metrics cards */
.metrics {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}}
.metric-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.2rem;
    text-align: center;
}}
.metric-value {{
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
}}
.metric-value.highlight {{ color: var(--green); }}
.metric-label {{
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-top: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* Summary bar */
.summary-bar {{
    display: flex;
    height: 8px;
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 2rem;
    background: var(--surface2);
}}
.summary-bar .pass {{ background: var(--green); }}
.summary-bar .fail {{ background: var(--red); }}
.summary-bar .error {{ background: var(--yellow); }}

/* Filter buttons */
.filters {{
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}}
.filter-btn {{
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 0.4rem 1rem;
    border-radius: 20px;
    cursor: pointer;
    font-size: 0.85rem;
    transition: all 0.15s;
}}
.filter-btn:hover {{ border-color: var(--blue); }}
.filter-btn.active {{ background: var(--blue); border-color: var(--blue); color: #fff; }}
.filter-btn .count {{ color: var(--text-muted); margin-left: 0.3rem; }}
.filter-btn.active .count {{ color: rgba(255,255,255,0.7); }}

/* Task cards */
.task {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 0.5rem;
    overflow: hidden;
    transition: border-color 0.15s;
}}
.task:hover {{ border-color: var(--text-muted); }}
.task.pass {{ border-left: 3px solid var(--green); }}
.task.fail {{ border-left: 3px solid var(--red); }}
.task.error {{ border-left: 3px solid var(--yellow); }}

.task-header {{
    display: flex;
    align-items: center;
    padding: 0.7rem 1rem;
    cursor: pointer;
    user-select: none;
    gap: 0.8rem;
}}
.task-header:hover {{ background: var(--surface2); }}
.task-id {{ font-family: 'SF Mono', Monaco, monospace; font-size: 0.9rem; font-weight: 600; }}
.exec-time {{ color: var(--text-muted); font-size: 0.8rem; margin-left: auto; }}
.expand-icon {{
    color: var(--text-muted);
    font-size: 0.7rem;
    transition: transform 0.2s;
}}
.task.expanded .expand-icon {{ transform: rotate(90deg); }}

.status-badge {{
    font-size: 0.7rem;
    font-weight: 700;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}
.status-badge.pass {{ background: var(--green-bg); color: var(--green); }}
.status-badge.fail {{ background: var(--red-bg); color: var(--red); }}
.status-badge.error {{ background: var(--yellow-bg); color: var(--yellow); }}

.task-body {{
    display: none;
    padding: 0 1rem 1rem;
    border-top: 1px solid var(--border);
}}
.task.expanded .task-body {{ display: block; }}

/* Field comparison table */
.field-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}}
.field-table th {{
    text-align: left;
    padding: 0.4rem 0.6rem;
    color: var(--text-muted);
    font-weight: 600;
    font-size: 0.75rem;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
}}
.field-table td {{
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid var(--border);
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.82rem;
}}
.field-table tr.match td {{ color: var(--text); }}
.field-table tr.mismatch td {{ color: var(--red); }}
.field-table tr.missing td {{ color: var(--yellow); }}
.field-icon {{ width: 1.5rem; text-align: center; }}
.field-name {{ color: var(--text-muted) !important; }}

/* Steps and tool calls */
.step {{
    margin-bottom: 0.8rem;
    background: var(--bg);
    border-radius: 6px;
    padding: 0.8rem;
    border: 1px solid var(--border);
}}
.step-title {{
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
    color: var(--blue);
}}
.tool-call, .tool-result, .tool-error {{
    margin: 0.4rem 0;
    padding: 0.3rem 0;
}}
.tool-label {{
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-right: 0.4rem;
}}
.tool-label.call {{ background: #1f2937; color: var(--blue); }}
.tool-label.success {{ background: var(--green-bg); color: var(--green); }}
.tool-label.error {{ background: var(--red-bg); color: var(--red); }}
.tool-name {{ font-family: 'SF Mono', Monaco, monospace; font-size: 0.85rem; color: var(--purple); }}
.tool-args, .tool-output {{
    font-family: 'SF Mono', Monaco, monospace;
    font-size: 0.78rem;
    background: var(--surface2);
    padding: 0.5rem 0.7rem;
    border-radius: 4px;
    margin-top: 0.3rem;
    overflow-x: auto;
    white-space: pre-wrap;
    color: var(--text-muted);
    line-height: 1.5;
}}
.no-tools {{
    color: var(--yellow);
    font-size: 0.82rem;
    font-style: italic;
    padding: 0.3rem 0;
}}
.task-error-msg {{
    background: var(--red-bg);
    color: var(--red);
    padding: 0.6rem 0.8rem;
    border-radius: 4px;
    font-size: 0.82rem;
    margin-top: 0.5rem;
    font-family: 'SF Mono', Monaco, monospace;
}}

/* Footer */
.footer {{
    text-align: center;
    color: var(--text-muted);
    font-size: 0.8rem;
    margin-top: 3rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
}}
</style>
</head>
<body>

<h1>SOP-Bench: {esc(domain.replace("_", " ").title())}</h1>
<h2>Proceda Benchmark Run &middot; {esc(metrics.get("timestamp", "")[:10])}</h2>

<div class="metrics">
    <div class="metric-card">
        <div class="metric-value highlight">{metrics["tsr"]:.1%}</div>
        <div class="metric-label">Task Success Rate</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{num_pass}</div>
        <div class="metric-label">Passed</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{num_fail + num_error}</div>
        <div class="metric-label">Failed</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{metrics["ecr"]:.0%}</div>
        <div class="metric-label">Completion Rate</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{avg_time:.0f}s</div>
        <div class="metric-label">Avg Time</div>
    </div>
    <div class="metric-card">
        <div class="metric-value">{metrics["num_tasks"]}</div>
        <div class="metric-label">Total Tasks</div>
    </div>
</div>

<div class="summary-bar">
    <div class="pass" style="width:{num_pass / len(tasks) * 100:.1f}%"></div>
    <div class="fail" style="width:{num_fail / len(tasks) * 100:.1f}%"></div>
    <div class="error" style="width:{num_error / len(tasks) * 100:.1f}%"></div>
</div>

<div class="filters">
    <button class="filter-btn active" onclick="filterTasks('all')">All<span class="count">({len(tasks)})</span></button>
    <button class="filter-btn" onclick="filterTasks('pass')">Pass<span class="count">({num_pass})</span></button>
    <button class="filter-btn" onclick="filterTasks('fail')">Fail<span class="count">({num_fail})</span></button>
    {"" if num_error == 0 else f'<button class="filter-btn" onclick="filterTasks(\'error\')">Error<span class="count">({num_error})</span></button>'}
</div>

<div id="tasks-container">
{tasks_html}
</div>

<div class="footer">
    Generated by Proceda SOP-Bench Harness &middot; Model: Gemini 2.5 Flash &middot;
    Baseline TSR: 0% (FC &amp; ReAct)
</div>

<script>
function filterTasks(type) {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    event.target.closest('.filter-btn').classList.add('active');
    document.querySelectorAll('.task').forEach(t => {{
        if (type === 'all') {{ t.style.display = ''; return; }}
        t.style.display = t.classList.contains(type) ? '' : 'none';
    }});
}}
</script>
</body>
</html>"""


def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "patient_intake"
    report_html = generate_report(domain)
    output_path = RESULTS_DIR / f"{domain}_report.html"
    with open(output_path, "w") as f:
        f.write(report_html)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
