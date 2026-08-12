import { useState, useCallback, useEffect } from "react";
import type { Site } from "@/components/seo/SiteList";
import type { Page } from "@/components/seo/PagesTable";
import type { Review } from "@/components/seo/ReviewCard";
import type { ToastData } from "@/components/seo/Toast";
import type { ScanResult } from "@/components/seo/ScanSummary";
import { api } from "@/lib/apiClient";

export function useSeoScanner() {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [pages, setPages] = useState<Page[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [scanning, setScanning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = useCallback((message: string, type: ToastData["type"] = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const fetchSites = useCallback(async () => {
    try {
      const data = await api.sites.list();
      setSites(data || []);
      if (data?.length && !selectedSite) setSelectedSite(data[0]);
    } catch (error: any) {
      showToast(error.message || "Erro ao carregar sites", "error");
    }
  }, [selectedSite, showToast]);

  const createSite = useCallback(
    async (baseUrl: string, platform?: string) => {
      setLoading(true);
      try {
        const newSite = await api.sites.create(baseUrl, platform);
        setSites((prev) => [newSite, ...prev]);
        setSelectedSite(newSite);
        showToast("Site cadastrado com sucesso", "success");
        return true;
      } catch (error: any) {
        showToast(error.message || "Erro ao cadastrar site", "error");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [showToast]
  );

  const updateSite = useCallback(
    async (siteId: string, data: { baseUrl: string; platform?: string }) => {
      setLoading(true);
      try {
        const updatedSite = await api.sites.update(siteId, data.baseUrl, data.platform);
        setSites((prev) => prev.map((s) => (s.id === siteId ? updatedSite : s)));
        if (selectedSite?.id === siteId) setSelectedSite(updatedSite);
        showToast("Site atualizado com sucesso", "success");
        return true;
      } catch (error: any) {
        showToast(error.message || "Erro ao atualizar site", "error");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [selectedSite, showToast]
  );

  const deleteSite = useCallback(
    async (siteId: string) => {
      setLoading(true);
      try {
        await api.sites.remove(siteId);
        setSites((prev) => prev.filter((s) => s.id !== siteId));
        if (selectedSite?.id === siteId) {
          setSelectedSite(null);
          setPages([]);
          setReviews([]);
        }
        showToast("Site removido", "success");
        return true;
      } catch (error: any) {
        showToast(error.message || "Erro ao remover site", "error");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [selectedSite, showToast]
  );

  const selectSite = useCallback(async (site: Site) => {
    setSelectedSite(site);
    try {
      const pagesData = await api.sites.pages(site.id);
      setPages(pagesData || []);
      const reviewsData = await api.sites.reviews(site.id);
      setReviews(reviewsData || []);
    } catch (error) {
      console.error(error);
    }
  }, []);

  const scanSite = useCallback(async () => {
    if (!selectedSite) return;

    setLoading(true);
    setScanning(true);
    setScanResult(null);
    
    try {
      const data = await api.sites.scan(selectedSite.id);
      
      // Armazenar resultado do scan
      setScanResult(data);

      showToast(
        `Varredura concluída: ${data.pages_scanned} páginas, score ${data.score}`,
        "success"
      );

      // Carregar páginas e reviews atualizados
      const [pagesData, reviewsData] = await Promise.all([
        api.sites.pages(selectedSite.id),
        api.sites.reviews(selectedSite.id)
      ]);
      setPages(pagesData || []);
      setReviews(reviewsData || []);
    } catch (error: any) {
      showToast(error.message || "Erro ao escanear site", "error");
    } finally {
      setLoading(false);
      setScanning(false);
    }
  }, [selectedSite, showToast]);

  const fetchReviews = useCallback(async () => {
    if (!selectedSite) return;

    setLoading(true);
    try {
      // Primeiro, gera sugestões com IA
      await api.sites.analyze(selectedSite.id);
      
      // Depois, busca as reviews atualizadas
      const data = await api.sites.reviews(selectedSite.id);
      setReviews(data || []);
      if (!data || data.length === 0) showToast("Nenhuma alteração pendente no momento", "info");
    } catch (error: any) {
      showToast(error.message || "Erro ao carregar revisões", "error");
    } finally {
      setLoading(false);
    }
  }, [selectedSite, showToast]);

  const approveTask = useCallback(
    async (taskId: string) => {
      setLoading(true);
      try {
        await api.tasks.approve(taskId);
        setReviews((prev) => prev.filter((r) => r.task_id !== taskId));
        showToast("Tarefa aprovada", "success");
      } catch (error: any) {
        showToast(error.message || "Erro ao registrar aprovação", "error");
      } finally {
        setLoading(false);
      }
    },
    [showToast]
  );

  const deleteTask = useCallback(
    async (taskId: string) => {
      setLoading(true);
      try {
        await api.tasks.delete(taskId);
        setReviews((prev) => prev.filter((r) => r.task_id !== taskId));
        showToast("Tarefa descartada", "success");
      } catch (error: any) {
        showToast(error.message || "Erro ao descartar tarefa", "error");
      } finally {
        setLoading(false);
      }
    },
    [showToast]
  );

  const deletePage = useCallback(
    async (pageId: string) => {
      if (!selectedSite) return false;

      setLoading(true);
      try {
        await api.sites.deletePage(selectedSite.id, pageId);
        setPages((prev) => prev.filter((p) => p.id !== pageId));
        showToast("Página removida", "success");
        return true;
      } catch (error: any) {
        showToast(error.message || "Erro ao remover página", "error");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [selectedSite, showToast]
  );

  const executeChanges = useCallback(async () => {
    if (!selectedSite) return;

    setLoading(true);
    try {
      const data = await api.sites.execute(selectedSite.id);
      showToast(data?.message || "Alterações executadas", "success");

      // Refresh
      const pagesData = await api.sites.pages(selectedSite.id);
      setPages(pagesData || []);
      const reviewsData = await api.sites.reviews(selectedSite.id);
      setReviews(reviewsData || []);
    } catch (error: any) {
      showToast(error.message || "Erro ao executar alterações", "error");
    } finally {
      setLoading(false);
    }
  }, [selectedSite, showToast]);

  // initial load
  useEffect(() => {
    fetchSites();
  }, [fetchSites]);

  return {
    sites,
    selectedSite,
    pages,
    reviews,
    scanResult,
    scanning,
    loading,
    toast,
    createSite,
    updateSite,
    deleteSite,
    selectSite,
    scanSite,
    fetchReviews,
    approveTask,
    deleteTask,
    deletePage,
    executeChanges,
  };
}
