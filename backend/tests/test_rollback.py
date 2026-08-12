"""
Tests for rollback_direct methods in Shopify and Nuvemshop clients.
Verifies that rollback works from a record dict (surviving cold starts).
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def shopify_client():
    from app.integrations.shopify import ShopifyClient
    client = ShopifyClient(shop_url="test-shop.myshopify.com", access_token="token")
    client._request = AsyncMock(return_value={})
    return client


@pytest.mark.asyncio
async def test_shopify_rollback_direct_product_title(shopify_client):
    record = {
        "id": "r1",
        "product_id": 123,
        "content_type": "product",
        "optimization_type": "title",
        "field_name": "title",
        "original_value": "Original Title",
        "new_value": "New Title",
    }
    result = await shopify_client.rollback_direct(record)
    assert result["rolled_back"] == 1
    shopify_client._request.assert_called_once()
    args, kwargs = shopify_client._request.call_args
    assert args[0] == "PUT"
    assert "/products/123.json" in args[1]
    assert kwargs["data"] == {"product": {"title": "Original Title"}}


@pytest.mark.asyncio
async def test_shopify_rollback_direct_product_seo_description(shopify_client):
    record = {
        "id": "r2",
        "product_id": 555,
        "content_type": "product",
        "optimization_type": "seo_description",
        "field_name": "description_tag",
        "original_value": "old meta",
        "new_value": "new meta",
    }
    await shopify_client.rollback_direct(record)
    args, kwargs = shopify_client._request.call_args
    assert args[0] == "POST"
    assert "/products/555/metafields.json" in args[1]
    metafield = kwargs["data"]["metafield"]
    assert metafield["key"] == "description_tag"
    assert metafield["value"] == "old meta"


@pytest.mark.asyncio
async def test_shopify_rollback_direct_image_alt(shopify_client):
    record = {
        "id": "r3",
        "product_id": 100,
        "image_id": 999,
        "content_type": "product",
        "optimization_type": "image_alt",
        "field_name": "image_alt_999",
        "original_value": "old alt",
        "new_value": "new alt",
    }
    await shopify_client.rollback_direct(record)
    args, kwargs = shopify_client._request.call_args
    assert args[0] == "PUT"
    assert "/products/100/images/999.json" in args[1]
    assert kwargs["data"] == {"image": {"id": 999, "alt": "old alt"}}


@pytest.mark.asyncio
async def test_shopify_rollback_direct_page(shopify_client):
    record = {
        "id": "r4",
        "product_id": 42,
        "content_type": "page",
        "optimization_type": "page_title",
        "field_name": "title",
        "original_value": "Old page title",
        "new_value": "New page title",
    }
    await shopify_client.rollback_direct(record)
    args, kwargs = shopify_client._request.call_args
    assert args[0] == "PUT"
    assert "/pages/42.json" in args[1]
    assert kwargs["data"] == {"page": {"title": "Old page title"}}


@pytest.mark.asyncio
async def test_shopify_rollback_direct_article_with_blog_id(shopify_client):
    record = {
        "id": "r5",
        "product_id": 200,
        "blog_id": 10,
        "content_type": "article",
        "optimization_type": "article_title",
        "field_name": "title",
        "original_value": "Old article",
        "new_value": "New article",
    }
    await shopify_client.rollback_direct(record)
    args, kwargs = shopify_client._request.call_args
    assert args[0] == "PUT"
    assert "/blogs/10/articles/200.json" in args[1]
    assert kwargs["data"] == {"article": {"title": "Old article"}}


@pytest.mark.asyncio
async def test_shopify_rollback_direct_missing_product_id_raises(shopify_client):
    with pytest.raises(ValueError, match="product_id"):
        await shopify_client.rollback_direct({"content_type": "product", "optimization_type": "title"})


@pytest.mark.asyncio
async def test_shopify_rollback_direct_article_missing_blog_id_discovers(shopify_client):
    # When blog_id missing, it tries to discover via blogs list
    async def mock_request(method, endpoint, **kwargs):
        if endpoint == "/blogs.json":
            return {"blogs": [{"id": 77}]}
        if method == "GET" and "/blogs/77/articles/500.json" in endpoint:
            return {"article": {"id": 500}}
        return {}
    shopify_client._request = AsyncMock(side_effect=mock_request)
    record = {
        "product_id": 500,
        "content_type": "article",
        "optimization_type": "article_content",
        "original_value": "old body",
    }
    await shopify_client.rollback_direct(record)
    # Last call should update the article
    last = shopify_client._request.call_args_list[-1]
    assert last.args[0] == "PUT"
    assert "/blogs/77/articles/500.json" in last.args[1]


@pytest.fixture
def nuvemshop_client():
    from app.integrations.nuvemshop import NuvemshopClient
    client = NuvemshopClient(store_id="9999", access_token="t")
    client.update_product = AsyncMock(return_value={})
    client.update_category = AsyncMock(return_value={})
    client.update_page = AsyncMock(return_value={})
    client.update_blog_post = AsyncMock(return_value={})
    return client


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_product_title(nuvemshop_client):
    record = {
        "id": "r1",
        "product_id": 123,
        "content_type": "product",
        "optimization_type": "title",
        "field_name": "name",
        "original_value": "Old",
        "new_value": "New",
    }
    await nuvemshop_client.rollback_direct(record)
    nuvemshop_client.update_product.assert_called_once_with(123, {"name": "Old"})


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_product_seo_description(nuvemshop_client):
    record = {
        "product_id": 77,
        "content_type": "product",
        "optimization_type": "seo_description",
        "field_name": "seo_description",
        "original_value": "old meta",
    }
    await nuvemshop_client.rollback_direct(record)
    nuvemshop_client.update_product.assert_called_once_with(77, {"seo_description": "old meta"})


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_category(nuvemshop_client):
    record = {
        "product_id": 44,
        "content_type": "category",
        "optimization_type": "category_seo_title",
        "original_value": "Old Cat",
    }
    await nuvemshop_client.rollback_direct(record)
    nuvemshop_client.update_category.assert_called_once_with(44, {"seo_title": "Old Cat"})


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_page(nuvemshop_client):
    record = {
        "product_id": 88,
        "content_type": "page",
        "optimization_type": "page_content",
        "original_value": "old content",
    }
    await nuvemshop_client.rollback_direct(record)
    nuvemshop_client.update_page.assert_called_once_with(88, {"content": "old content"})


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_blog_with_blog_id(nuvemshop_client):
    record = {
        "product_id": 500,
        "blog_id": 10,
        "content_type": "blog",
        "optimization_type": "blog_title",
        "original_value": "Old Post",
    }
    await nuvemshop_client.rollback_direct(record)
    nuvemshop_client.update_blog_post.assert_called_once_with(10, 500, {"title": "Old Post"})


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_blog_without_blog_id_raises(nuvemshop_client):
    record = {
        "product_id": 500,
        "content_type": "blog",
        "optimization_type": "blog_title",
        "original_value": "Old Post",
    }
    with pytest.raises(ValueError, match="blog_id"):
        await nuvemshop_client.rollback_direct(record)


@pytest.mark.asyncio
async def test_nuvemshop_rollback_direct_missing_product_id_raises(nuvemshop_client):
    with pytest.raises(ValueError, match="product_id"):
        await nuvemshop_client.rollback_direct({"content_type": "product", "optimization_type": "title"})


@pytest.mark.asyncio
async def test_nuvemshop_apply_proposals_direct_returns_rollback_records():
    from app.integrations.nuvemshop import NuvemshopClient
    client = NuvemshopClient(store_id="1234", access_token="t")
    client.update_product = AsyncMock(return_value={})
    
    proposals = [{
        "id": "p1",
        "product_id": 10,
        "optimization_type": "title",
        "field_name": "name",
        "original_value": "Old",
        "proposed_value": "New",
        "content_type": "product",
    }]
    
    result = await client.apply_proposals_direct(proposals)
    assert result["applied"] == 1
    assert "rollback_records" in result
    assert len(result["rollback_records"]) == 1
    rec = result["rollback_records"][0]
    assert rec["product_id"] == 10
    assert rec["original_value"] == "Old"
    assert rec["new_value"] == "New"
    assert rec["content_type"] == "product"
    assert rec["optimization_type"] == "title"
    assert "id" in rec
    assert "applied_at" in rec


@pytest.mark.asyncio
async def test_shopify_apply_proposals_direct_returns_rollback_records():
    from app.integrations.shopify import ShopifyClient
    client = ShopifyClient(shop_url="test.myshopify.com", access_token="t")
    client._request = AsyncMock(return_value={})
    
    proposals = [{
        "id": "p1",
        "product_id": 42,
        "optimization_type": "title",
        "field_name": "title",
        "original_value": "Old",
        "proposed_value": "New",
        "content_type": "product",
    }]
    
    result = await client.apply_proposals_direct(proposals)
    assert result["applied"] == 1
    assert "rollback_records" in result
    assert len(result["rollback_records"]) == 1
    rec = result["rollback_records"][0]
    assert rec["product_id"] == 42
    assert rec["original_value"] == "Old"
    assert rec["optimization_type"] == "title"


@pytest.mark.asyncio
async def test_nuvemshop_apply_then_rollback_direct_roundtrip():
    """Simula fluxo completo: aplicar proposta -> receber record -> usar para rollback"""
    from app.integrations.nuvemshop import NuvemshopClient
    client = NuvemshopClient(store_id="1234", access_token="t")
    update_calls = []
    
    async def mock_update_product(product_id, data):
        update_calls.append((product_id, dict(data)))
        return {}
    
    client.update_product = AsyncMock(side_effect=mock_update_product)
    
    # 1. Aplicar
    proposals = [{
        "product_id": 10,
        "optimization_type": "seo_title",
        "field_name": "seo_title",
        "original_value": "Old SEO",
        "proposed_value": "New SEO",
        "content_type": "product",
    }]
    apply_result = await client.apply_proposals_direct(proposals)
    assert apply_result["applied"] == 1
    record = apply_result["rollback_records"][0]
    # Apply should have sent the NEW value
    assert update_calls[0] == (10, {"seo_title": "New SEO"})
    
    # 2. Reverter usando apenas o record (simula cold start: cliente recriado)
    new_client = NuvemshopClient(store_id="1234", access_token="t")
    new_update_calls = []
    async def mock_update_2(product_id, data):
        new_update_calls.append((product_id, dict(data)))
        return {}
    new_client.update_product = AsyncMock(side_effect=mock_update_2)
    
    await new_client.rollback_direct(record)
    assert new_update_calls[0] == (10, {"seo_title": "Old SEO"})
