"""
Tests for SearchAPI trending now + termos lookup/trending endpoints.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestFetchTrendingNow:
    @pytest.mark.asyncio
    async def test_returns_error_without_api_key(self):
        from app.integrations import searchapi_client as client

        client.clear_trending_cache()
        with patch.object(client, "SEARCHAPI_KEY", ""):
            result = await client.fetch_trending_now(use_cache=False)

        assert result["trends"] == []
        assert result["count"] == 0
        assert "error" in result
        assert "SEARCHAPI_KEY" in result["error"]

    @pytest.mark.asyncio
    async def test_parses_and_limits_to_six(self):
        from app.integrations import searchapi_client as client

        client.clear_trending_cache()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "trends": [
                {
                    "position": i,
                    "query": f"termo {i}",
                    "search_volume": 1000 * i,
                    "percentage_increase": 10 * i,
                    "categories": ["shopping"],
                    "keywords": [f"termo {i}"],
                    "is_active": True,
                }
                for i in range(1, 10)
            ]
        }
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "SEARCHAPI_KEY", "test-key"):
            with patch.object(client.httpx, "AsyncClient", return_value=mock_http):
                result = await client.fetch_trending_now(
                    geo="BR", time_window="past_24_hours", limit=6, use_cache=False
                )

        assert result["geo"] == "BR"
        assert result["time"] == "past_24_hours"
        assert result["count"] == 6
        assert len(result["trends"]) == 6
        assert result["trends"][0]["query"] == "termo 1"
        assert result["trends"][0]["search_volume"] == 1000
        assert result["cached"] is False

        # chamada HTTP com engine correto
        params = mock_http.get.call_args.kwargs.get("params") or mock_http.get.call_args[1].get("params")
        assert params["engine"] == "google_trends_trending_now"
        assert params["geo"] == "BR"
        assert params["time"] == "past_24_hours"

    @pytest.mark.asyncio
    async def test_uses_cache_on_second_call(self):
        from app.integrations import searchapi_client as client

        client.clear_trending_cache()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "trends": [
                {
                    "position": 1,
                    "query": "cache hit",
                    "search_volume": 5000,
                    "percentage_increase": 100,
                    "categories": ["other"],
                    "keywords": ["cache hit"],
                    "is_active": True,
                }
            ]
        }
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "SEARCHAPI_KEY", "test-key"):
            with patch.object(client.httpx, "AsyncClient", return_value=mock_http):
                first = await client.fetch_trending_now(limit=6, use_cache=True)
                second = await client.fetch_trending_now(limit=6, use_cache=True)

        assert first["cached"] is False
        assert second["cached"] is True
        assert second["trends"][0]["query"] == "cache hit"
        assert mock_http.get.call_count == 1

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        from app.integrations import searchapi_client as client
        import httpx

        client.clear_trending_cache()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "rate limited"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429", request=MagicMock(), response=mock_response
        )
        mock_http = AsyncMock()
        mock_http.get.return_value = mock_response
        mock_http.__aenter__ = AsyncMock(return_value=mock_http)
        mock_http.__aexit__ = AsyncMock(return_value=False)

        with patch.object(client, "SEARCHAPI_KEY", "test-key"):
            with patch.object(client.httpx, "AsyncClient", return_value=mock_http):
                result = await client.fetch_trending_now(use_cache=False)

        assert result["trends"] == []
        assert "HTTP 429" in result["error"]


class TestTermosEndpoints:
    @pytest.mark.asyncio
    async def test_trending_endpoint_returns_payload(self):
        from app.main import termos_trending

        mock_payload = {
            "geo": "BR",
            "time": "past_24_hours",
            "trends": [{"position": 1, "query": "x", "search_volume": 10}],
            "count": 1,
            "cached": False,
        }
        with patch(
            "app.integrations.searchapi_client.fetch_trending_now",
            new_callable=AsyncMock,
            return_value=mock_payload,
        ):
            result = await termos_trending(user={"user_id": "u1", "token": "t"})

        assert result["geo"] == "BR"
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_lookup_validates_min_length(self):
        from app.main import lookup_termo, LookupTermRequest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await lookup_termo(
                LookupTermRequest(term="a"),
                user={"user_id": "u1", "token": "t"},
            )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_lookup_returns_enriched_result_without_saving(self):
        from app.main import lookup_termo, LookupTermRequest

        mock_trends = {
            "keywords": ["tenis feminino"],
            "trends": {
                "tenis feminino": {
                    "current": 72,
                    "average": 55,
                    "peak": 90,
                    "trend": "up",
                    "history": [50, 60, 72],
                }
            },
            "related": {
                "tenis feminino": {
                    "top": [
                        {"query": "tenis corrida", "value": 80},
                        {"query": "tenis casual", "value": 70},
                        {"query": "tenis caminhada", "value": 60},
                    ],
                    "rising": [{"query": "tenis branco", "value": 100}],
                }
            },
        }
        with patch(
            "app.integrations.searchapi_client.fetch_trends",
            new_callable=AsyncMock,
            return_value=mock_trends,
        ):
            result = await lookup_termo(
                LookupTermRequest(term="tenis feminino"),
                user={"user_id": "u1", "token": "t"},
            )

        assert result["term"] == "tenis feminino"
        assert result["current_interest"] == 72
        assert result["chance"] == "alta"
        assert result["trend"] == "up"
        assert len(result["related"]["top"]) == 3
