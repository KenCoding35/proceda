# ABOUTME: Minimal MCP stdio server that provides a get_time_remaining tool.
# ABOUTME: Returns time remaining in the current day, week, month, and year.

import json
import sys
from datetime import datetime, timedelta


def get_time_remaining() -> dict:
    now = datetime.now()

    # End of day
    end_of_day = now.replace(hour=23, minute=59, second=59)
    day_left = end_of_day - now

    # End of week (Sunday 23:59:59)
    days_until_sunday = 6 - now.weekday()
    if days_until_sunday < 0:
        days_until_sunday = 0
    end_of_week = (now + timedelta(days=days_until_sunday)).replace(hour=23, minute=59, second=59)
    week_left = end_of_week - now

    # End of month
    if now.month == 12:
        end_of_month = now.replace(year=now.year + 1, month=1, day=1) - timedelta(seconds=1)
    else:
        end_of_month = now.replace(month=now.month + 1, day=1) - timedelta(seconds=1)
    month_left = end_of_month - now

    # End of year
    end_of_year = now.replace(month=12, day=31, hour=23, minute=59, second=59)
    year_left = end_of_year - now

    def fmt(td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)

    return {
        "now": now.strftime("%Y-%m-%d %H:%M"),
        "day_remaining": fmt(day_left),
        "week_remaining": fmt(week_left),
        "month_remaining": fmt(month_left),
        "year_remaining": fmt(year_left),
    }


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "time-left", "version": "0.1.0"},
            },
        }

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_time_remaining",
                        "description": (
                            "Get time remaining in the current day, week, month, and year"
                        ),
                        "inputSchema": {"type": "object", "properties": {}},
                    }
                ]
            },
        }

    if method == "tools/call":
        name = request.get("params", {}).get("name", "")
        if name == "get_time_remaining":
            result = get_time_remaining()
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {name}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
