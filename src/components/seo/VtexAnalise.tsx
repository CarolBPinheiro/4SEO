import IntegrationAnalise from "@/components/seo/IntegrationAnalise";
import { useVtex } from "@/hooks/useVtex";

/**
 * Painel de análise/otimização SEO da VTEX (produtos + categorias).
 * storeId = account name da conta VTEX.
 */
export default function VtexAnalise({ storeId, storeName }: { storeId: string; storeName?: string }) {
  const seo = useVtex();
  return (
    <IntegrationAnalise
      seo={seo}
      storeId={storeId}
      storeName={storeName}
      platformLabel="VTEX"
    />
  );
}
