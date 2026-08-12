import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft } from "lucide-react";
import { isValidUrl } from "@/lib/validation";

interface SiteFormProps {
  onSubmit: (baseUrl: string, platform?: string) => void;
  loading: boolean;
  onCancel?: () => void;
}

const SiteForm = ({ onSubmit, loading, onCancel }: SiteFormProps) => {
  const [baseUrl, setBaseUrl] = useState("");
  const [urlError, setUrlError] = useState<string | null>(null);

  const validateUrl = (url: string) => {
    if (!url.trim()) {
      setUrlError(null);
      return;
    }
    if (!isValidUrl(url)) {
      setUrlError("URL inválida. Use formato: https://exemplo.com");
    } else {
      setUrlError(null);
    }
  };

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setBaseUrl(value);
    validateUrl(value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!baseUrl.trim() || urlError) return;
    if (!isValidUrl(baseUrl)) {
      setUrlError("URL inválida");
      return;
    }
    onSubmit(baseUrl);
    setBaseUrl("");
    setUrlError(null);
  };

  const isValid = baseUrl.trim() && !urlError;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {onCancel && (
        <button
          type="button"
          onClick={onCancel}
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-3 h-3" />
          Voltar
        </button>
      )}
      <div className="space-y-2">
        <Label htmlFor="url" className="text-xs text-muted-foreground">
          URL do e-commerce
        </Label>
        <Input
          id="url"
          type="url"
          placeholder="https://www.sualoja.com.br"
          value={baseUrl}
          onChange={handleUrlChange}
          className={`bg-background border-border ${urlError ? "border-destructive" : ""}`}
          required
        />
        {urlError && (
          <p className="text-xs text-destructive">{urlError}</p>
        )}
      </div>
      <Button
        type="submit"
        disabled={loading || !isValid}
        className="w-full btn-gradient text-primary-foreground font-medium rounded-full hover:brightness-105 transition-all hover:-translate-y-0.5"
      >
        {loading ? "Processando..." : "Adicionar site"}
      </Button>
    </form>
  );
};

export default SiteForm;
