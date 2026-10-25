"""Behavioral tests for the Data Explorer MCP tools."""

from unittest.mock import Mock

import httpx
import pytest

import server


def _response(status_code: int, payload: dict) -> httpx.Response:
    request = httpx.Request("GET", f"{server.BASE_URL}/name")
    return httpx.Response(status_code, request=request, json=payload)


def _invalid_json_response() -> httpx.Response:
    request = httpx.Request("GET", f"{server.BASE_URL}/name")
    return httpx.Response(200, request=request, content=b"not-json")


@pytest.mark.parametrize("query", [None, "", "   "])
def test_search_countries_rejects_blank_query(monkeypatch, query):
    get = Mock()
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.search_countries("   ") == [{"error": "query must not be empty"}]
    get.assert_not_called()


@pytest.mark.parametrize("limit", [True, 0, 101, 1.5, "2"])
def test_search_countries_rejects_invalid_limit(monkeypatch, limit):
    get = Mock()
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.search_countries("Germany", limit) == [
        {"error": "limit must be an integer between 1 and 100"}
    ]
    get.assert_not_called()


def test_search_countries_requires_api_key(monkeypatch):
    monkeypatch.delenv(server.API_KEY_ENV, raising=False)
    get = Mock()
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.search_countries("Germany") == [
        {"error": "REST_COUNTRIES_API_KEY is not configured"}
    ]
    get.assert_not_called()


def test_search_countries_maps_v5_response(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    response = _response(
        200,
        {
            "data": {
                "objects": [
                    {
                        "names": {"common": "Germany"},
                        "capitals": [{"name": "Berlin", "primary": True}],
                        "region": "Europe",
                        "population": 83_500_000,
                    }
                ]
            }
        },
    )
    get = Mock(return_value=response)
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.search_countries(" Germany ", limit=2) == [
        {
            "name": "Germany",
            "capital": "Berlin",
            "region": "Europe",
            "population": 83_500_000,
        }
    ]
    get.assert_called_once_with(
        f"{server.BASE_URL}/name",
        params={
            "q": "Germany",
            "limit": 2,
            "response_fields": server.SEARCH_FIELDS,
        },
        headers={"Authorization": "Bearer test-key"},
        timeout=server.REQUEST_TIMEOUT,
    )


def test_search_countries_returns_empty_list_when_no_country_matches(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx,
        "get",
        Mock(return_value=_response(200, {"data": {"objects": []}})),
    )

    assert server.search_countries("not-a-country") == []


@pytest.mark.parametrize(
    ("side_effect", "message"),
    [
        (httpx.TimeoutException("too slow"), "upstream request timed out"),
        (httpx.RequestError("offline"), "upstream request failed"),
    ],
)
def test_search_countries_handles_network_errors(monkeypatch, side_effect, message):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(server.httpx, "get", Mock(side_effect=side_effect))

    assert server.search_countries("Germany") == [{"error": message}]


def test_search_countries_handles_http_error(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx, "get", Mock(return_value=_response(503, {"errors": []}))
    )

    assert server.search_countries("Germany") == [
        {"error": "upstream returned HTTP 503"}
    ]


def test_search_countries_handles_invalid_json(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx, "get", Mock(return_value=_invalid_json_response())
    )

    assert server.search_countries("Germany") == [
        {"error": "upstream returned invalid JSON"}
    ]


@pytest.mark.parametrize("name", [None, "", "   "])
def test_get_country_details_rejects_blank_name(monkeypatch, name):
    get = Mock()
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.get_country_details(name) == {"error": "name must not be empty"}
    get.assert_not_called()


def test_tools_tolerate_missing_optional_country_fields(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx,
        "get",
        Mock(return_value=_response(200, {"data": {"objects": [{}]}})),
    )

    assert server.search_countries("Unknown") == [
        {"name": None, "capital": None, "region": None, "population": None}
    ]
    assert server.get_country_details("Unknown") == {
        "country_name": None,
        "currencies": [],
        "languages": [],
        "borders": [],
        "flag_url": None,
    }


def test_get_country_details_requires_api_key(monkeypatch):
    monkeypatch.delenv(server.API_KEY_ENV, raising=False)
    get = Mock()
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.get_country_details("Türkiye") == {
        "error": "REST_COUNTRIES_API_KEY is not configured"
    }
    get.assert_not_called()


def test_get_country_details_returns_model_friendly_shape(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    response = _response(
        200,
        {
            "data": {
                "objects": [
                    {
                        "names": {"common": "Türkiye"},
                        "currencies": [
                            {
                                "code": "TRY",
                                "name": "Turkish lira",
                                "symbol": "₺",
                            }
                        ],
                        "languages": [{"name": "Turkish"}],
                        "borders": ["ARM", "BGR"],
                        "flag": {"url_png": "https://flags.example/tr.png"},
                    }
                ]
            }
        },
    )
    get = Mock(return_value=response)
    monkeypatch.setattr(server.httpx, "get", get)

    assert server.get_country_details(" Türkiye ") == {
        "country_name": "Türkiye",
        "currencies": [{"code": "TRY", "name": "Turkish lira", "symbol": "₺"}],
        "languages": ["Turkish"],
        "borders": [
            {"code": "ARM", "country_name": "Armenia"},
            {"code": "BGR", "country_name": "Bulgaria"},
        ],
        "flag_url": "https://flags.example/tr.png",
    }
    get.assert_called_once_with(
        f"{server.BASE_URL}/name",
        params={
            "q": "Türkiye",
            "limit": 1,
            "response_fields": server.DETAIL_FIELDS,
        },
        headers={"Authorization": "Bearer test-key"},
        timeout=server.REQUEST_TIMEOUT,
    )


def test_get_country_details_returns_not_found(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx,
        "get",
        Mock(return_value=_response(200, {"data": {"objects": []}})),
    )

    assert server.get_country_details("not-a-country") == {"error": "country not found"}


@pytest.mark.parametrize(
    ("side_effect", "message"),
    [
        (httpx.TimeoutException("too slow"), "upstream request timed out"),
        (httpx.RequestError("offline"), "upstream request failed"),
    ],
)
def test_get_country_details_handles_network_errors(monkeypatch, side_effect, message):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(server.httpx, "get", Mock(side_effect=side_effect))

    assert server.get_country_details("Türkiye") == {"error": message}


def test_get_country_details_handles_http_error(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx, "get", Mock(return_value=_response(503, {"errors": []}))
    )

    assert server.get_country_details("Türkiye") == {
        "error": "upstream returned HTTP 503"
    }


def test_get_country_details_handles_invalid_json(monkeypatch):
    monkeypatch.setenv(server.API_KEY_ENV, "test-key")
    monkeypatch.setattr(
        server.httpx, "get", Mock(return_value=_invalid_json_response())
    )

    assert server.get_country_details("Türkiye") == {
        "error": "upstream returned invalid JSON"
    }
