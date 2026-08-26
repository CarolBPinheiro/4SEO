"""
Google Search Console API Integration
Test mode supports up to 100 integrations without Google review.

OAuth flow with per-user token isolation:
1. User clicks "Conectar GSC" → frontend calls GET /api/gsc/auth-url
2. Backend generates Google OAuth URL with user_id in state
3. User authorizes → Google redirects to GET /api/gsc/callback
4. Backend exchanges code for tokens, stores in gsc_tokens table (RLS-protected)
5. All subsequent API calls use the stored tokens for that user

Setup:
1. Google Cloud Console → Enable Search Console API
2. Create OAuth 2.0 credential (Web application)
3. Add redirect URI: http://localhost:8000/api/gsc/callback (dev) / https://yourdomain/api/gsc/callback (prod)
4. Set GSC_CLIENT_ID, GSC_CLIENT_SECRET, GSC_REDIRECT_URI in .env
"""
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv
import httpx

load_dotenv()

GSC_CLIENT_ID = os.getenv("GSC_CLIENT_ID", "")
GSC_CLIENT_SECRET = os.getenv("GSC_CLIENT_SECRET", "")
GSC_REDIRECT_URI = os.getenv("GSC_REDIRECT_URI", "http://localhost:8000/api/gsc/callback")

# Supabase config for storing tokens
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def get_gsc_auth_url(user_id: str) -> str:
    """Generate Google OAuth URL for Search Console API. user_id is encoded in state for callback."""
    scope = "https://www.googleapis.com/auth/webmasters.readonly"
    return (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GSC_CLIENT_ID}&"
        f"redirect_uri={GSC_REDIRECT_URI}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent&"
        f"state={user_id}"
    )


async def exchange_gsc_code(code: str) -> Dict[str, str]:
    """Exchange authorization code for access/refresh tokens"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GSC_CLIENT_ID,
                "client_secret": GSC_CLIENT_SECRET,
                "redirect_uri": GSC_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            raise Exception(f"GSC token exchange failed: {resp.text}")
        return resp.json()


async def refresh_gsc_token(refresh_token: str) -> Dict[str, str]:
    """Refresh an expired access token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "refresh_token": refresh_token,
                "client_id": GSC_CLIENT_ID,
                "client_secret": GSC_CLIENT_SECRET,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code != 200:
            raise Exception(f"GSC token refresh failed: {resp.text}")
        return resp.json()


async def _supabase_request(method: str, path: str, json_data: dict = None, params: dict = None) -> Any:
    """Make a request to Supabase REST API using service key (bypasses RLS)"""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{path}",
            headers=headers,
            json=json_data,
            params=params,
        )
        if resp.status_code >= 400:
            raise Exception(f"Supabase error: {resp.status_code} - {resp.text}")
        return resp.json() if resp.text else None


async def store_gsc_tokens(user_id: str, tokens: dict, site_url: str = "") -> dict:
    """Store or update GSC tokens for a user in the gsc_tokens table"""
    expires_in = tokens.get("expires_in", 3600)
    expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat()

    # Check if user already has tokens
    existing = await _supabase_request(
        "GET", "gsc_tokens",
        params={"user_id": f"eq.{user_id}", "select": "id"},
    )

    data = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token", ""),
        "expires_at": expires_at,
        "site_url": site_url or "",
        "updated_at": datetime.utcnow().isoformat(),
    }

    if existing:
        # Update
        result = await _supabase_request(
            "PATCH", f"gsc_tokens?user_id=eq.{user_id}",
            json_data=data,
        )
    else:
        # Insert
        data["user_id"] = user_id
        result = await _supabase_request("POST", "gsc_tokens", json_data=data)

    return result[0] if result else data


async def get_gsc_tokens(user_id: str) -> Optional[dict]:
    """Get stored GSC tokens for a user. Auto-refreshes if expired."""
    result = await _supabase_request(
        "GET", "gsc_tokens",
        params={"user_id": f"eq.{user_id}", "select": "*"},
    )
    if not result:
        return None

    token_row = result[0]
    if str(token_row.get("access_token") or "").startswith("demo_") or str(
        token_row.get("refresh_token") or ""
    ).startswith("demo_"):
        return token_row

    expires_at = token_row.get("expires_at", "")

    # Check if token is expired (with 5 min buffer)
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00").replace("+00:00", ""))
            if datetime.utcnow() > exp - timedelta(minutes=5):
                # Token expired  - refresh it
                refresh_token = token_row.get("refresh_token")
                if not refresh_token:
                    return None  # Can't refresh, user must re-authorize

                new_tokens = await refresh_gsc_token(refresh_token)
                # Preserve the refresh_token if Google didn't issue a new one
                if "refresh_token" not in new_tokens:
                    new_tokens["refresh_token"] = refresh_token
                updated = await store_gsc_tokens(
                    user_id, new_tokens, token_row.get("site_url", "")
                )
                return updated
        except (ValueError, TypeError):
            pass  # If date parsing fails, use token as-is

    return token_row


async def delete_gsc_tokens(user_id: str) -> None:
    """Delete GSC tokens for a user (disconnect)"""
    await _supabase_request("DELETE", f"gsc_tokens?user_id=eq.{user_id}")


async def list_gsc_sites(access_token: str) -> List[str]:
    """List all sites the user has access to in GSC"""
    from app.demo.gsc import demo_sites, is_demo_gsc_token

    if is_demo_gsc_token(access_token):
        return demo_sites()

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/webmasters/v3/sites",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code != 200:
            raise Exception(f"GSC sites list error: {resp.text}")
        data = resp.json()
        return [entry["siteUrl"] for entry in data.get("siteEntry", [])]


async def fetch_gsc_performance(
    access_token: str,
    site_url: str,
    start_date: str = None,
    end_date: str = None,
    dimensions: List[str] = None,
    row_limit: int = 100,
) -> Dict[str, Any]:
    """
    Fetch performance data from Google Search Console API.
    Returns impressions, clicks, CTR, position for the site.
    """
    from app.demo.gsc import demo_performance, is_demo_gsc_token

    if is_demo_gsc_token(access_token):
        return demo_performance(dimensions)

    if not start_date:
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    if not dimensions:
        dimensions = ["query"]

    body = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "rowLimit": row_limit,
    }

    encoded_site = site_url.replace(":", "%3A").replace("/", "%2F")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if resp.status_code != 200:
            raise Exception(f"GSC API error: {resp.status_code} - {resp.text}")
        return resp.json()


async def fetch_gsc_overview(access_token: str, site_url: str) -> Dict[str, Any]:
    """
    Fetch overview metrics: total impressions, clicks, avg CTR, avg position.
    Also fetches unique pages that appeared in search.
    """
    from app.demo.gsc import demo_overview, is_demo_gsc_token

    if is_demo_gsc_token(access_token):
        return demo_overview(site_url)

    overall = await fetch_gsc_performance(
        access_token, site_url, dimensions=[], row_limit=1
    )
    pages = await fetch_gsc_performance(
        access_token, site_url, dimensions=["page"], row_limit=1000
    )
    queries = await fetch_gsc_performance(
        access_token, site_url, dimensions=["query"], row_limit=50
    )

    totals = overall.get("rows", [{}])
    total_row = totals[0] if totals else {}

    return {
        "impressions": total_row.get("impressions", 0),
        "clicks": total_row.get("clicks", 0),
        "ctr": round(total_row.get("ctr", 0) * 100, 2),
        "position": round(total_row.get("position", 0), 1),
        "unique_pages": len(pages.get("rows", [])),
        "top_queries": [
            {
                "query": row["keys"][0],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            }
            for row in queries.get("rows", [])[:20]
        ],
    }


async def fetch_gsc_page_performance(
    access_token: str,
    site_url: str,
    page_url: str,
) -> Dict[str, Any]:
    """
    Fetch GSC performance metrics for a specific page (last 30 days).
    Returns clicks, impressions, CTR, avg position, and top queries for the page.
    """
    from app.demo.gsc import demo_page_performance, is_demo_gsc_token

    if is_demo_gsc_token(access_token):
        return demo_page_performance(page_url)

    try:
        # Page-level aggregate
        page_data = await fetch_gsc_performance(
            access_token, site_url,
            dimensions=["page"],
            row_limit=1000,
        )
        page_row = None
        for row in page_data.get("rows", []):
            if row.get("keys", [""])[0] == page_url:
                page_row = row
                break

        if not page_row:
            return {"page_url": page_url, "found": False}

        # Top queries for this page
        from datetime import datetime as _dt, timedelta as _td
        start = (_dt.utcnow() - _td(days=30)).strftime("%Y-%m-%d")
        end = (_dt.utcnow() - _td(days=1)).strftime("%Y-%m-%d")
        encoded_site = site_url.replace(":", "%3A").replace("/", "%2F")

        body = {
            "startDate": start,
            "endDate": end,
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [{"dimension": "page", "expression": page_url}]
            }],
            "rowLimit": 20,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=body,
            )
        queries = []
        if resp.status_code == 200:
            for row in resp.json().get("rows", []):
                queries.append({
                    "query": row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                })

        return {
            "page_url": page_url,
            "found": True,
            "clicks": page_row.get("clicks", 0),
            "impressions": page_row.get("impressions", 0),
            "ctr": round(page_row.get("ctr", 0) * 100, 2),
            "position": round(page_row.get("position", 0), 1),
            "top_queries": queries,
        }
    except Exception as e:
        return {"page_url": page_url, "found": False, "error": str(e)}
