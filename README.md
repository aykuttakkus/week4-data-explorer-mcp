# Data Explorer MCP Server

A local Model Context Protocol (MCP) server that gives an AI client two controlled
tools for exploring country data:

- `search_countries` searches by country name.
- `get_country_details` returns currencies, languages, land borders, and a flag URL.

The server uses STDIO transport and the REST Countries API. It does not expose an HTTP
server and does not require remote hosting.

## Requirements

- Python 3.10 or newer
- A REST Countries API key from <https://restcountries.com/>
- An MCP client such as Codex, Claude Desktop, or an MCP-aware IDE

The assignment starter originally used the unauthenticated REST Countries v3.1 API.
That API has been retired, so this implementation uses the current authenticated v5
API while preserving the assignment's small, model-friendly return shapes. See the
[official migration notice](https://restcountries.com/docs/countries/legacy-api-deprecation).

## Install

Run these commands from this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a local environment file:

```bash
cp .env.example .env
```

Open `.env` and add the private key after the equals sign:

```dotenv
REST_COUNTRIES_API_KEY=your_private_key_here
```

The repository's `.gitignore` excludes `.env`. Never place the real key in source code,
screenshots, transcripts, commits, or GitHub.

## Run over STDIO

```bash
.venv/bin/python server.py
```

The process waits for MCP JSON-RPC messages on standard input. A quiet terminal is
normal. Do not add `print()` calls to the server because ordinary standard output would
corrupt the STDIO protocol.

## Register in Codex

Use absolute paths so the client can launch the correct interpreter from any directory:

```bash
codex mcp add data-explorer -- \
  /absolute/path/to/starter/.venv/bin/python \
  /absolute/path/to/starter/server.py
```

Verify the registration:

```bash
codex mcp get data-explorer
```

Restart Codex after registering the server. The server reads the key from the `.env`
file beside `server.py`, so the key does not need to be copied into the MCP registration.

## Register in Claude Desktop

Add a STDIO entry to the client's MCP configuration, replacing both paths:

```json
{
  "mcpServers": {
    "data-explorer": {
      "command": "/absolute/path/to/starter/.venv/bin/python",
      "args": ["/absolute/path/to/starter/server.py"]
    }
  }
}
```

Restart the client after saving the configuration.

## Tool reference

### `search_countries`

Searches country names and returns a list containing only the fields useful to an
agent.

| Parameter | Type | Required | Default | Meaning |
| --- | --- | --- | --- | --- |
| `query` | string | yes | — | Country name or partial name to search |
| `limit` | integer | no | `5` | Maximum number of results, from 1 to 100 |

Example input:

```json
{
  "query": "Germany",
  "limit": 2
}
```

Example output:

```json
[
  {
    "name": "Germany",
    "capital": "Berlin",
    "region": "Europe",
    "population": 83298787
  }
]
```

No match is represented by an empty list:

```json
[]
```

### `get_country_details`

Returns one country's currencies, languages, land borders, and PNG flag URL. Border
codes are enriched with readable ISO country names locally.

| Parameter | Type | Required | Meaning |
| --- | --- | --- | --- |
| `name` | string | yes | Country name to look up |

Example input:

```json
{
  "name": "Türkiye"
}
```

Example output:

```json
{
  "country_name": "Turkey",
  "currencies": [
    {
      "code": "TRY",
      "name": "Turkish lira",
      "symbol": "₺"
    }
  ],
  "languages": ["Turkish"],
  "borders": [
    {
      "code": "ARM",
      "country_name": "Armenia"
    },
    {
      "code": "BGR",
      "country_name": "Bulgaria"
    }
  ],
  "flag_url": "https://flags.restcountries.com/v5/w640/tr.png"
}
```

## Error behavior

Expected failures are returned as data instead of crashing the MCP process. Examples:

```json
[{"error": "query must not be empty"}]
```

```json
{"error": "country not found"}
```

The tools also handle an invalid limit, a missing API key, timeouts, connection errors,
HTTP failures, malformed JSON, and unexpected upstream response shapes. Error messages
never include the API key.

## Quality checks

```bash
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
.venv/bin/python -m pytest -q
```

The tests mock the external API, so they do not consume quota and do not require a real
key or network connection.

## Files

- `server.py` — STDIO MCP server and both tools
- `test_server.py` — success and failure-path tests
- `.gitignore` — prevents secrets, virtual environments, and caches from being committed
- `.env.example` — safe local configuration template
- `requirements.txt` — runtime and quality-check dependencies
- `writeup.md` — real MCP client transcript, error strategy, and reflection
