import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { isValidUrl } from "@/lib/validation";
import type { Site } from "./SiteList";

interface SiteEditDialogProps {
  site: Site;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: { ownerEmail?: string; baseUrl?: string; platform?: string }) => Promise<boolean>;
  loading?: boolean;
}

const SiteEditDialog = ({ site, open, onOpenChange, onSave, loading }: SiteEditDialogProps) => {
  const [ownerEmail, setOwnerEmail] = useState(site.owner_email);
  const [baseUrl, setBaseUrl] = useState(site.base_url);
  const [platform, setPlatform] = useState(site.platform || "");
  const [urlError, setUrlError] = useState<string | null>(null);

  useEffect(() => {
    if (site) {
      setOwnerEmail(site.owner_email);
      setBaseUrl(site.base_url);
      setPlatform(site.platform || "");
      setUrlError(null);
    }
  }, [site]);

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setBaseUrl(value);
    if (value && !isValidUrl(value)) {
      setUrlError("URL inválida");
    } else {
      setUrlError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (urlError) return;
    await onSave({ ownerEmail, baseUrl, platform: platform || undefined });
  };

  const isValid = !urlError && baseUrl.trim();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Editar Site</DialogTitle>
          <DialogDescription>
            Atualize as informações do site cadastrado.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="edit-email" className="text-xs text-muted-foreground">
              E-mail do proprietário
            </Label>
            <Input
              id="edit-email"
              type="email"
              value={ownerEmail}
              onChange={(e) => setOwnerEmail(e.target.value)}
              className="bg-background border-border"
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-url" className="text-xs text-muted-foreground">
              URL do e-commerce
            </Label>
            <Input
              id="edit-url"
              type="url"
              value={baseUrl}
              onChange={handleUrlChange}
              className={`bg-background border-border ${urlError ? "border-destructive" : ""}`}
              required
            />
            {urlError && (
              <p className="text-xs text-destructive">{urlError}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-platform" className="text-xs text-muted-foreground">
              Plataforma
            </Label>
            <Select value={platform || "none"} onValueChange={(val) => setPlatform(val === "none" ? "" : val)}>
              <SelectTrigger className="bg-background border-border">
                <SelectValue placeholder="Selecione (opcional)" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Nenhuma</SelectItem>
                <SelectItem value="shopify">Shopify</SelectItem>
                <SelectItem value="lojaintegrada">Loja Integrada</SelectItem>
                <SelectItem value="tray">Tray</SelectItem>
                <SelectItem value="nuvemshop">Nuvemshop</SelectItem>
                <SelectItem value="vtex">VTEX</SelectItem>
                <SelectItem value="outro">Outro</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancelar
            </Button>
            <Button type="submit" disabled={loading || !isValid}>
              {loading ? "Salvando..." : "Salvar alterações"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default SiteEditDialog;
