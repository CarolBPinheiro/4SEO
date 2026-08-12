"""
Configuração central do modelo de IA e compatibilidade de parâmetros.

Modelos da família GPT-5 e o-series (modelos de raciocínio) têm restrições na
Chat Completions API que diferem dos modelos GPT-4o:
  - `temperature` aceita apenas o valor padrão (1) → o parâmetro é omitido;
  - `max_tokens` não é suportado → usa-se `max_completion_tokens`;
  - tokens de raciocínio consomem o orçamento de saída → aplicamos um piso de
    segurança e `reasoning_effort` para controlar custo/latência.

`completion_params()` devolve os kwargs corretos para o modelo configurado,
mantendo compatibilidade retroativa com gpt-4o-mini/gpt-4o caso AI_MODEL seja
sobrescrito via variável de ambiente.
"""
import os
import re
import json
import logging

logger = logging.getLogger(__name__)

# Modelo padrão: gpt-5-mini — melhor custo-benefício atual para SEO estruturado.
AI_MODEL = os.getenv("AI_MODEL", "gpt-5-mini")

# Esforço de raciocínio para modelos GPT-5. "minimal" = mais rápido e barato,
# adequado para reestruturação de metadados (não exige raciocínio profundo).
AI_REASONING_EFFORT = os.getenv("AI_REASONING_EFFORT", "minimal")

# Piso de tokens de saída para modelos de raciocínio: garante espaço para os
# tokens de reasoning + a resposta, evitando saídas truncadas ou vazias.
# max_completion_tokens é um teto, não uma meta — o modelo para quando conclui,
# então elevar o piso não aumenta o custo de saídas curtas.
_REASONING_TOKEN_FLOOR = 1024


def is_reasoning_model(model: str = None) -> bool:
    """True se o modelo é da família de raciocínio (GPT-5 / o1 / o3 / o4)."""
    m = (model or AI_MODEL).lower()
    return (
        m.startswith("gpt-5")
        or m.startswith("o1")
        or m.startswith("o3")
        or m.startswith("o4")
    )


def completion_params(max_output_tokens: int, temperature: float = 0.7, model: str = None) -> dict:
    """
    Retorna os kwargs de tokens/temperature compatíveis com o modelo configurado.

    Uso:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[...],
            **completion_params(2000, temperature=0.7),
        )

    - GPT-5 / o-series: max_completion_tokens (com piso) + reasoning_effort;
      temperature é omitida (apenas o default é aceito).
    - GPT-4o e afins: temperature + max_tokens (comportamento original).
    """
    model = model or AI_MODEL
    if is_reasoning_model(model):
        return {
            "max_completion_tokens": max(max_output_tokens, _REASONING_TOKEN_FLOOR),
            "reasoning_effort": AI_REASONING_EFFORT,
        }
    return {
        "max_tokens": max_output_tokens,
        "temperature": temperature,
    }


def parse_ai_json(content: str, context: str = "") -> dict:
    """
    Extrai e faz parse do primeiro objeto JSON encontrado na resposta da IA.

    Retorna {} (dict vazio) e LOGA um warning com o conteúdo bruto (truncado)
    quando não há JSON válido — sem isso, a falha fica indistinguível de "a
    IA não encontrou nada para otimizar" tanto para o usuário quanto para
    quem for investigar depois. Cenário real com gpt-5-mini (modelo de
    raciocínio): se os tokens de reasoning consomem todo o
    max_completion_tokens, `content` pode vir vazio com finish_reason='length'.

    `context` é um rótulo curto (ex.: "produto VTEX", "categoria Loja
    Integrada") incluído no log para facilitar diagnóstico.
    """
    if not content:
        logger.warning(f"[AI parse] resposta vazia da IA ({context}) — nenhuma proposta será gerada")
        return {}

    match = re.search(r'\{[\s\S]*\}', content)
    if not match:
        logger.warning(f"[AI parse] nenhum JSON encontrado na resposta da IA ({context}): {content[:200]!r}")
        return {}

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        logger.warning(f"[AI parse] JSON malformado na resposta da IA ({context}): {e} — conteúdo: {match.group()[:200]!r}")
        return {}
