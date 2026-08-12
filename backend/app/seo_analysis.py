"""
Centralized SEO analysis logic for SiteCan backend.
Extracted and unified from crawler.py and main.py.
"""
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import re

# Penalties and messages for each SEO issue (mensagens em português)
ISSUE_CONFIG = {
    # Título
    "missing_title": {"penalty": 20, "message": "Título da página não definido - adicione uma tag <title> descritiva"},
    "title_length": {"penalty": 8, "message": "Tamanho do título inadequado - ajuste para 30-60 caracteres"},  # legado (dados escaneados antes da separação curto/longo)
    "title_too_short": {"penalty": 8, "message": "Título muito curto - abaixo do mínimo perde contexto e cliques; ajuste para 30-60 caracteres"},
    "title_too_long": {"penalty": 8, "message": "Título muito longo - o Google trunca títulos acima de 60 caracteres"},
    # Meta Description
    "missing_meta_description": {"penalty": 15, "message": "Meta descrição não definida - esse texto aparece nos resultados do Google"},
    "meta_description_length": {"penalty": 5, "message": "Tamanho da meta descrição inadequado - ajuste para 120-160 caracteres"},  # legado
    "meta_description_short": {"penalty": 5, "message": "Meta descrição muito curta - abaixo do mínimo recomendado; ajuste para 120-160 caracteres"},
    "meta_description_long": {"penalty": 5, "message": "Meta descrição muito longa - o Google trunca acima de 160 caracteres"},
    # Headings
    "missing_h1": {"penalty": 15, "message": "Título principal (H1) não encontrado - essencial para o Google entender a página"},
    "multiple_h1": {"penalty": 5, "message": "Múltiplos títulos H1 na página - mantenha apenas um por página"},
    "missing_h2": {"penalty": 3, "message": "Subtítulos (H2) não encontrados - organize o conteúdo com subtítulos"},
    # Technical SEO
    "missing_canonical": {"penalty": 5, "message": "Link canônico não definido - evita penalizações por conteúdo duplicado"},
    "noindex_detected": {"penalty": 25, "message": "ATENCAO: Página bloqueada para indexação - não aparecerá no Google!"},
    # Imagens
    "missing_img_alt": {"penalty": 8, "message": "Imagens sem descrição alternativa - prejudica acessibilidade e SEO"},
    # Links
    "few_internal_links": {"penalty": 5, "message": "Poucos links internos - ajude o Google a descobrir outras páginas"},
    # Social / Rich Snippets
    "missing_og_tags": {"penalty": 5, "message": "Tags de redes sociais ausentes - melhore a aparência ao compartilhar"},
    "missing_og_image": {"penalty": 3, "message": "Imagem para compartilhamento não definida - defina uma imagem atraente"},
    "missing_schema": {"penalty": 5, "message": "Dados estruturados (Schema.org) ausentes - perca de rich snippets no Google"},
}

# Classificação de impacto para cada issue
# Alto = afeta diretamente rankeamento/indexação
# Médio = afeta qualidade mas não bloqueia indexação
# Baixo = melhorias finas / semânticas
ISSUE_IMPACT = {
    # ALTO — Crítico para indexação e rankeamento
    "missing_title": "alto",
    "missing_meta_description": "alto",
    "noindex_detected": "alto",
    "title_too_short": "alto",          # spec: título abaixo do mínimo = impacto alto
    "meta_description_short": "alto",   # spec: descrição abaixo do mínimo = impacto alto
    # MÉDIO — Problemas estruturais relevantes
    "title_length": "medio",           # legado (dados antigos, sem distinção curto/longo)
    "meta_description_length": "medio",  # legado
    "title_too_long": "medio",         # tamanho inadequado (excesso) = médio
    "meta_description_long": "medio",
    "missing_h1": "medio",
    "multiple_h1": "medio",
    "missing_canonical": "medio",
    "missing_schema": "medio",
    "missing_og_tags": "medio",
    # BAIXO — Melhorias semânticas e acessibilidade
    "missing_h2": "baixo",
    "missing_img_alt": "baixo",
    "missing_og_image": "baixo",
    "few_internal_links": "baixo",
}

# Labels amigáveis para cada issue (usados nos filtros)
ISSUE_LABEL = {
    "missing_title": "Sem Título",
    "title_length": "Título Curto/Longo",  # legado
    "title_too_short": "Título Curto",
    "title_too_long": "Título Longo",
    "missing_meta_description": "Sem Meta Descrição",
    "meta_description_length": "Descrição Curta/Longa",  # legado
    "meta_description_short": "Descrição Curta",
    "meta_description_long": "Descrição Longa",
    "missing_h1": "Sem H1",
    "multiple_h1": "Múltiplos H1",
    "missing_h2": "Sem H2",
    "missing_canonical": "Sem Canonical",
    "noindex_detected": "Bloqueado (noindex)",
    "missing_img_alt": "Imagens sem Alt",
    "few_internal_links": "Poucos Links Internos",
    "missing_og_tags": "Sem Open Graph",
    "missing_og_image": "Sem Imagem OG",
    "missing_schema": "Sem Schema.org",
}

def analyze_seo_html(html: str, base_url: str, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Central SEO analysis logic. Returns issues and score for a given HTML.
    """
    soup = BeautifulSoup(html, "html.parser")
    issues: Dict[str, bool] = {}
    score = 100

    # Title
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    issues["missing_title"] = not bool(title)
    if issues["missing_title"]:
        score -= ISSUE_CONFIG["missing_title"]["penalty"]
    elif len(title) < 30:
        issues["title_too_short"] = True
        score -= ISSUE_CONFIG["title_too_short"]["penalty"]
    elif len(title) > 60:
        issues["title_too_long"] = True
        score -= ISSUE_CONFIG["title_too_long"]["penalty"]

    # Meta Description
    meta_desc = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = meta_desc.get("content", "").strip() if meta_desc else None
    issues["missing_meta_description"] = not bool(description)
    if issues["missing_meta_description"]:
        score -= ISSUE_CONFIG["missing_meta_description"]["penalty"]
    elif len(description) < 70:
        issues["meta_description_short"] = True
        score -= ISSUE_CONFIG["meta_description_short"]["penalty"]
    elif len(description) > 160:
        issues["meta_description_long"] = True
        score -= ISSUE_CONFIG["meta_description_long"]["penalty"]

    # H1
    h1_tags = soup.find_all("h1")
    h1_text = h1_tags[0].get_text(strip=True) if h1_tags else None
    issues["missing_h1"] = len(h1_tags) == 0
    issues["multiple_h1"] = len(h1_tags) > 1
    if issues["missing_h1"]:
        score -= ISSUE_CONFIG["missing_h1"]["penalty"]
    if issues["multiple_h1"]:
        score -= ISSUE_CONFIG["multiple_h1"]["penalty"]

    # H2
    h2_tags = soup.find_all("h2")
    issues["missing_h2"] = len(h2_tags) == 0
    if issues["missing_h2"]:
        score -= ISSUE_CONFIG["missing_h2"]["penalty"]

    # Canonical
    canonical = soup.find("link", rel=lambda x: x and "canonical" in str(x).lower())
    issues["missing_canonical"] = not canonical or not canonical.get("href")
    if issues["missing_canonical"]:
        score -= ISSUE_CONFIG["missing_canonical"]["penalty"]

    # Noindex
    robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    issues["noindex_detected"] = bool(robots and "noindex" in (robots.get("content", "").lower()))
    if issues["noindex_detected"]:
        score -= ISSUE_CONFIG["noindex_detected"]["penalty"]

    # Images
    imgs = soup.find_all("img")
    images_without_alt = [img for img in imgs if not (img.get("alt") or "").strip()]
    issues["missing_img_alt"] = len(images_without_alt) > 0
    if issues["missing_img_alt"]:
        score -= ISSUE_CONFIG["missing_img_alt"]["penalty"]

    # Internal Links
    links = [a.get("href") for a in soup.find_all("a") if a.get("href")]
    internal_links = []
    if base_url:
        from urllib.parse import urlparse, urljoin
        parsed_base = urlparse(base_url)
        for href in links:
            if not href.startswith(("#", "mailto:", "tel:")):
                abs_url = urljoin(base_url, href)
                if urlparse(abs_url).netloc == parsed_base.netloc:
                    internal_links.append(href)
    elif domain:
        for href in links:
            if href.startswith("/") or (domain and domain in href):
                internal_links.append(href)
    issues["few_internal_links"] = len(internal_links) < 3
    if issues["few_internal_links"]:
        score -= ISSUE_CONFIG["few_internal_links"]["penalty"]

    # Open Graph
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_image = soup.find("meta", property="og:image")
    issues["missing_og_tags"] = not (og_title and og_desc)
    issues["missing_og_image"] = not og_image
    if issues["missing_og_tags"]:
        score -= ISSUE_CONFIG["missing_og_tags"]["penalty"]
    if issues["missing_og_image"]:
        score -= ISSUE_CONFIG["missing_og_image"]["penalty"]

    # Schema.org
    schema_scripts = soup.find_all("script", type="application/ld+json")
    issues["missing_schema"] = len(schema_scripts) == 0
    if issues["missing_schema"]:
        score -= ISSUE_CONFIG["missing_schema"]["penalty"]

    return {
        "title": title,
        "meta_description": description,
        "h1": h1_text,
        "h2_count": len(h2_tags),
        "images_count": len(imgs),
        "images_without_alt": len(images_without_alt),
        "internal_links_count": len(internal_links),
        "has_canonical": bool(canonical),
        "has_schema": bool(schema_scripts),
        "has_og_tags": bool(og_title and og_desc),
        "issues": {k: v for k, v in issues.items() if v},
        "all_issues": issues,
        "score": max(0, score),
    }
