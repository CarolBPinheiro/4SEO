"""
Regressão: DELETE /api/integrations/disconnect
engolia silenciosamente uma falha em delete_integration (só logava um
warning) e sempre respondia {"ok": True, "message": "Loja desconectada"} -
mesmo quando as credenciais salvas em user_integrations continuavam lá.

Isso é exatamente o mecanismo do "loop de reconexão" relatado pelo usuário:
GET /api/integrations/status restaura o site a partir de user_integrations
sempre que encontra um access_token salvo e nenhum site correspondente -
então, se delete_integration falhasse (ex.: falha transitória de rede/DB),
a loja "desconectada" reaparecia sozinha alguns segundos depois, no próximo
refresh de status.

Cobre:
- Sucesso de primeira: delete_integration roda uma vez, sem retry.
- Falha transitória: delete_integration falha algumas vezes e se recupera
  no retry - ainda reporta sucesso (não regride o caso comum).
- Falha persistente: delete_integration falha em todas as tentativas -
  NÃO reporta sucesso (levanta HTTPException) em vez de mentir.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException


def _mock_db(sites=None, integration=None):
    db = MagicMock()
    db.list_sites_for_user = AsyncMock(return_value=sites or [])
    db.get_integration = AsyncMock(return_value=integration)
    db.delete_site = AsyncMock(return_value=True)
    db.delete_integration = AsyncMock(return_value=True)
    return db


SITE = {"id": "site1", "base_url": "https://loja.myshopify.com", "platform": "shopify", "store_id": ""}
INTEGRATION = {"platform": "shopify", "store_url": "https://loja.myshopify.com", "access_token": "tok"}


class TestIntegrationsDisconnect:

    @pytest.mark.asyncio
    async def test_success_on_first_try_no_retry(self):
        from app.main import integrations_disconnect

        db = _mock_db(sites=[SITE], integration=INTEGRATION)

        with patch("app.supabase_client.get_supabase_for_user", return_value=db):
            result = await integrations_disconnect(user={"user_id": "u1", "token": "t"})

        assert result["ok"] is True
        db.delete_site.assert_awaited_once_with("site1")
        assert db.delete_integration.await_count == 1

    @pytest.mark.asyncio
    async def test_recovers_after_transient_failures(self):
        """Falha transitória (ex.: rede/DB) nas 2 primeiras tentativas, sucesso na 3ª —
        ainda reporta sucesso: não regride o caso comum (a maioria das falhas é transitória)."""
        from app.main import integrations_disconnect

        db = _mock_db(sites=[SITE], integration=INTEGRATION)
        db.delete_integration = AsyncMock(
            side_effect=[Exception("timeout"), Exception("timeout"), True]
        )

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch("app.main.asyncio.sleep", new_callable=AsyncMock):
            result = await integrations_disconnect(user={"user_id": "u1", "token": "t"})

        assert result["ok"] is True
        assert db.delete_integration.await_count == 3

    @pytest.mark.asyncio
    async def test_persistent_failure_does_not_report_success(self):
        """delete_integration falha em TODAS as tentativas: o endpoint não pode
        mentir 'Loja desconectada' com a credencial ainda viva (isso é o que
        causa a reconexão fantasma alguns segundos depois)."""
        from app.main import integrations_disconnect

        db = _mock_db(sites=[SITE], integration=INTEGRATION)
        db.delete_integration = AsyncMock(side_effect=Exception("db indisponível"))

        with patch("app.supabase_client.get_supabase_for_user", return_value=db), \
             patch("app.main.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(HTTPException) as exc:
                await integrations_disconnect(user={"user_id": "u1", "token": "t"})

        assert exc.value.status_code == 500
        assert db.delete_integration.await_count == 3
        # O site já tinha sido removido antes do retry de delete_integration começar
        db.delete_site.assert_awaited_once_with("site1")
