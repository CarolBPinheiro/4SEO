/**
 * Não existe CMS de categorias/conteúdo no 4SEO.
 * Categorias = dados da loja (APIs ecommerce) ou áreas do produto.
 */
export default function AdminContentPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Conteúdo e categorias</h1>
        <p className="text-sm text-zinc-400">Escopo alinhado à arquitetura existente</p>
      </div>

      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-5 text-sm leading-relaxed text-amber-100/90">
        <p className="font-semibold text-amber-200">CMS não aplicável neste produto</p>
        <p className="mt-3">
          As “categorias” da plataforma são entidades das lojas conectadas (Nuvemshop,
          Shopify, VTEX, Loja Integrada) e áreas de produto (Termos, Análise, Histórico…),
          não um catálogo editorial no banco.
        </p>
        <p className="mt-3">
          Por isso o painel admin <strong>não</strong> cria um CMS paralelo. Gerencie
          usuários, assinaturas e saúde por aqui; o conteúdo de SEO continua nas
          integrações do app.
        </p>
      </div>
    </div>
  );
}
