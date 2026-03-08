# Configuration Reference

Proceda is configured via `proceda.yaml`. The file is searched in order:

1. `./proceda.yaml` (or `proceda.yml`)
2. `~/.config/proceda/proceda.yaml`

If no config file is found, defaults are used.

## Environment variable expansion

All string values support `${VAR}` and `${VAR:-default}` syntax:

```yaml
apps:
  - name: my-app
    env:
      API_KEY: ${MY_API_KEY}
      REGION: ${AWS_REGION:-us-east-1}
```

## Full reference

```yaml
llm:
  model: anthropic/claude-sonnet-4-20250514  # Any LiteLLM-supported model
  api_key_env: ANTHROPIC_API_KEY             # Env var containing the API key
  temperature: 0.7
  max_tokens: 4096
  max_retries: 3                             # Retry count for transient LLM errors

apps:                                        # MCP tool servers
  - name: my-tools                           # Used as tool name prefix (my-tools__tool_name)
    description: What this server provides
    transport: stdio                         # "stdio" or "http"
    command: ["path/to/server"]              # For stdio: command + args to launch
    # url: http://localhost:8080             # For http: server URL
    env:                                     # Environment variables for the server process
      API_KEY: ${MY_API_KEY}

dev:
  show_reasoning: true                       # Show LLM reasoning in dev/TUI mode
  log_mcp: true                              # Log MCP tool calls

security:
  tool_denylist:                             # Tools the agent is never allowed to call
    - dangerous_tool

logging:
  run_dir: .proceda/runs                     # Where run event logs are stored
  redact_secrets: true                       # Redact API keys in event logs
```

## Sections

### `llm`

Controls the LLM provider. Proceda uses [LiteLLM](https://docs.litellm.ai/) under the hood, so any LiteLLM model string works (e.g., `openai/gpt-4o`, `anthropic/claude-sonnet-4-20250514`, `ollama_chat/llama3`).

### `apps`

Each entry defines an MCP tool server. The `name` becomes the tool prefix — a server named `fs` exposing a tool `read_file` creates the tool `fs__read_file`.

**Stdio transport** launches the server as a subprocess. The `command` array is the argv.

**HTTP transport** connects to a running server at the given `url`.

### `security`

The `tool_denylist` blocks specific tools from being called, regardless of what the LLM requests. Useful for preventing destructive operations.

### `logging`

Run logs are JSONL event streams stored in `run_dir`. Each run gets a timestamped subdirectory. Use `proceda replay` to inspect them.
