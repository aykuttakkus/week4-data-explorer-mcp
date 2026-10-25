"""Data Explorer MCP server for Week 4.

Wraps the REST Countries API (https://restcountries.com) and exposes it to an agent
as MCP tools over STDIO. The API key is read from REST_COUNTRIES_API_KEY.

Setup:
    pip install -r requirements.txt
Run (STDIO) — register this command in your MCP client (e.g. Claude Desktop / an IDE):
    python server.py
"""

import os
from pathlib import Path

import httpx
import pycountry
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(Path(__file__).with_name(".env"))

BASE_URL = "https://api.restcountries.com/countries/v5"
API_KEY_ENV = "REST_COUNTRIES_API_KEY"
REQUEST_TIMEOUT = 10
SEARCH_FIELDS = "names.common,capitals,region,population"
DETAIL_FIELDS = "names.common,currencies,languages,borders,flag.url_png"
mcp = FastMCP("data-explorer")


def _fetch_countries(
    query: str, *, limit: int, response_fields: str
) -> tuple[list[dict] | None, str | None]:
    """Fetch countries from REST Countries and normalize failures."""
    api_key = os.getenv(API_KEY_ENV, "").strip()
    if not api_key:
        return None, f"{API_KEY_ENV} is not configured"

    try:
        response = httpx.get(
            f"{BASE_URL}/name",
            params={
                "q": query,
                "limit": limit,
                "response_fields": response_fields,
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=REQUEST_TIMEOUT,
        )
    except httpx.TimeoutException:
        return None, "upstream request timed out"
    except httpx.RequestError:
        return None, "upstream request failed"

    if response.status_code == 404:
        return [], None

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None, f"upstream returned HTTP {response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return None, "upstream returned invalid JSON"

    if not isinstance(payload, dict):
        return None, "upstream returned an unexpected response"
    data = payload.get("data")
    if not isinstance(data, dict):
        return None, "upstream returned an unexpected response"
    countries = data.get("objects")
    if not isinstance(countries, list) or not all(
        isinstance(country, dict) for country in countries
    ):
        return None, "upstream returned an unexpected response"
    return countries, None


def _currency_list(raw_currencies: object) -> list[dict]:
    """Return a stable currency list for either v5-supported representation."""
    currencies = []
    if isinstance(raw_currencies, list):
        for currency in raw_currencies:
            if isinstance(currency, dict):
                currencies.append(
                    {
                        "code": currency.get("code"),
                        "name": currency.get("name"),
                        "symbol": currency.get("symbol"),
                    }
                )
    elif isinstance(raw_currencies, dict):
        for code, details in raw_currencies.items():
            if isinstance(details, dict):
                currencies.append(
                    {
                        "code": code,
                        "name": details.get("name"),
                        "symbol": details.get("symbol"),
                    }
                )
    return currencies


def _language_list(raw_languages: object) -> list[str]:
    """Return readable language names for supported API representations."""
    languages = []
    if isinstance(raw_languages, list):
        for language in raw_languages:
            if isinstance(language, dict) and isinstance(language.get("name"), str):
                languages.append(language["name"])
            elif isinstance(language, str):
                languages.append(language)
    elif isinstance(raw_languages, dict):
        languages.extend(
            language for language in raw_languages.values() if isinstance(language, str)
        )
    return languages


def _border_list(raw_borders: object) -> list[dict]:
    """Add readable ISO country names to alpha-3 border codes."""
    if not isinstance(raw_borders, list):
        return []

    borders = []
    for raw_code in raw_borders:
        if not isinstance(raw_code, str):
            continue
        code = raw_code.upper()
        country = pycountry.countries.get(alpha_3=code)
        country_name = None
        if country is not None:
            country_name = getattr(country, "common_name", country.name)
        borders.append({"code": code, "country_name": country_name})
    return borders


def _common_country_name(country: dict) -> str | None:
    """Read a common country name without assuming nested fields are present."""
    names = country.get("names")
    return names.get("common") if isinstance(names, dict) else None


def _first_capital(raw_capitals: object) -> str | None:
    """Return the first readable capital name from an upstream value."""
    if not isinstance(raw_capitals, list):
        return None
    for capital in raw_capitals:
        if isinstance(capital, dict) and isinstance(capital.get("name"), str):
            return capital["name"]
    return None


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict]:
    """Search countries by name. Returns a list of {name, capital, region, population}.

    This tool is a WORKED EXAMPLE — study how it validates input, calls the API,
    handles errors, and returns model-friendly data.
    """
    if not isinstance(query, str) or not query.strip():
        return [{"error": "query must not be empty"}]
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        return [{"error": "limit must be an integer between 1 and 100"}]

    countries, error = _fetch_countries(
        query.strip(), limit=limit, response_fields=SEARCH_FIELDS
    )
    if error:
        return [{"error": error}]

    results = []
    for country in countries or []:
        results.append(
            {
                "name": _common_country_name(country),
                "capital": _first_capital(country.get("capitals")),
                "region": country.get("region"),
                "population": country.get("population"),
            }
        )
    return results


@mcp.tool()
def get_country_details(name: str) -> dict:
    """Return currencies, languages, borders, and a flag URL for one country."""
    if not isinstance(name, str) or not name.strip():
        return {"error": "name must not be empty"}

    countries, error = _fetch_countries(
        name.strip(), limit=1, response_fields=DETAIL_FIELDS
    )
    if error:
        return {"error": error}
    if not countries:
        return {"error": "country not found"}

    country = countries[0]
    flag = country.get("flag")
    flag_url = flag.get("url_png") if isinstance(flag, dict) else None
    return {
        "country_name": _common_country_name(country),
        "currencies": _currency_list(country.get("currencies")),
        "languages": _language_list(country.get("languages")),
        "borders": _border_list(country.get("borders")),
        "flag_url": flag_url,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
