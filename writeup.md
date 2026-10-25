# Week 4 Write-up — Data Explorer MCP Server

## MCP client used

I registered the server as `data-explorer` in Codex Desktop using STDIO transport and
absolute paths to the project's virtual-environment Python interpreter and `server.py`.
After restarting Codex, the client discovered both tools. The calls below were made from
the Codex conversation on 2026-10-25; the REST Countries API key remained only in the
local, ignored `.env` file.

## Real tool-call transcript

### 1. Search for a country

**Agent request**

> Search for Germany and return at most two matching countries.

**Tool call**

```text
search_countries({"query": "Germany", "limit": 2})
```

**Tool result**

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

### 2. Get country details

**Agent request**

> Get the currencies, languages, borders, and flag URL for Türkiye.

**Tool call**

```text
get_country_details({"name": "Türkiye"})
```

**Tool result**

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
  "languages": [
    "Turkish"
  ],
  "borders": [
    {
      "code": "ARM",
      "country_name": "Armenia"
    },
    {
      "code": "AZE",
      "country_name": "Azerbaijan"
    },
    {
      "code": "BGR",
      "country_name": "Bulgaria"
    },
    {
      "code": "GEO",
      "country_name": "Georgia"
    },
    {
      "code": "GRC",
      "country_name": "Greece"
    },
    {
      "code": "IRN",
      "country_name": "Iran"
    },
    {
      "code": "IRQ",
      "country_name": "Iraq"
    },
    {
      "code": "SYR",
      "country_name": "Syria"
    }
  ],
  "flag_url": "https://flags.restcountries.com/v5/w640/tr.png"
}
```

### 3. Controlled bad-input check

**Agent request**

> Call the search tool with a blank query.

**Tool call**

```text
search_countries({"query": "   ", "limit": 5})
```

**Tool result**

```json
[
  {
    "error": "query must not be empty"
  }
]
```

The bad input returned structured data and did not terminate the MCP server.

## Error-handling approach

Both public tools validate their inputs before making a network request. Blank names and
queries return a clear error, while `search_countries` also restricts `limit` to an integer
between 1 and 100. The shared request helper checks for the API key, distinguishes timeouts,
connection failures, and HTTP failures, and safely rejects invalid JSON or an unexpected
response shape. A search with no matches returns `[]`, while a missing country detail returns
`{"error": "country not found"}`; neither case crashes the server or leaks the API key.

The test suite covers successful calls and each failure category with mocked HTTP responses.
This makes the behavior repeatable without network access or API quota usage. The final run
completed with 21 passing tests, a clean Ruff lint check, and a clean Ruff format check.

## What I learned

Yapay zekâ gereksiz yere token harcamamış oluyor. Ayrıca gereksiz veya yanlış bilgilere
bakıp yanlış anlamasını önlüyoruz. Bu da kodda loglama gibi; ne hatası çıktığını anlıyoruz,
nerede ve neden olduğunu kontrol edebiliyoruz. API’yi herkesin erişimine açarsak bu ciddi
güvenlik sıkıntılarına yol açabilir.
