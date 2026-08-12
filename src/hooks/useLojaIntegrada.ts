import { api } from "@/lib/apiClient";
import {
  useIntegrationSeo,
  IntegrationProduct,
  IntegrationCategory,
  IntegrationProposal,
  IntegrationRollback,
  IntegrationSEOAnalysis,
} from "@/hooks/useIntegrationSeo";

// Aliases tipados da plataforma (mesmo protocolo do useNuvemshop)
export type LojaIntegradaProduct = IntegrationProduct;
export type LojaIntegradaCategory = IntegrationCategory;
export type LojaIntegradaProposal = IntegrationProposal;
export type LojaIntegradaRollback = IntegrationRollback;
export type LojaIntegradaSEOAnalysis = IntegrationSEOAnalysis;

/**
 * Hook da integração Loja Integrada — produtos e categorias, propostas de SEO
 * com IA (transparência inclusa), aplicação (SEO via recurso /v1/seo) e rollback.
 */
export function useLojaIntegrada() {
  return useIntegrationSeo(api.lojaintegrada, "lojaintegrada");
}
