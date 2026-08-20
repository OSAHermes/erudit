# QwenPaw Integration Notes

## Key Finding: QwenPaw is MCP Client, Not Server

**Critical**: QwenPaw cannot be connected TO via MCP. It connects TO external MCP servers.

### Connection Methods

1. **ACP Protocol** (Recommended)
   ```bash
   qwenpaw acp
   ```
   - Stdio JSON-RPC protocol
   - External clients connect to QwenPaw
   - Methods: initialize, new_session, prompt, cancel

2. **HTTP API**
   ```bash
   qwenpaw app --port 8088
   ```
   - Web UI: http://localhost:8088
   - API: http://localhost:8088/api/agents
   - MCP config via Web UI

3. **MCP Configuration** (QwenPaw as client)
   - Configure in Web UI: Agent → MCP
   - QwenPaw connects to external MCP servers

## Installation

```bash
# Using uv (recommended)
uv venv /opt/data/qwenpaw-venv
source /opt/data/qwenpaw-venv/bin/activate
uv pip install qwenpaw
qwenpaw init --defaults
qwenpaw app --port 8088
```

## Common Issues

### Issue: "No module named qwenpaw"
- Check which Python is being used
- QwenPaw venv: `/opt/data/qwenpaw-venv/bin/python3`
- System Python: `/usr/bin/python3`

### Issue: Port 8088 already in use
- QwenPaw may already be running
- Check: `ps aux | grep qwenpaw`
- Use different port or kill existing process

## ACP Methods Reference

| Method | Description |
|--------|-------------|
| `initialize` | Handshake, return capabilities |
| `new_session` | Create new conversation |
| `load_session` | Load existing session by ID |
| `prompt` | Send message, stream response |
| `cancel` | Cancel in-progress prompt |
| `close_session` | Close and clean up session |

## QwenPaw Built-in Tools

- File operations: read_file, write_file, edit_file
- Search: grep_search, glob_search
- Shell: execute_shell_command
- Browser: browser automation
- Memory: memory_search
- Tools: delegate_external_agent

## Related

- GitHub: https://github.com/EKKOLearnAI/qwenpaw
- Docs: https://qwenpaw-docs
