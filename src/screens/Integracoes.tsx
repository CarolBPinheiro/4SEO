import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useStore, type StoreInfo } from "@/contexts/StoreContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Store,
  Lock,
  Trash2,
  X,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/apiClient";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

/* Platform icons using actual Figma assets */
function ShopifyIcon() {
  return (
    <img src="/illustrations/shopify-icon.png" alt="" className="w-20 h-24 opacity-30 object-contain" />
  );
}

function NuvemshopIcon() {
  return (
    <img src="/illustrations/nuvemshop-icon.png" alt="" className="w-24 h-20 opacity-30 object-contain" />
  );
}

/*
 * Marcas d'água das plataformas: recriações SVG monocromáticas dos logos
 * oficiais (VTEX = duplo-triângulo). Herdam o cinza (text-muted-foreground)
 * do container, no mesmo tratamento esmaecido do Shopify/Nuvemshop. Para usar
 * o PNG oficial, salve-o em /illustrations/ e troque por
 * <img src="/illustrations/vtex-icon.png" ... /> como as demais.
 */
function VtexIcon() {
  return (
    <svg viewBox="0 0 100 100" className="w-20 h-20 opacity-30" fill="currentColor" aria-hidden="true">
      {/* Dois triângulos sobrepostos apontando para baixo — o recorte na
          interseção (negativo) é obtido com fill-rule evenodd */}
      <path fillRule="evenodd" d="M24 20 L92 20 L58 80 Z M8 42 L60 42 L34 90 Z" />
    </svg>
  );
}

function LojaIntegradaIcon() {
  return (
    <svg viewBox="0 0 100 100" className="w-20 h-20 opacity-30" aria-hidden="true">
      <path
        d="M30 28 L30 50 Q30 74 52 74 Q74 74 74 52"
        fill="none"
        stroke="currentColor"
        strokeWidth="16"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="76" cy="30" r="11" fill="currentColor" />
    </svg>
  );
}

interface IntegrationCardProps {
  platform: string;
  description: string;
  icon: React.ReactNode;
  disabled?: boolean;
  connected: boolean;
  lockedByOther?: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
}

function IntegrationCard({ platform, description, icon, disabled, connected, lockedByOther, onConnect, onDisconnect }: IntegrationCardProps) {
  return (
    <div className={`rounded-xl border border-border bg-card p-6 flex flex-col justify-between min-h-[200px] relative overflow-hidden ${lockedByOther ? "opacity-50" : ""}`}>
      <div>
        <h3 className="text-2xl font-semibold mb-2">{platform}</h3>
        <p className="text-sm text-muted-foreground max-w-[70%]">{description}</p>
      </div>

      {/* Large faded platform icon on the right */}
      <div className="absolute right-4 bottom-4 text-muted-foreground">
        {icon}
      </div>

      <div className="mt-6 relative z-10">
        {disabled || lockedByOther ? (
          <Button variant="outline" disabled className="gap-2 opacity-50">
            <Lock className="w-4 h-4" />
            {lockedByOther ? "Desconecte a loja atual" : "Em breve"}
          </Button>
        ) : connected ? (
          <Button variant="destructive" size="sm" className="gap-2" onClick={onDisconnect}>
            <Trash2 className="w-4 h-4" />
            Desconectar
          </Button>
        ) : (
          <Button variant="outline" className="gap-2" onClick={onConnect}>
            <Store className="w-4 h-4" />
            Realizar integração
          </Button>
        )}
      </div>
    </div>
  );
}

// Shopify connect dialog — OAuth do app 4SEO (fluxo principal)
function ShopifyConnectDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
  onConnected: (store: StoreInfo) => void;
}) {
  const [shopUrl, setShopUrl] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleOAuth = async () => {
    if (!shopUrl.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await api.shopify.getAuthUrl(shopUrl.trim());
      if (data?.auth_url) {
        window.location.href = data.auth_url;
        return;
      }
      setError("Não foi possível iniciar a autorização Shopify.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao iniciar OAuth Shopify";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleManualConnect = async () => {
    if (!shopUrl.trim() || !accessToken.trim()) return;
    setError("");
    setLoading(true);
    try {
      const rawUrl = shopUrl.includes(".myshopify.com")
        ? shopUrl
        : `${shopUrl}.myshopify.com`;
      const fullUrl = rawUrl.startsWith("http") ? rawUrl : `https://${rawUrl}`;
      await api.shopify.connect(fullUrl, accessToken);
      window.location.href = "/analise?connected=true&platform=shopify";
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Erro ao conectar com Shopify";
      setError(message);
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-8">
        <div>
          <h2 className="text-2xl font-bold mb-1">Conectar Shopify</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Informe o nome da loja e autorize o app 4SEO na Shopify.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>URL da loja</Label>
              <div className="flex">
                <Input
                  placeholder="sua-loja"
                  className="rounded-r-none bg-muted/50"
                  value={shopUrl}
                  onChange={(e) => setShopUrl(e.target.value)}
                  disabled={loading}
                />
                <div className="flex items-center px-3 border border-l-0 border-border rounded-r-lg bg-muted/30 text-sm text-muted-foreground">
                  .myshopify.com
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Apenas o nome da loja, sem &quot;https://&quot; ou &quot;.myshopify.com&quot;
              </p>
            </div>

            {!showManual && (
              <Button
                className="w-full btn-gradient text-primary-foreground font-semibold gap-2"
                size="lg"
                onClick={handleOAuth}
                disabled={loading || !shopUrl.trim()}
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Store className="w-5 h-5" />}
                {loading ? "Redirecionando..." : "Autorizar na Shopify"}
              </Button>
            )}

            {showManual && (
              <>
                <div className="space-y-2">
                  <Label>Access Token (legado)</Label>
                  <div className="relative">
                    <Input
                      type={showToken ? "text" : "password"}
                      placeholder="shpat_xxxxx..."
                      className="pr-20 bg-muted/50"
                      value={accessToken}
                      onChange={(e) => setAccessToken(e.target.value)}
                      disabled={loading}
                    />
                    <button
                      type="button"
                      onClick={() => setShowToken(!showToken)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground hover:text-foreground"
                    >
                      {showToken ? "Ocultar" : "Mostrar"}
                    </button>
                  </div>
                </div>
                <Button
                  className="w-full btn-gradient text-primary-foreground font-semibold gap-2"
                  size="lg"
                  onClick={handleManualConnect}
                  disabled={loading || !shopUrl.trim() || !accessToken.trim()}
                >
                  {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Store className="w-5 h-5" />}
                  {loading ? "Conectando..." : "Conectar com token"}
                </Button>
              </>
            )}
          </div>

          <div className="mt-6 p-4 rounded-lg bg-muted/30 border border-border">
            <p className="text-sm font-semibold mb-2">Como funciona</p>
            <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Informe o nome da sua loja Shopify</li>
              <li>Clique em Autorizar na Shopify</li>
              <li>Instale/autorize o app 4SEO na tela da Shopify</li>
              <li>Você volta automaticamente para o 4SEO conectado</li>
            </ol>
          </div>

          <button
            type="button"
            className="mt-4 text-xs text-muted-foreground underline hover:text-foreground"
            onClick={() => setShowManual((v) => !v)}
          >
            {showManual ? "Usar autorização OAuth (recomendado)" : "Já tenho um access token (legado)"}
          </button>

          <Button variant="ghost" className="w-full mt-4" onClick={onClose} disabled={loading}>
            Cancelar
          </Button>
        </div>
      </div>
    </div>
  );
}

// Diálogo de conexão VTEX (App Key + App Token)
function VtexConnectDialog({
  open,
  onClose,
  onConnected,
}: {
  open: boolean;
  onClose: () => void;
  onConnected: (store: StoreInfo) => void;
}) {
  const [accountName, setAccountName] = useState("");
  const [appKey, setAppKey] = useState("");
  const [appToken, setAppToken] = useState("");
  const [showToken, setShowToken] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConnect = async () => {
    if (!accountName.trim() || !appKey.trim() || !appToken.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await api.vtex.connect(accountName.trim(), appKey.trim(), appToken.trim());
      if (!data?.success) {
        setError(data?.detail || data?.message || "Falha ao conectar com a VTEX");
        return;
      }
      onConnected({
        platform: "vtex",
        name: data.store?.name || accountName.trim(),
        url: data.store?.url || "",
        storeId: data.store_id || accountName.trim().toLowerCase(),
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao conectar com VTEX");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-8">
        <h2 className="text-2xl font-bold mb-1">Conectar VTEX</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Insira as credenciais de aplicação (App Key/App Token) da sua conta VTEX
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Account name</Label>
            <Input
              placeholder="minhaloja"
              className="bg-muted/50"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              O nome da conta (subdomínio), ex: minhaloja.vtexcommercestable.com.br
            </p>
          </div>

          <div className="space-y-2">
            <Label>App Key</Label>
            <Input
              placeholder="vtexappkey-minhaloja-XXXXXX"
              className="bg-muted/50"
              value={appKey}
              onChange={(e) => setAppKey(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label>App Token</Label>
            <div className="relative">
              <Input
                type={showToken ? "text" : "password"}
                placeholder="Token da aplicação"
                className="pr-20 bg-muted/50"
                value={appToken}
                onChange={(e) => setAppToken(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground hover:text-foreground"
              >
                {showToken ? "Ocultar" : "Mostrar"}
              </button>
            </div>
          </div>

          <Button
            className="w-full btn-gradient text-primary-foreground font-semibold gap-2"
            size="lg"
            onClick={handleConnect}
            disabled={loading || !accountName.trim() || !appKey.trim() || !appToken.trim()}
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Store className="w-5 h-5" />}
            {loading ? "Conectando..." : "Conectar loja"}
          </Button>
        </div>

        <div className="mt-6 p-4 rounded-lg bg-muted/30 border border-border">
          <p className="text-sm font-semibold mb-2">Como obter as credenciais:</p>
          <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
            <li>Acesse o Admin VTEX → Configurações da conta → Chaves de aplicação</li>
            <li>Gere um novo par App Key / App Token</li>
            <li>Associe uma função (role) com os recursos de Catálogo:
              "Product and SKU Management" e "Categories Management"</li>
            <li>Sem essas permissões a conexão retorna erro 403</li>
          </ol>
        </div>

        <Button variant="ghost" className="w-full mt-4" onClick={onClose}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

// Diálogo de conexão Loja Integrada (Chave de API da loja)
function LojaIntegradaConnectDialog({
  open,
  onClose,
  onConnected,
}: {
  open: boolean;
  onClose: () => void;
  onConnected: (store: StoreInfo) => void;
}) {
  const [chaveApi, setChaveApi] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleConnect = async () => {
    if (!chaveApi.trim()) return;
    setError("");
    setLoading(true);
    try {
      const data = await api.lojaintegrada.connect(chaveApi.trim());
      if (!data?.success) {
        setError(data?.detail || data?.message || "Falha ao conectar com a Loja Integrada");
        return;
      }
      onConnected({
        platform: "lojaintegrada",
        name: data.store?.name || "Loja Integrada",
        url: data.store?.url || "",
        storeId: data.store_id || "",
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao conectar com Loja Integrada");
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-8">
        <h2 className="text-2xl font-bold mb-1">Conectar Loja Integrada</h2>
        <p className="text-sm text-muted-foreground mb-6">
          Insira a Chave de API da sua loja para começar
        </p>

        <div className="mb-4 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-sm text-yellow-600">
          A API da Loja Integrada está disponível apenas para lojas em <strong>planos pagos</strong>.
          No plano grátis não é possível gerar a Chave de API.
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Chave de API</Label>
            <div className="relative">
              <Input
                type={showKey ? "text" : "password"}
                placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                className="pr-20 bg-muted/50"
                value={chaveApi}
                onChange={(e) => setChaveApi(e.target.value)}
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground hover:text-foreground"
              >
                {showKey ? "Ocultar" : "Mostrar"}
              </button>
            </div>
          </div>

          <Button
            className="w-full btn-gradient text-primary-foreground font-semibold gap-2"
            size="lg"
            onClick={handleConnect}
            disabled={loading || !chaveApi.trim()}
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Store className="w-5 h-5" />}
            {loading ? "Conectando..." : "Conectar loja"}
          </Button>
        </div>

        <div className="mt-6 p-4 rounded-lg bg-muted/30 border border-border">
          <p className="text-sm font-semibold mb-2">Como obter a Chave de API:</p>
          <ol className="text-xs text-muted-foreground space-y-1 list-decimal list-inside">
            <li>Acesse o painel da sua Loja Integrada</li>
            <li>Vá em Configurações → Chave para API</li>
            <li>Clique para cadastrar/gerar uma nova chave</li>
            <li>Copie a chave (formato UUID) e cole acima</li>
          </ol>
        </div>

        <Button variant="ghost" className="w-full mt-4" onClick={onClose} disabled={loading}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

export default function Integracoes() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { store, connected, setStore, disconnect, refreshStatus } = useStore();
  const [showShopify, setShowShopify] = useState(false);
  const [showVtex, setShowVtex] = useState(false);
  const [showLojaIntegrada, setShowLojaIntegrada] = useState(false);
  const [showRemoveDialog, setShowRemoveDialog] = useState(false);
  const [nuvemshopLoading, setNuvemshopLoading] = useState(false);

  // O GSC continua funcionando via backend — o card de conexão manual foi removido da UI.
  // Limpa o parâmetro do callback OAuth (?gsc=connected) se o usuário cair aqui após autorizar.
  useEffect(() => {
    if (searchParams.get("gsc")) {
      setSearchParams({}, { replace: true });
    }
  }, []);

  const handleConnected = (info: StoreInfo) => {
    setStore(info);
    refreshStatus();
    // Pequena pausa cosmética antes de trocar de tela (não garante nem
    // depende do scan inicial, que roda em background no backend e pode
    // levar bem mais que isso — o próprio Dashboard detecta e sinaliza o
    // scan em andamento ao montar, veja Dashboard.tsx).
    setTimeout(() => {
      navigate("/dashboard");
    }, 1500);
  };

  const handleNuvemshopConnect = async () => {
    setNuvemshopLoading(true);
    try {
      const data = await api.nuvemshop.getAuthUrl();
      if (data?.auth_url) {
        window.location.href = data.auth_url;
      }
    } catch (err) {
      console.error("Erro ao iniciar OAuth Nuvemshop:", err);
      setNuvemshopLoading(false);
    }
  };

  const [disconnectError, setDisconnectError] = useState("");
  const [disconnecting, setDisconnecting] = useState(false);

  const handleDisconnect = async () => {
    setDisconnecting(true);
    setDisconnectError("");
    try {
      await disconnect();
      setShowRemoveDialog(false);
    } catch (err: any) {
      // Não fecha o diálogo nem finge sucesso: se a desconexão falhou de
      // verdade no backend, a loja ainda está conectada lá — fechar aqui
      // deixaria o usuário achando que deu certo até ela "reaparecer"
      // sozinha.
      setDisconnectError(err?.message || "Falha ao desconectar. Tente novamente.");
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Integrações</h1>
      <p className="text-muted-foreground">
        Conecte sua loja para começar a otimizar o SEO automaticamente.
        {connected && " Limite de 1 integração por usuário."}
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <IntegrationCard
          platform="Shopify"
          description="Integre rapidamente a sua loja Shopify no 4SEO e faça a análise de SEO e produtos"
          icon={<ShopifyIcon />}
          connected={connected && store?.platform === "shopify"}
          lockedByOther={connected && store?.platform !== "shopify"}
          onConnect={() => setShowShopify(true)}
          onDisconnect={() => setShowRemoveDialog(true)}
        />
        <IntegrationCard
          platform="Nuvemshop"
          description="Integre rapidamente a sua loja Nuvemshop no 4SEO e faça a análise de SEO e produtos"
          icon={<NuvemshopIcon />}
          connected={connected && store?.platform === "nuvemshop"}
          lockedByOther={connected && store?.platform !== "nuvemshop"}
          onConnect={handleNuvemshopConnect}
          onDisconnect={() => setShowRemoveDialog(true)}
        />
        <IntegrationCard
          platform="VTEX"
          description="Integração nativa com lojas VTEX. Leitura de produtos, categorias e otimização de SEO."
          icon={<VtexIcon />}
          connected={connected && store?.platform === "vtex"}
          lockedByOther={connected && store?.platform !== "vtex"}
          onConnect={() => setShowVtex(true)}
          onDisconnect={() => setShowRemoveDialog(true)}
        />
        <IntegrationCard
          platform="Loja Integrada"
          description="Integração com lojas Loja Integrada. Leitura de produtos, categorias e otimização de SEO."
          icon={<LojaIntegradaIcon />}
          connected={connected && store?.platform === "lojaintegrada"}
          lockedByOther={connected && store?.platform !== "lojaintegrada"}
          onConnect={() => setShowLojaIntegrada(true)}
          onDisconnect={() => setShowRemoveDialog(true)}
        />
      </div>

      {/* Shopify dialog */}
      <ShopifyConnectDialog
        open={showShopify}
        onClose={() => setShowShopify(false)}
        onConnected={handleConnected}
      />

      {/* VTEX dialog */}
      <VtexConnectDialog
        open={showVtex}
        onClose={() => setShowVtex(false)}
        onConnected={handleConnected}
      />

      {/* Loja Integrada dialog */}
      <LojaIntegradaConnectDialog
        open={showLojaIntegrada}
        onClose={() => setShowLojaIntegrada(false)}
        onConnected={handleConnected}
      />

      {/* Remove integration dialog */}
      <AlertDialog
        open={showRemoveDialog}
        onOpenChange={(open) => {
          setShowRemoveDialog(open);
          if (!open) setDisconnectError("");
        }}
      >
        <AlertDialogContent className="bg-card border-border">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-xl">Atenção</AlertDialogTitle>
            <AlertDialogDescription className="text-muted-foreground">
              Deseja realmente remover esta integração? Os dados contidos nela serão removidos da plataforma.
            </AlertDialogDescription>
            {disconnectError && (
              <p className="text-sm text-destructive mt-2">{disconnectError}</p>
            )}
          </AlertDialogHeader>
          <AlertDialogFooter className="flex gap-3 sm:gap-3">
            <AlertDialogCancel className="gap-2 border-primary/30 text-primary hover:bg-primary/10 flex-1">
              <X className="w-4 h-4" />
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-primary text-primary-foreground gap-2 flex-1"
              disabled={disconnecting}
              onClick={(e) => {
                // Controla o fechamento manualmente: se a desconexão falhar,
                // o diálogo precisa continuar aberto mostrando o erro em vez
                // de fechar como se tivesse dado certo (Radix fecha sozinho
                // no clique a menos que a gente previna).
                e.preventDefault();
                handleDisconnect();
              }}
            >
              {disconnecting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  );
}
