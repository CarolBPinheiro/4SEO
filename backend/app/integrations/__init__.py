# Módulo de integrações
from .shopify import (
    ShopifyClient, 
    ShopifyProduct,
    ShopifyImage,
    OptimizationProposal,
    OptimizationStatus,
    RollbackRecord,
    create_shopify_client,
)
from .shopify_optimizer import (
    ShopifySEOOptimizer,
    create_shopify_optimizer,
)
from .nuvemshop import NuvemshopClient, create_nuvemshop_client

__all__ = [
    # Shopify
    "ShopifyClient",
    "ShopifyProduct",
    "ShopifyImage",
    "OptimizationProposal",
    "OptimizationStatus",
    "RollbackRecord",
    "create_shopify_client",
    "ShopifySEOOptimizer",
    "create_shopify_optimizer",
    # Nuvemshop
    "NuvemshopClient",
    "create_nuvemshop_client",
]
