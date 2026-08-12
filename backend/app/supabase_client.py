"""
Cliente Supabase para o Backend
Usa a API REST do Supabase ao invés de conexão PostgreSQL direta
"""
import os
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Fuso horário de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

def _today_brt() -> str:
    """Retorna data de hoje no horário de Brasília (YYYY-MM-DD)"""
    return datetime.now(BRT).strftime("%Y-%m-%d")

# Carregar .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
# Prioriza SERVICE_KEY (bypassa RLS) sobre ANON_KEY
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
).strip()

# Anon key for RLS-enabled requests (service key bypasses RLS)
SUPABASE_ANON_KEY = (
    os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_KEY") or ""
).strip()


def _require_supabase_config(url: str | None, key: str | None) -> None:
    if not (url or "").strip():
        raise RuntimeError(
            "SUPABASE_URL não configurada. Defina no backend/.env (veja .env.example)."
        )
    if not (key or "").strip():
        raise RuntimeError(
            "Configure SUPABASE_SERVICE_KEY e/ou SUPABASE_ANON_KEY no backend/.env."
        )


class SupabaseClient:
    """Cliente REST para Supabase"""
    
    def __init__(self, url: str = None, key: str = None, user_token: str = None):
        resolved_url = url or SUPABASE_URL
        resolved_key = key or SUPABASE_KEY
        _require_supabase_config(resolved_url, resolved_key)
        self.url = resolved_url
        self.key = resolved_key
        self.rest_url = f"{self.url}/rest/v1"
        # If user_token is provided, use it for Authorization (enables RLS as that user)
        # but keep apikey as the anon key
        auth_key = user_token or self.key
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {auth_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
    
    async def _request(
        self, 
        method: str, 
        table: str, 
        data: dict = None, 
        params: dict = None
    ) -> Any:
        """Faz requisição à API REST do Supabase"""
        async with httpx.AsyncClient() as client:
            url = f"{self.rest_url}/{table}"
            
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
            )
            
            if response.status_code >= 400:
                raise Exception(f"Supabase error: {response.status_code} - {response.text}")
            
            if response.text:
                return response.json()
            return None
    
    async def list_sites(self, limit: int = 50) -> List[Dict]:
        """Lista todos os sites"""
        return await self._request(
            "GET", 
            "sites",
            params={"select": "*", "order": "created_at.desc", "limit": limit}
        )
    
    async def list_sites_for_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Lista sites de um usuário específico"""
        return await self._request(
            "GET",
            "sites",
            params={"select": "*", "user_id": f"eq.{user_id}", "order": "created_at.desc", "limit": limit}
        )
    
    async def get_site(self, site_id: str) -> Optional[Dict]:
        """Busca um site por ID"""
        result = await self._request(
            "GET",
            "sites",
            params={"id": f"eq.{site_id}", "select": "*"}
        )
        return result[0] if result else None
    
    async def create_site(self, base_url: str, platform: str = None, user_id: str = None) -> Dict:
        """Cria um novo site"""
        data = {
            "base_url": base_url,
            "platform": platform,
        }
        if user_id:
            data["user_id"] = user_id
        result = await self._request("POST", "sites", data=data)
        return result[0] if result else data
    
    async def update_site(self, site_id: str, base_url: str = None, platform: str = None) -> Dict:
        """Atualiza um site"""
        data = {}
        if base_url:
            data["base_url"] = base_url
        if platform:
            data["platform"] = platform
        
        result = await self._request(
            "PATCH",
            f"sites?id=eq.{site_id}",
            data=data
        )
        return result[0] if result else data
    
    async def delete_site(self, site_id: str) -> bool:
        """Remove um site"""
        await self._request("DELETE", f"sites?id=eq.{site_id}")
        return True
    
    async def list_pages(self, site_id: str) -> List[Dict]:
        """Lista páginas de um site"""
        return await self._request(
            "GET",
            "pages",
            params={"site_id": f"eq.{site_id}", "select": "*", "order": "last_scanned_at.desc"}
        )

    async def find_page_by_url(self, site_id: str, url: str) -> Optional[Dict]:
        """Busca a página de um site cuja URL bate com `url` (comparação
        normalizada, ignorando protocolo/www/barra final). Usada para ligar uma
        otimização de plataforma (produto/categoria) à página correspondente
        do scan genérico (pages/seo_tasks)."""
        if not url:
            return None

        def norm(u: str) -> str:
            u = (u or "").strip().lower()
            u = u.replace("https://", "").replace("http://", "")
            if u.startswith("www."):
                u = u[4:]
            return u.rstrip("/")

        target = norm(url)
        if not target:
            return None
        pages = await self.list_pages(site_id)
        for p in pages:
            if norm(p.get("url", "")) == target:
                return p
        return None

    async def approve_pending_tasks_for_page(self, page_id: str) -> int:
        """Marca como 'approved' todas as tasks pendentes de uma página.
        Chamado após aplicar de fato uma otimização de IA numa página (produto/
        categoria de uma integração), para que o Dashboard reflita o selo
        '✓ Otimizado' e o filtro 'Já Otimizados'. Retorna quantas foram marcadas."""
        tasks = await self._request(
            "GET",
            "seo_tasks",
            params={"page_id": f"eq.{page_id}", "status": "eq.pending", "select": "id"},
        )
        count = 0
        for t in tasks:
            await self.update_task_status(str(t["id"]), "approved")
            count += 1
        return count

    async def upsert_page(self, site_id: str, url: str, data: Dict) -> Dict:
        """Cria ou atualiza uma página"""
        # Verificar se já existe
        existing = await self._request(
            "GET",
            "pages",
            params={"site_id": f"eq.{site_id}", "url": f"eq.{url}", "select": "id"}
        )
        
        page_data = {
            "site_id": site_id,
            "url": url,
            "title": data.get("title"),
            "meta_description": data.get("meta_description"),
            "h1": data.get("h1"),
            "issues": data.get("issues", {}),
            "score": data.get("seo_score", 0),
            "last_scanned_at": datetime.utcnow().isoformat(),
        }
        
        if existing:
            # Update
            result = await self._request(
                "PATCH",
                f"pages?id=eq.{existing[0]['id']}",
                data=page_data
            )
        else:
            # Insert
            result = await self._request("POST", "pages", data=page_data)
        
        return result[0] if result else page_data
    
    async def delete_page(self, page_id: str) -> bool:
        """Remove uma página"""
        await self._request("DELETE", f"pages?id=eq.{page_id}")
        return True
    
    async def list_tasks(self, site_id: str, status: str = None) -> List[Dict]:
        """Lista tarefas de um site"""
        params = {"site_id": f"eq.{site_id}", "select": "*", "order": "created_at.desc"}
        if status:
            params["status"] = f"eq.{status}"
        return await self._request("GET", "seo_tasks", params=params)
    
    async def create_task(
        self, 
        site_id: str, 
        page_id: str,
        task_type: str,
        payload: Dict,
        ai_suggestion: str = None
    ) -> Dict:
        """Cria uma nova tarefa"""
        data = {
            "site_id": site_id,
            "page_id": page_id,
            "issue_type": task_type,
            "description": payload.get("issue", task_type),
            "suggestion": ai_suggestion,
            "priority": "medium",
            "status": "pending",
        }
        result = await self._request("POST", "seo_tasks", data=data)
        return result[0] if result else data
    
    async def update_task_status(self, task_id: str, status: str) -> Dict:
        """Atualiza status de uma tarefa"""
        data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        result = await self._request(
            "PATCH",
            f"seo_tasks?id=eq.{task_id}",
            data=data
        )
        return result[0] if result else data
    
    async def delete_task(self, task_id: str) -> bool:
        """Remove uma tarefa"""
        await self._request("DELETE", f"seo_tasks?id=eq.{task_id}")
        return True
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Busca uma tarefa por ID"""
        result = await self._request(
            "GET",
            "seo_tasks",
            params={"id": f"eq.{task_id}", "select": "*"}
        )
        return result[0] if result else None
    
    async def get_page(self, page_id: str) -> Optional[Dict]:
        """Busca uma página por ID"""
        result = await self._request(
            "GET",
            "pages",
            params={"id": f"eq.{page_id}", "select": "*"}
        )
        return result[0] if result else None
    
    async def update_task(self, task_id: str, data: Dict) -> Dict:
        """Atualiza uma tarefa com dados arbitrários"""
        data["updated_at"] = datetime.utcnow().isoformat()
        result = await self._request(
            "PATCH",
            f"seo_tasks?id=eq.{task_id}",
            data=data
        )
        return result[0] if result else data
    
    async def get_latest_scan_run(self, site_id: str) -> Optional[Dict]:
        """Retorna o scan_run mais recente (completed) de um site"""
        result = await self._request(
            "GET",
            "scan_runs",
            params={
                "site_id": f"eq.{site_id}",
                "status": "eq.completed",
                "select": "*",
                "order": "completed_at.desc",
                "limit": "1",
            }
        )
        return result[0] if result else None

    async def get_running_scan_run(self, site_id: str) -> Optional[Dict]:
        """Retorna o scan_run 'running' mais recente de um site, se houver.
        Usado para evitar dois scans concorrentes do mesmo site (ex.: auto-scan
        de onboarding ainda rodando quando o usuário pede um scan manual)."""
        result = await self._request(
            "GET",
            "scan_runs",
            params={
                "site_id": f"eq.{site_id}",
                "status": "eq.running",
                "select": "*",
                "order": "started_at.desc",
                "limit": "1",
            }
        )
        return result[0] if result else None

    async def list_recent_scan_runs(self, site_id: str, limit: int = 2) -> List[Dict]:
        """Retorna os últimos N scan_runs (completed) de um site, ordenados por completed_at DESC."""
        result = await self._request(
            "GET",
            "scan_runs",
            params={
                "site_id": f"eq.{site_id}",
                "status": "eq.completed",
                "select": "*",
                "order": "completed_at.desc",
                "limit": str(limit),
            }
        )
        return result or []

    async def create_scan_run(self, site_id: str) -> Dict:
        """Inicia um novo scan"""
        data = {
            "site_id": site_id,
            "status": "running",
            "started_at": datetime.utcnow().isoformat(),
        }
        result = await self._request("POST", "scan_runs", data=data)
        return result[0] if result else data
    
    async def complete_scan_run(
        self, 
        scan_id: str, 
        pages_scanned: int,
        tasks_created: int,
        avg_score: int,
        issues_summary: Dict = None
    ) -> Dict:
        """Finaliza um scan"""
        data = {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
            "pages_scanned": pages_scanned,
            "tasks_created": tasks_created,
            "avg_score": avg_score,
        }
        if issues_summary is not None:
            data["issues_summary"] = issues_summary
        try:
            result = await self._request(
                "PATCH",
                f"scan_runs?id=eq.{scan_id}",
                data=data
            )
        except Exception as e:
            # Fallback: caso a coluna issues_summary não exista no schema, repete sem ela.
            if "issues_summary" in data:
                data.pop("issues_summary", None)
                result = await self._request(
                    "PATCH",
                    f"scan_runs?id=eq.{scan_id}",
                    data=data
                )
            else:
                raise
        return result[0] if result else data

    async def save_integration(
        self, user_id: str, platform: str, store_url: str,
        access_token: str = None, store_name: str = None, metadata: dict = None
    ) -> Dict:
        """Salva ou atualiza integração do usuário (upsert por user_id)"""
        data = {
            "user_id": user_id,
            "platform": platform,
            "store_url": store_url,
            "access_token": access_token,
            "store_name": store_name,
            "metadata": metadata or {},
        }
        # Use upsert (on conflict user_id)
        headers = {**self.headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/user_integrations",
                headers=headers,
                json=data,
                params={"on_conflict": "user_id"},
            )
            if response.status_code >= 400:
                raise Exception(f"Supabase error: {response.status_code} - {response.text}")
            result = response.json()
            return result[0] if isinstance(result, list) and result else result

    async def delete_integration(self, user_id: str) -> bool:
        """Remove o registro de integração do usuário (credenciais salvas).
        Precisa ser chamado junto com delete_site no disconnect — caso contrário
        o endpoint de status restaura a loja a partir daqui (loop de reconexão)."""
        await self._request("DELETE", f"user_integrations?user_id=eq.{user_id}")
        return True

    async def get_integration(self, user_id: str) -> Optional[Dict]:
        """Busca integração do usuário"""
        result = await self._request(
            "GET",
            "user_integrations",
            params={"user_id": f"eq.{user_id}", "select": "*", "limit": "1"}
        )
        return result[0] if result else None

    async def increment_applied_count(self, user_id: str, delta: int = 1) -> None:
        """Incrementa metadata.applied_count em user_integrations.
        Persiste o contador de otimizações aplicadas (sobrevive a cold starts)."""
        if not delta:
            return
        try:
            integration = await self.get_integration(user_id)
            if not integration:
                return
            meta = integration.get("metadata") or {}
            meta["applied_count"] = int(meta.get("applied_count") or 0) + int(delta)
            headers = {**self.headers, "Prefer": "return=representation"}
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"{self.rest_url}/user_integrations",
                    headers=headers,
                    json={"metadata": meta},
                    params={"user_id": f"eq.{user_id}"},
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"increment_applied_count falhou: {e}")

    async def save_oauth_state(self, state: str, user_id: str, user_token: str) -> None:
        """Persiste OAuth state no banco para sobreviver a restarts do servidor"""
        data = {
            "state": state,
            "user_id": user_id,
            "user_token": user_token,
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        }
        headers = {**self.headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/oauth_states",
                headers=headers,
                json=data,
            )
            if response.status_code >= 400:
                raise Exception(f"save_oauth_state error: {response.status_code} - {response.text}")

    async def get_oauth_state(self, state: str) -> Optional[Dict]:
        """Recupera OAuth state do banco"""
        result = await self._request(
            "GET",
            "oauth_states",
            params={"state": f"eq.{state}", "select": "*", "limit": "1"}
        )
        if result:
            row = result[0]
            # Verificar expiração
            try:
                expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires:
                    return None
            except Exception:
                pass
            return row
        return None

    async def delete_oauth_state(self, state: str) -> None:
        """Remove OAuth state usado"""
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{self.rest_url}/oauth_states",
                headers=self.headers,
                params={"state": f"eq.{state}"},
            )

    async def list_search_terms(self, user_id: str) -> List[Dict]:
        """Lista termos de pesquisa do usuário"""
        return await self._request(
            "GET",
            "user_search_terms",
            params={"user_id": f"eq.{user_id}", "select": "*", "order": "created_at.desc"}
        )

    async def count_search_terms(self, user_id: str) -> int:
        """Conta termos de pesquisa do usuário"""
        terms = await self.list_search_terms(user_id)
        return len(terms)

    async def create_search_term(self, user_id: str, term: str) -> Dict:
        """Cria um novo termo de pesquisa"""
        data = {"user_id": user_id, "term": term}
        result = await self._request("POST", "user_search_terms", data=data)
        return result[0] if result else data

    async def delete_search_term(self, term_id: str, user_id: str) -> bool:
        """Remove um termo (verifica ownership via user_id)"""
        await self._request("DELETE", f"user_search_terms?id=eq.{term_id}&user_id=eq.{user_id}")
        return True

    async def get_search_term(self, term_id: str, user_id: str) -> Optional[Dict]:
        """Busca termo por ID (com ownership check)"""
        result = await self._request(
            "GET",
            "user_search_terms",
            params={"id": f"eq.{term_id}", "user_id": f"eq.{user_id}", "select": "*"}
        )
        return result[0] if result else None

    async def save_term_snapshot(self, term_id: str, user_id: str, interest_over_time: Dict, related_queries: Dict) -> Dict:
        """Salva snapshot de dados do Pytrends para um termo"""
        data = {
            "term_id": term_id,
            "user_id": user_id,
            "interest_over_time": interest_over_time,
            "related_queries": related_queries,
            "date": _today_brt(),
        }
        result = await self._request("POST", "term_snapshots", data=data)
        return result[0] if result else data

    async def get_latest_term_snapshot(self, term_id: str) -> Optional[Dict]:
        """Busca snapshot mais recente de um termo"""
        result = await self._request(
            "GET",
            "term_snapshots",
            params={
                "term_id": f"eq.{term_id}",
                "select": "*",
                "order": "date.desc",
                "limit": "1",
            }
        )
        return result[0] if result else None

    async def save_daily_snapshot(self, user_id: str, data: Dict) -> Dict:
        """Salva snapshot diário de GSC"""
        snapshot = {
            "user_id": user_id,
            "date": data.get("date", _today_brt()),
            "impressions": data.get("impressions", 0),
            "clicks": data.get("clicks", 0),
            "ctr": data.get("ctr", 0),
            "position_avg": data.get("position_avg", 0),
            "pages_count": data.get("pages_count", 0),
        }
        # Upsert by user_id + date
        headers = {**self.headers, "Prefer": "return=representation,resolution=merge-duplicates"}
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.rest_url}/daily_snapshots",
                headers=headers,
                json=snapshot,
                params={"on_conflict": "user_id,date"},
            )
            if response.status_code >= 400:
                raise Exception(f"Supabase error: {response.status_code} - {response.text}")
            result = response.json()
            return result[0] if isinstance(result, list) and result else result

    async def list_daily_snapshots(self, user_id: str, days: int = 30) -> List[Dict]:
        """Lista snapshots diários dos últimos N dias"""
        cutoff = (datetime.now(BRT) - timedelta(days=days)).strftime("%Y-%m-%d")
        return await self._request(
            "GET",
            "daily_snapshots",
            params={
                "user_id": f"eq.{user_id}",
                "date": f"gte.{cutoff}",
                "select": "*",
                "order": "date.asc",
            }
        )


# Singleton for service-role (admin) operations
_client: Optional[SupabaseClient] = None


def get_supabase() -> SupabaseClient:
    """Retorna instância do cliente Supabase (service role)"""
    global _client
    if _client is None:
        _client = SupabaseClient()
    return _client


def get_supabase_for_user(user_token: str) -> SupabaseClient:
    """Retorna cliente Supabase autenticado como o usuário (para RLS).
    Uses anon key as apikey so RLS is enforced (service key bypasses RLS)."""
    return SupabaseClient(key=SUPABASE_ANON_KEY, user_token=user_token)
