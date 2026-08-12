import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Store, Key, Loader2, CheckCircle, ExternalLink, LogOut } from "lucide-react";
import type { ShopifyConnection } from "@/hooks/useShopify";

interface ShopifyConnectProps {
  connection: ShopifyConnection;
  loading: boolean;
  onConnect: (shop_url: string, access_token: string) => Promise<boolean>;
  onDisconnect: () => void;
}

const ShopifyConnect = ({ connection, loading, onConnect, onDisconnect }: ShopifyConnectProps) => {
  const [shopUrl, setShopUrl] = useState("");
  const [accessToken, setAccessToken] = useState("");
  const [showToken, setShowToken] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!shopUrl.trim() || !accessToken.trim()) return;
    
    // Normalizar URL da loja
    let normalizedUrl = shopUrl.trim();
    if (!normalizedUrl.includes(".myshopify.com")) {
      normalizedUrl = `${normalizedUrl}.myshopify.com`;
    }
    normalizedUrl = normalizedUrl.replace(/^https?:\/\//, "").replace(/\/$/, "");
    
    const success = await onConnect(normalizedUrl, accessToken.trim());
    if (success) {
      setAccessToken(""); // Limpar token por segurança
    }
  };

  if (connection.connected) {
    return (
      <Card className="border-green-500/30 bg-green-500/5">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  {connection.shop_name || connection.shop_url}
                  <a 
                    href={`https://${connection.shop_url}`} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-primary"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </CardTitle>
                <CardDescription className="text-xs">
                  Conectado ao Shopify
                </CardDescription>
              </div>
            </div>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={onDisconnect}
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <LogOut className="w-4 h-4 mr-2" />
              Desconectar
            </Button>
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
            <Store className="w-5 h-5 text-primary" />
          </div>
          <div>
            <CardTitle className="text-base">Conectar Shopify</CardTitle>
            <CardDescription className="text-xs">
              Insira as credenciais da sua loja para começar
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="shop-url" className="text-xs text-muted-foreground">
              URL da Loja
            </Label>
            <div className="relative">
              <Input
                id="shop-url"
                type="text"
                placeholder="sua-loja"
                value={shopUrl}
                onChange={(e) => setShopUrl(e.target.value)}
                className="pr-32"
                required
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                .myshopify.com
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Apenas o nome da loja, sem "https://" ou ".myshopify.com"
            </p>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="access-token" className="text-xs text-muted-foreground flex items-center gap-2">
              <Key className="w-3 h-3" />
              Access Token
            </Label>
            <div className="relative">
              <Input
                id="access-token"
                type={showToken ? "text" : "password"}
                placeholder="shpat_xxxxx..."
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                className="pr-16"
                required
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground"
              >
                {showToken ? "Ocultar" : "Mostrar"}
              </button>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Obtenha em: Shopify Admin → Apps → Desenvolver apps → Criar app
            </p>
          </div>

          <Button
            type="submit"
            disabled={loading || !shopUrl.trim() || !accessToken.trim()}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Conectando...
              </>
            ) : (
              <>
                <Store className="w-4 h-4 mr-2" />
                Conectar Loja
              </>
            )}
          </Button>
        </form>

        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
          <p className="text-xs text-muted-foreground">
            <strong className="text-foreground">Como obter o Access Token:</strong>
          </p>
          <ol className="text-xs text-muted-foreground mt-2 space-y-1 list-decimal list-inside">
            <li>Acesse o painel admin do Shopify</li>
            <li>Vá em Configurações → Apps e canais de vendas</li>
            <li>Clique em "Desenvolver apps" → "Criar app"</li>
            <li>Configure as permissões de API (Products: Read/Write)</li>
            <li>Instale o app e copie o Access Token</li>
          </ol>
        </div>
      </CardContent>
    </Card>
  );
};

export default ShopifyConnect;
