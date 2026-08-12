import IntegrationAnalise from "@/components/seo/IntegrationAnalise";
import { useLojaIntegrada } from "@/hooks/useLojaIntegrada";

/**
 * Painel de análise/otimização SEO da Loja Integrada (produtos + categorias).
 * storeId = store_key retornado pelo backend no connect.
 */
export default function LojaIntegradaAnalise({ storeId, storeName }: { storeId: string; storeName?: string }) {
  const seo = useLojaIntegrada();
  return (
    <IntegrationAnalise
      seo={seo}
      storeId={storeId}
      storeName={storeName}
      platformLabel="Loja Integrada"
    />
  );
}
