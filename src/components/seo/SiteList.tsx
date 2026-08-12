import { useState } from "react";
import { cn } from "@/lib/utils";
import { Globe, ChevronRight, Pencil, Trash2, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import SiteEditDialog from "./SiteEditDialog";

export interface Site {
  id: string;
  base_url: string;
  owner_email: string;
  platform?: string;
}

interface SiteListProps {
  sites: Site[];
  selectedSite: Site | null;
  onSelectSite: (site: Site) => void;
  onUpdateSite?: (siteId: string, data: { ownerEmail?: string; baseUrl?: string; platform?: string }) => Promise<boolean>;
  onDeleteSite?: (siteId: string) => Promise<boolean>;
  loading?: boolean;
}

const SiteList = ({ sites, selectedSite, onSelectSite, onUpdateSite, onDeleteSite, loading }: SiteListProps) => {
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [deletingSite, setDeletingSite] = useState<Site | null>(null);

  const handleEdit = (e: React.MouseEvent, site: Site) => {
    e.stopPropagation();
    setEditingSite(site);
  };

  const handleDelete = (e: React.MouseEvent, site: Site) => {
    e.stopPropagation();
    setDeletingSite(site);
  };

  const confirmDelete = async () => {
    if (deletingSite && onDeleteSite) {
      await onDeleteSite(deletingSite.id);
    }
    setDeletingSite(null);
  };

  const handleUpdateSite = async (data: { ownerEmail?: string; baseUrl?: string; platform?: string }) => {
    if (editingSite && onUpdateSite) {
      const success = await onUpdateSite(editingSite.id, data);
      if (success) {
        setEditingSite(null);
      }
      return success;
    }
    return false;
  };

  if (sites.length === 0) {
    return (
      <div className="text-center py-6">
        <Globe className="w-10 h-10 text-muted-foreground/50 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">
          Nenhum site cadastrado ainda.
        </p>
        <p className="text-xs text-muted-foreground/70 mt-1">
          Comece adicionando um acima.
        </p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2 max-h-80 overflow-auto scrollbar-thin">
        {sites.map((site) => {
          const isSelected = selectedSite?.id === site.id;
          return (
            <div
              key={site.id}
              className={cn(
                "w-full text-left p-3 rounded-xl border transition-all group relative",
                isSelected
                  ? "border-primary bg-primary/10 shadow-sm"
                  : "border-border/50 hover:border-primary/30 hover:bg-muted/50"
              )}
            >
              <button
                onClick={() => onSelectSite(site)}
                className="w-full text-left"
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                    isSelected ? "bg-primary/20" : "bg-muted group-hover:bg-primary/10"
                  )}>
                    <Globe className={cn(
                      "w-4 h-4 transition-colors",
                      isSelected ? "text-primary" : "text-muted-foreground group-hover:text-primary"
                    )} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate pr-8">
                      {site.base_url.replace(/^https?:\/\//, '')}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      {site.platform && (
                        <span className={cn(
                          "px-1.5 py-0.5 rounded text-[10px] font-medium uppercase",
                          isSelected ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                        )}>
                          {site.platform}
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronRight className={cn(
                    "w-4 h-4 shrink-0 transition-all",
                    isSelected ? "text-primary translate-x-0" : "text-muted-foreground -translate-x-1 opacity-0 group-hover:translate-x-0 group-hover:opacity-100"
                  )} />
                </div>
              </button>

              {(onUpdateSite || onDeleteSite) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="absolute top-2 right-2 h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="h-3 w-3" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-32">
                    {onUpdateSite && (
                      <DropdownMenuItem onClick={(e) => handleEdit(e as any, site)}>
                        <Pencil className="w-3 h-3 mr-2" />
                        Editar
                      </DropdownMenuItem>
                    )}
                    {onDeleteSite && (
                      <DropdownMenuItem 
                        onClick={(e) => handleDelete(e as any, site)}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="w-3 h-3 mr-2" />
                        Excluir
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          );
        })}
      </div>

      {/* Edit Dialog */}
      {editingSite && (
        <SiteEditDialog
          site={editingSite}
          open={!!editingSite}
          onOpenChange={(open) => !open && setEditingSite(null)}
          onSave={handleUpdateSite}
          loading={loading}
        />
      )}

      {/* Delete Confirmation */}
      <AlertDialog open={!!deletingSite} onOpenChange={(open) => !open && setDeletingSite(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir site?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta ação removerá permanentemente o site <strong>{deletingSite?.base_url.replace(/^https?:\/\//, '')}</strong>, 
              incluindo todas as páginas, varreduras e tarefas associadas. Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default SiteList;
