"""
Camada de validação pós-geração da IA.
Compara título original vs sugerido e gera metadados de transparência.
NÃO chama IA — apenas faz string matching e comparação com dados estruturados.
"""
from typing import Optional, Dict, Any, List


def validar_atributos_descritivos(
    titulo_original: Optional[str],
    titulo_sugerido: str,
    atributos_produto: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Verifica se o título sugerido incorporou atributos descritivos
    (material, cor, gênero, etc.) que estavam ausentes no título original.
    """
    atributos = atributos_produto or []
    titulo_old = (titulo_original or "").lower()
    titulo_new = (titulo_sugerido or "").lower()

    encontrados = []
    seen = set()
    for attr in atributos:
        attr_lower = attr.lower().strip()
        if not attr_lower or attr_lower in seen:
            continue
        seen.add(attr_lower)  # evita contar duplicatas
        if attr_lower in titulo_new and attr_lower not in titulo_old:
            encontrados.append(attr)

    if encontrados:
        return {
            "status": "atributos_identificados",
            "atributos": encontrados,
            "tag": "✓ Atributo Identificado",
            "descricao": f"O título agora inclui: {', '.join(encontrados)}",
        }
    return {
        "status": "sem_atributos_novos",
        "atributos": [],
        "tag": "Sem atributo descritivo",
        "descricao": "Nenhum atributo novo identificado no título",
    }


def calcular_cobertura_semantica(
    titulo_original: Optional[str],
    titulo_sugerido: str,
    keywords_estrategicas: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Compara quantas keywords estratégicas (da SearchAPI) foram incorporadas
    no título sugerido que não estavam no original.

    Se 2+ keywords novas → selo 🔥 Melhor Cobertura Semântica
    """
    keywords = keywords_estrategicas or []
    titulo_old = (titulo_original or "").lower()
    titulo_new = (titulo_sugerido or "").lower()

    incorporadas = []
    seen = set()
    for kw in keywords:
        kw_lower = kw.lower().strip()
        if not kw_lower or kw_lower in seen:
            continue
        seen.add(kw_lower)  # evita contar a mesma keyword mais de uma vez
        if kw_lower in titulo_new and kw_lower not in titulo_old:
            incorporadas.append(kw)

    if len(incorporadas) >= 2:
        return {
            "status": "melhor_cobertura",
            "total": len(incorporadas),
            "keywords_incorporadas": incorporadas,
            "tag": "🔥 Melhor Cobertura Semântica",
            "descricao": f"+{len(incorporadas)} palavras-chave estratégicas incorporadas: {', '.join(incorporadas[:3])}",
        }
    elif len(incorporadas) == 1:
        return {
            "status": "cobertura_parcial",
            "total": 1,
            "keywords_incorporadas": incorporadas,
            "tag": "Melhoria detectada",
            "descricao": f"+1 palavra-chave incorporada: {incorporadas[0]}",
        }
    return {
        "status": "sem_melhoria_detectada",
        "total": 0,
        "keywords_incorporadas": [],
        "tag": "",
        "descricao": "",
    }
