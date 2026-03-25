#!/bin/bash
# ABOUTME: Batch runner for rate-limited Gemini 3.1 Pro benchmark runs.
# ABOUTME: Uses --resume to continue from where the last batch left off.

set -e

DOMAIN="${1:-referral_abuse_detection_v2}"
MAX_TASKS="${2:-200}"

export GEMINI_API_KEY=$(pass soprun/GEMINI_API_KEY)

echo "=== SOP-Bench batch run: ${DOMAIN} ==="
echo "Max tasks: ${MAX_TASKS}"
echo "Model: gemini/gemini-3.1-pro-preview"
echo "Time: $(date)"
echo ""

# Check if quota is available with a quick test
echo "Checking API quota..."
QUOTA_CHECK=$(uv run python -c "
import litellm, asyncio
async def test():
    try:
        r = await litellm.acompletion(model='gemini/gemini-3.1-pro-preview', messages=[{'role':'user','content':'Say ok'}], max_tokens=5)
        print('OK')
    except Exception as e:
        if '429' in str(e):
            import re
            m = re.search(r'retryDelay.*?\"(\d+)s\"', str(e))
            if m:
                print(f'RATE_LIMITED:{m.group(1)}')
            else:
                print('RATE_LIMITED:unknown')
        else:
            print(f'ERROR:{str(e)[:100]}')
asyncio.run(test())
" 2>/dev/null)

if [[ "$QUOTA_CHECK" == RATE_LIMITED* ]]; then
    DELAY=$(echo "$QUOTA_CHECK" | cut -d: -f2)
    if [[ "$DELAY" != "unknown" ]]; then
        MINS=$((DELAY / 60))
        echo "Rate limited. Quota resets in ${MINS} minutes. Try again later."
    else
        echo "Rate limited. Quota reset time unknown. Try again later."
    fi
    exit 1
elif [[ "$QUOTA_CHECK" == ERROR* ]]; then
    echo "API error: $QUOTA_CHECK"
    exit 1
fi

echo "Quota available. Starting run..."
echo ""

uv run python -m benchmarks.sop_bench.harness \
    --domain "$DOMAIN" \
    --max-tasks "$MAX_TASKS" \
    --resume

echo ""
echo "Batch complete at $(date)"
echo "Run again tomorrow to continue (uses --resume to skip completed tasks)"
