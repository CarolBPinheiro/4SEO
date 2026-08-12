"""
Regressão: quando a resposta da IA não tinha JSON
válido (comum em modelos de raciocínio como gpt-5-mini, se os tokens de
reasoning consomem todo o max_completion_tokens e content vem vazio), os 4
optimizers de plataforma (Shopify/Nuvemshop/VTEX/Loja Integrada) simplesmente
retornavam lista vazia sem NENHUM log — indistinguível de "a IA não encontrou
nada para otimizar" tanto para o usuário quanto para quem for investigar.

Cobre o novo helper compartilhado app.ai_config.parse_ai_json e o
comportamento (log + retorno vazio, nunca exceção) nos 4 optimizers.
"""
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.ai_config import parse_ai_json


class TestParseAiJson:

    def test_valid_json_object(self):
        result = parse_ai_json('{"seo_title": {"value": "Titulo Novo"}}', "teste")
        assert result == {"seo_title": {"value": "Titulo Novo"}}

    def test_json_embedded_in_prose(self):
        """A IA às vezes envolve o JSON em texto explicativo — regex deve extrair."""
        content = 'Aqui está o resultado:\n{"name": {"value": "X"}}\nEspero que ajude!'
        result = parse_ai_json(content, "teste")
        assert result == {"name": {"value": "X"}}

    def test_empty_content_returns_empty_dict_and_logs(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = parse_ai_json("", "produto X")
        assert result == {}
        assert "produto X" in caplog.text
        assert "vazia" in caplog.text.lower()

    def test_none_content_returns_empty_dict(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = parse_ai_json(None, "produto X")
        assert result == {}

    def test_no_json_in_content_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            result = parse_ai_json("Desculpe, não consegui gerar uma sugestão.", "categoria Y")
        assert result == {}
        assert "categoria Y" in caplog.text
        assert "nenhum json" in caplog.text.lower()

    def test_malformed_json_logs_warning(self, caplog):
        # Chaves balanceadas (regex encontra o span), mas sintaxe JSON inválida
        # dentro (vírgula sobrando) -> json.loads falha após o match.
        with caplog.at_level(logging.WARNING):
            result = parse_ai_json('{"seo_title": {"value": "ok",}}', "produto Z")
        assert result == {}
        assert "produto Z" in caplog.text
        assert "malformado" in caplog.text.lower()

    def test_never_raises(self):
        """Nunca deve lançar, mesmo com entradas estranhas."""
        assert parse_ai_json("}{", "x") == {}
        assert parse_ai_json("   ", "x") == {}


def _mock_ai_response(content: str):
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


class TestOptimizersDegradeGracefullyOnEmptyAiResponse:
    """Para cada plataforma: resposta da IA sem JSON válido -> [] + warning logado
    (nunca uma exceção, nunca silêncio total)."""

    @pytest.mark.asyncio
    async def test_vtex_product(self, caplog):
        from app.integrations.vtex import VtexClient
        from app.integrations.vtex_optimizer import VtexSEOOptimizer
        from app.integrations.vtex import VtexProduct

        client = VtexClient("loja", "k", "t")
        optimizer = VtexSEOOptimizer(client)
        client.get_product = AsyncMock(return_value=VtexProduct(id=1, name="Produto"))
        optimizer._fetch_serp_context = AsyncMock(return_value="")
        optimizer.ai_client = MagicMock()
        optimizer.ai_client.chat.completions.create = AsyncMock(return_value=_mock_ai_response(""))

        from unittest.mock import patch
        with patch("app.data_enrichment.enrich_product_context", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"atributos_extraidos": [], "keywords_mercado": [], "segmento": ""}
            with caplog.at_level(logging.WARNING):
                proposals = await optimizer.optimize_product(1)

        assert proposals == []
        assert "produto vtex" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_lojaintegrada_product(self, caplog):
        from app.integrations.lojaintegrada import LojaIntegradaClient, LojaIntegradaProduct
        from app.integrations.lojaintegrada_optimizer import LojaIntegradaSEOOptimizer
        from unittest.mock import patch

        client = LojaIntegradaClient("chave", "app")
        optimizer = LojaIntegradaSEOOptimizer(client)
        client.get_product = AsyncMock(return_value=LojaIntegradaProduct(id=1, name="Produto"))
        optimizer._fetch_serp_context = AsyncMock(return_value="")
        optimizer.ai_client = MagicMock()
        optimizer.ai_client.chat.completions.create = AsyncMock(
            return_value=_mock_ai_response("não é json")
        )

        with patch("app.data_enrichment.enrich_product_context", new_callable=AsyncMock) as mock_enrich:
            mock_enrich.return_value = {"atributos_extraidos": [], "keywords_mercado": [], "segmento": ""}
            with caplog.at_level(logging.WARNING):
                proposals = await optimizer.optimize_product(1)

        assert proposals == []
        assert "loja integrada" in caplog.text.lower()
