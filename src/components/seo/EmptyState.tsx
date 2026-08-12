import { MousePointerClick, Rocket, Lightbulb, FileSearch } from "lucide-react";

const EmptyState = () => {
  const steps = [
    { icon: MousePointerClick, label: "Selecione um site", description: "Escolha na lista ao lado" },
    { icon: Rocket, label: "Rode a varredura", description: "Análise SEO completa" },
    { icon: Lightbulb, label: "Veja os problemas", description: "IA identifica melhorias" },
    { icon: FileSearch, label: "Analise o relatório", description: "Entenda o que corrigir" },
  ];

  return (
    <div className="card-gradient rounded-2xl border border-border p-8 shadow-soft">
      <div className="text-center mb-8">
        <div className="w-20 h-20 mx-auto mb-5 rounded-full bg-gradient-to-br from-blue-500/20 to-blue-500/5 flex items-center justify-center border border-blue-500/20">
          <FileSearch className="w-10 h-10 text-blue-500" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Auditoria SEO</h2>
        <p className="text-muted-foreground text-sm max-w-md mx-auto">
          Analise qualquer site para identificar problemas de SEO. 
          Para aplicar correções automaticamente, conecte sua loja via <strong>Shopify</strong> ou <strong>Nuvemshop</strong>.
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {steps.map((step, index) => (
          <div
            key={step.label}
            className="relative p-4 rounded-xl bg-muted/30 border border-border/50 text-center group hover:border-primary/30 transition-colors"
          >
            <div className="absolute -top-2 -left-2 w-6 h-6 rounded-full bg-primary/80 text-primary-foreground text-xs font-bold flex items-center justify-center">
              {index + 1}
            </div>
            <step.icon className="w-6 h-6 text-muted-foreground group-hover:text-primary mx-auto mb-2 transition-colors" />
            <p className="text-sm font-medium mb-1">{step.label}</p>
            <p className="text-xs text-muted-foreground">{step.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default EmptyState;
