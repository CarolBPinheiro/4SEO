"""
Service Layer for SiteCan Backend
Separates business logic from persistence and API concerns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.supabase_client import SupabaseClient, get_supabase
from app.seo_analysis import ISSUE_CONFIG, analyze_seo_html
from app.crawler import crawl_site

# Tempo máximo que um scan_run "running" é considerado genuinamente em
# andamento. Passado isso, é tratado como abandonado (processo derrubado
# antes de chamar complete_scan_run) e um novo scan é permitido — evita que
# uma falha travada bloqueie o site para sempre.
SCAN_LOCK_TIMEOUT_SECONDS = 600  # 10 minutos


class ScanInProgressError(Exception):
    """Levantado quando já existe um scan em andamento (não obsoleto) para o site."""
    pass


class SiteService:
    """Business logic for site management"""
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_supabase()
    
    async def list_sites(self, limit: int = 50, user_id: str = None) -> List[Dict]:
        """List sites  - filtered by user_id when provided"""
        if user_id:
            return await self.db.list_sites_for_user(user_id, limit)
        return await self.db.list_sites(limit)
    
    async def get_site(self, site_id: str) -> Optional[Dict]:
        """Get a site by ID"""
        return await self.db.get_site(site_id)
    
    async def create_site(self, base_url: str, platform: str = None, user_id: str = None) -> Dict:
        """Create a new site with auto-detected platform"""
        # Auto-detect platform from URL
        url_lower = base_url.lower()
        if not platform:
            if "myshopify.com" in url_lower or "shopify" in url_lower:
                platform = "shopify"
            elif "nuvemshop" in url_lower or "lojavirtual" in url_lower:
                platform = "nuvemshop"
            elif "wordpress" in url_lower or "wp-content" in url_lower:
                platform = "wordpress"
        
        return await self.db.create_site(base_url, platform, user_id=user_id)
    
    async def update_site(self, site_id: str, base_url: str = None, platform: str = None) -> Dict:
        """Update a site"""
        return await self.db.update_site(site_id, base_url, platform)
    
    async def delete_site(self, site_id: str) -> bool:
        """Delete a site"""
        return await self.db.delete_site(site_id)


class ScanService:
    """Business logic for SEO scanning"""
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_supabase()
    
    async def run_scan(self, site_id: str, max_pages: int = 30) -> Dict[str, Any]:
        """
        Run a full SEO scan for a site.
        Returns scan results with pages analyzed and tasks created.
        """
        import logging
        _log = logging.getLogger(__name__)

        site = await self.db.get_site(site_id)
        if not site:
            raise ValueError("Site não encontrado")

        # Evita dois scans concorrentes do mesmo site (ex.: o auto-scan de
        # onboarding ainda rodando quando o usuário clica "Analisar meu site
        # agora" logo em seguida) — sem isso, cada execução concorrente
        # duplica seo_tasks e cria dois scan_runs quase simultâneos.
        running = await self.db.get_running_scan_run(site_id)
        if running:
            stale = True
            started_at = running.get("started_at")
            if started_at:
                try:
                    started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    now = datetime.now(started.tzinfo) if started.tzinfo else datetime.utcnow()
                    stale = (now - started).total_seconds() > SCAN_LOCK_TIMEOUT_SECONDS
                except Exception:
                    stale = True
            if not stale:
                raise ScanInProgressError(f"Já existe um scan em andamento para o site {site_id}")

        base_url = site.get("base_url") or ""
        _log.info(f"[ScanService] run_scan start site={site_id} base_url={base_url!r} max={max_pages}")

        # Create scan run record
        scan_run = await self.db.create_scan_run(site_id)

        # Execute crawl
        try:
            result = await crawl_site(base_url, max_pages=max_pages)
        except Exception as e:
            _log.exception(f"[ScanService] crawl_site falhou site={site_id}: {e}")
            # Completa o scan_run com 0 páginas para não deixar em estado pendurado
            await self.db.complete_scan_run(
                scan_id=str(scan_run["id"]),
                pages_scanned=0,
                tasks_created=0,
                avg_score=0,
                issues_summary={"crawl_error": 1},
            )
            raise

        _log.info(
            f"[ScanService] crawl concluído site={site_id} "
            f"analyzed={result.get('pages_analyzed')} found={result.get('pages_found')} "
            f"failed={result.get('pages_failed')} avg={result.get('average_score')}"
        )

        tasks_created = 0

        # Carrega as tasks pendentes já existentes UMA vez por scan, para não
        # duplicar a cada rescan. Sem isso, cada clique em "Atualizar panorama"
        # reinseria uma task por issue ainda presente na página, inflando
        # 'Oportunidades Encontradas' sem limite a cada execução.
        existing_pending = await self.db.list_tasks(site_id, "pending")
        existing_task_keys = {
            (str(t.get("page_id")), t.get("issue_type"))
            for t in existing_pending
        }

        # Process each page
        for page_data in result["pages"]:
            page = await self.db.upsert_page(site_id, page_data["url"], {
                "status_code": page_data["status_code"],
                "title": page_data["title"],
                "meta_description": page_data["meta_description"],
                "h1": page_data["h1"],
                "issues": page_data["issues"],
                "seo_score": page_data["score"],
                "total_score": page_data["score"],
            })

            # Create tasks for each issue (pula issues que já têm task pendente)
            tasks_created += await self._create_tasks_for_issues(
                site_id=site_id,
                page_id=str(page.get("id", "")),
                page_url=page_data["url"],
                issues=page_data["issues"],
                existing_task_keys=existing_task_keys,
            )
        
        # Complete scan run
        await self.db.complete_scan_run(
            scan_id=str(scan_run["id"]),
            pages_scanned=result["pages_analyzed"],
            tasks_created=tasks_created,
            avg_score=result["average_score"],
            issues_summary=result["issues_summary"],
        )
        
        return {
            "pages_scanned": result["pages_analyzed"],
            "pages_found": result["pages_found"],
            "tasks_created": tasks_created,
            "score": result["average_score"],
            "duration_seconds": result["duration_seconds"],
            "issues_summary": result["issues_summary"],
        }
    
    async def _create_tasks_for_issues(
        self,
        site_id: str,
        page_id: str,
        page_url: str,
        issues: Dict[str, bool],
        existing_task_keys: Optional[set] = None,
    ) -> int:
        """Create tasks for detected SEO issues. Returns count of tasks created.

        existing_task_keys: set de (page_id, issue_type) com task PENDENTE já
        existente — evita duplicar a cada rescan. Passe o mesmo set entre
        chamadas (uma por página) para que as tasks recém-criadas também
        sejam consideradas dentro do mesmo scan.
        """
        existing_task_keys = existing_task_keys if existing_task_keys is not None else set()
        count = 0
        for issue_code, is_present in issues.items():
            if not is_present or issue_code not in ISSUE_CONFIG:
                continue
            key = (page_id, issue_code)
            if key in existing_task_keys:
                continue
            await self.db.create_task(
                site_id=site_id,
                page_id=page_id,
                task_type=issue_code,
                payload={"issue": issue_code, "url": page_url},
                ai_suggestion=ISSUE_CONFIG[issue_code]["message"],
            )
            existing_task_keys.add(key)
            count += 1
        return count


class TaskService:
    """Business logic for task management"""
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_supabase()
    
    async def list_tasks(self, site_id: str, status: str = None) -> List[Dict]:
        """List tasks for a site"""
        tasks = await self.db.list_tasks(site_id, status)
        pages = await self.db.list_pages(site_id)
        page_urls = {str(p["id"]): p["url"] for p in pages}
        
        # Enrich tasks with page URLs and messages
        for task in tasks:
            task["page_url"] = page_urls.get(str(task.get("page_id")), "")
            if not task.get("suggestion"):
                task["message"] = ISSUE_CONFIG.get(task.get("issue_type"), {}).get("message", "")
            else:
                task["message"] = task["suggestion"]
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a task by ID"""
        return await self.db.get_task(task_id)
    
    async def approve_task(self, task_id: str) -> Dict:
        """Approve a task"""
        return await self.db.update_task_status(task_id, "approved")
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        return await self.db.delete_task(task_id)
    
    async def update_task_with_fix(self, task_id: str, fix_result: Dict) -> Dict:
        """Update a task with a generated fix"""
        if fix_result.get("optimized"):
            return await self.db.update_task(task_id, {
                "suggestion": fix_result.get("html_code", fix_result.get("optimized")),
                "ai_generated": fix_result.get("ai_powered", False),
            })
        return await self.db.get_task(task_id)
    
    async def generate_fix(self, task_id: str) -> Dict:
        """Generate an AI fix for a task"""
        task = await self.db.get_task(task_id)
        if not task:
            raise ValueError("Task não encontrada")
        
        page = await self.db.get_page(task.get("page_id"))
        
        from app.llm_optimizer import generate_seo_fix
        result = await generate_seo_fix(
            issue_type=task.get("issue_type", task.get("type", "")),
            page_url=page.get("url", "") if page else "",
            page_title=page.get("title") if page else None,
            page_description=page.get("meta_description") if page else None,
            page_h1=page.get("h1") if page else None,
        )
        
        # Update task with the suggestion
        await self.update_task_with_fix(task_id, result)
        
        return {
            "task_id": task_id,
            "fix": result,
            "updated": True,
        }


class PageService:
    """Business logic for page management"""
    
    def __init__(self, db: SupabaseClient = None):
        self.db = db or get_supabase()
    
    async def list_pages(self, site_id: str) -> List[Dict]:
        """List pages for a site"""
        return await self.db.list_pages(site_id)
    
    async def get_page(self, page_id: str) -> Optional[Dict]:
        """Get a page by ID"""
        return await self.db.get_page(page_id)


class KeywordService:
    """Business logic for keyword extraction"""
    
    STOPWORDS = set(
        "a o os as um uma uns umas de da do das dos em no na nos nas "
        "para por com sem e ou que the an and or of to in on for with "
        "without is are be this that these those".split()
    )
    
    def extract_keywords(self, text: str, limit: int = 20) -> List[Dict]:
        """Extract keywords from text with estimated metrics"""
        import re
        words = re.findall(r"[a-zA-ZÀ-ÿ0-9]{3,}", text.lower())
        
        freq: Dict[str, int] = {}
        for w in words:
            if w not in self.STOPWORDS:
                freq[w] = freq.get(w, 0) + 1
        
        top = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        result = []
        for i, (kw, _) in enumerate(top):
            result.append({
                "keyword": kw,
                "volume": max(0, 1000 - i * 35),
                "cpc": round(max(0.0, 3.5 - i * 0.07), 2),
                "intent": "informational" if i < 7 else ("commercial" if i < 14 else "transactional"),
                "difficulty": min(90, 25 + i * 3),
                "opportunity": "high" if i < 6 else ("medium" if i < 14 else "low"),
            })
        
        return result


# Factory functions for service instances
def get_site_service(db: SupabaseClient = None) -> SiteService:
    return SiteService(db)

def get_scan_service(db: SupabaseClient = None) -> ScanService:
    return ScanService(db)

def get_task_service(db: SupabaseClient = None) -> TaskService:
    return TaskService(db)

def get_page_service(db: SupabaseClient = None) -> PageService:
    return PageService(db)

def get_keyword_service() -> KeywordService:
    return KeywordService()
