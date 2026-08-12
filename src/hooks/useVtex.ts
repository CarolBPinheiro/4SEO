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
export type VtexProduct = IntegrationProduct;
export type VtexCategory = IntegrationCategory;
export type VtexProposal = IntegrationProposal;
export type VtexRollback = IntegrationRollback;
export type VtexSEOAnalysis = IntegrationSEOAnalysis;

/**
 * Hook da integração VTEX — produtos e categorias, propostas de SEO com IA
 * (transparência inclusa), aplicação com read-modify-write e rollback.
 */
export function useVtex() {
  return useIntegrationSeo(api.vtex, "vtex");
}
