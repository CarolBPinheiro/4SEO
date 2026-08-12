"""Tests for product_diagnosis (heuristic + AI normalize + options mapping)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestHeuristicDiagnosis:
    def test_new_sparse_product_has_dynamic_issues_and_justification(self):
        from app.product_diagnosis import heuristic_diagnosis

        result = heuristic_diagnosis({
            "title": "Jaqueta de couro",
            "description": "Curta",
            "seo_title": "",
            "seo_description": "",
            "tags": "",
            "images_without_alt": 0,
        })

        assert 0 <= result["score"] <= 100
        assert result["score_justification"]
        assert len(result["issues"]) >= 3
        assert all("why" in i and "impact" in i and "recommendation" in i for i in result["issues"])
        assert "seo_title" in result["recommended_actions"]
        assert result["source"] == "heuristic"
        # Não deve ser o checklist engessado de recommendations fixas
        assert not any("Ao clicar" in (r or "") for r in result["recommendations"])

    def test_complete_product_scores_high(self):
        from app.product_diagnosis import heuristic_diagnosis

        result = heuristic_diagnosis({
            "title": "Jaqueta de Couro Feminina Marrom com Forro M",
            "description": "Jaqueta de couro legítimo feminina na cor marrom, forro interno macio, zíper frontal e bolsos laterais. Ideal para meia-estação. Composição 100% couro bovino. Disponível nos tamanhos P ao GG.",
            "seo_title": "Jaqueta Couro Feminina Marrom | Couro Legítimo",
            "seo_description": "Compre jaqueta de couro feminina marrom com forro macio. Couro legítimo, zíper e bolsos. Frete para todo o Brasil.",
            "tags": "jaqueta, couro, feminina, marrom",
            "images_without_alt": 0,
        })

        assert result["score"] >= 80
        assert result["issues"] == [] or all(i["severity"] != "critical" for i in result["issues"])


class TestActionsToOptions:
    def test_maps_actions(self):
        from app.product_diagnosis import actions_to_optimize_options

        opts = actions_to_optimize_options(["seo_title", "tags"])
        assert opts["optimize_seo_title"] is True
        assert opts["generate_tags"] is True
        assert opts["optimize_title"] is False
        assert opts["optimize_description"] is False

    def test_empty_falls_back_to_core(self):
        from app.product_diagnosis import actions_to_optimize_options

        opts = actions_to_optimize_options([])
        assert opts["optimize_title"] is True
        assert opts["optimize_seo_title"] is True


class TestDiagnoseProductAi:
    @pytest.mark.asyncio
    async def test_falls_back_without_client(self):
        from app.product_diagnosis import diagnose_product

        result = await diagnose_product({"title": "X", "description": ""}, ai_client=None)
        assert result["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_uses_ai_json_when_available(self):
        from app.product_diagnosis import diagnose_product

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
          "score": 42,
          "score_justification": "Produto incompleto com oportunidades claras de SEO.",
          "summary": "3 problemas",
          "issues": [
            {
              "type": "weak_title",
              "title": "Título genérico",
              "severity": "warning",
              "why": "Não descreve atributos",
              "impact": "Baixo CTR",
              "recommendation": "Incluir material e público",
              "suggested_fields": ["title", "seo_title"]
            }
          ],
          "opportunities": ["Explorar long-tail de couro feminino"],
          "recommended_actions": ["title", "seo_title", "seo_description"]
        }"""
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.product_diagnosis.completion_params", return_value={}):
            result = await diagnose_product(
                {"title": "Jaqueta", "description": "x" * 50},
                ai_client=mock_client,
                platform="Nuvemshop",
            )

        assert result["source"] == "ai"
        assert result["score"] == 42
        assert "incompleto" in result["score_justification"].lower() or "oportunidades" in result["score_justification"].lower()
        assert result["issues"][0]["title"] == "Título genérico"
        assert "seo_title" in result["recommended_actions"]
