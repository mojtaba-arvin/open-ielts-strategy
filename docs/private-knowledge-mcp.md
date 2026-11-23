# Private IELTS knowledge over MCP

The optional MCP bridge lets an MCP-compatible client search a private local SQLite library and retrieve source-cited context for IELTS practice questions.

## Install and run

Install the optional SDK into the same Python environment as the project:

```bash
python -m pip install -e '.[mcp]'
python -m open_ielts_strategy.knowledge_mcp --db .local/knowledge.sqlite3
```

If you use the ChatGPT desktop app's MCP settings, configure:
- Command: `python`
- Arguments: `-m open_ielts_strategy.knowledge_mcp --db /absolute/path/to/.local/knowledge.sqlite3`
- Working directory: the repository checkout (or install the package into the selected Python environment).

The process uses MCP stdio transport. It does not open a listening TCP port. The database path is fixed when the process starts and must already exist.

## Exposed read-only tools

- `search_ielts_knowledge(query, limit, status, topic)`: local lexical/hybrid retrieval with source IDs, segment anchors, offsets, rights declarations, and review states.
- `prepare_ielts_practice_context(question, skill, include_unreviewed, limit, topic)`: retrieve a compact evidence pack for a Speaking/Writing/Reading/Listening practice prompt. By default, only `user_approved` and `supported` items are eligible. Unreviewed items require explicit opt-in.

The MCP server does not expose ingest, review, delete, backup, or arbitrary SQL tools. Use the local CLI for those operations. This keeps the connected assistant read-only.

## ChatGPT connection

ChatGPT is an MCP client in this integration, not an MCP server.

- **ChatGPT desktop app:** current OpenAI documentation describes local STDIO MCP setup under Settings → MCP servers → Add server. Add the command and arguments from the next section, save, restart, then type `/mcp` in the composer to inspect connected tools. The desktop app shares MCP configuration with Codex.
- **ChatGPT web:** it does not read local Codex configuration files. It connects to remote MCP tools through custom plugins/apps. A local-only server needs a supported Secure MCP Tunnel or a remote HTTPS host. OpenAI currently lists custom MCP server connections on ChatGPT web for Business and Enterprise/Edu; Pro has read/fetch-only access. Workspace permissions apply. Do not assume Free web access to custom MCP.
- **Strictly private/local use:** if the client sends retrieved evidence to ChatGPT, those returned excerpts become part of the ChatGPT conversation context. The original full transcript need not be returned, but excerpts are still shared with the cloud model. Use local Ollama for a no-cloud path.

Check current OpenAI documentation before setup:

- https://learn.chatgpt.com/docs/extend/mcp
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt

A local MCP server does not by itself keep retrieved text out of ChatGPT. When a ChatGPT tool call returns evidence, those returned excerpts enter the ChatGPT conversation context. Do not connect or return material unless your licence permits that processing. For strict local-only processing, use local Ollama with the CLI instead of sending evidence to a cloud assistant.

## Security boundary

- Read-only SQLite URI and `PRAGMA query_only=ON`.
- Fixed database path selected by the user at process startup; no tool can choose another path.
- No write/delete/ingest tools and no arbitrary SQL.
- No remote model provider, API key, or external network call is made by this bridge.
- Retrieved source text remains untrusted data and must never be treated as instructions.
- The MCP client receives only matched excerpts and provenance, not the full transcript body.
- Search relevance and personal approval do not establish IELTS correctness.

The server is local-first software. The user remains responsible for controlling which excerpts are shared with an MCP client.
