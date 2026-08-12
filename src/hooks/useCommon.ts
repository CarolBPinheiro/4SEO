import { useState, useCallback, useMemo } from "react";
import type { ToastData } from "@/components/seo/Toast";

/**
 * Hook centralizado para gerenciar estado de loading e toasts
 * Reduz duplicação de código nos hooks principais
 */
export function useAsyncOperation() {
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<ToastData | null>(null);

  const showToast = useCallback((message: string, type: ToastData["type"] = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  }, []);

  const clearToast = useCallback(() => {
    setToast(null);
  }, []);

  /**
   * Wrapper para operações assíncronas com loading e tratamento de erro
   */
  const execute = useCallback(
    async <T>(
      operation: () => Promise<T>,
      options?: {
        successMessage?: string;
        errorMessage?: string;
        showLoading?: boolean;
      }
    ): Promise<{ data: T; success: true } | { error: string; success: false }> => {
      const { successMessage, errorMessage, showLoading = true } = options || {};

      if (showLoading) setLoading(true);
      
      try {
        const data = await operation();
        if (successMessage) showToast(successMessage, "success");
        return { data, success: true };
      } catch (err: unknown) {
        const errorObj = err as { message?: string };
        const message = errorMessage || errorObj.message || "Erro inesperado";
        showToast(message, "error");
        return { error: message, success: false };
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    [showToast]
  );

  return {
    loading,
    setLoading,
    toast,
    showToast,
    clearToast,
    execute,
  };
}

/**
 * Hook para gerenciar estado de seleção
 */
export function useSelection<T extends { id: string }>(initialItems: T[] = []) {
  const [items, setItems] = useState<T[]>(initialItems);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = useMemo(
    () => items.find((item) => item.id === selectedId) || null,
    [items, selectedId]
  );

  const select = useCallback((item: T | null) => {
    setSelectedId(item?.id || null);
  }, []);

  const add = useCallback((item: T) => {
    setItems((prev) => [item, ...prev]);
    setSelectedId(item.id);
  }, []);

  const update = useCallback((id: string, updater: (item: T) => T) => {
    setItems((prev) => prev.map((item) => (item.id === id ? updater(item) : item)));
  }, []);

  const remove = useCallback((id: string) => {
    setItems((prev) => prev.filter((item) => item.id !== id));
    if (selectedId === id) setSelectedId(null);
  }, [selectedId]);

  const reset = useCallback((newItems: T[]) => {
    setItems(newItems);
    if (newItems.length && !selectedId) {
      setSelectedId(newItems[0].id);
    }
  }, [selectedId]);

  return {
    items,
    selected,
    selectedId,
    setItems,
    select,
    add,
    update,
    remove,
    reset,
  };
}

/**
 * Hook para gerenciar estado de lista filtrada
 */
export function useFilteredList<T>(
  items: T[],
  filterFn: (item: T, query: string) => boolean
) {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    if (!query.trim()) return items;
    return items.filter((item) => filterFn(item, query.toLowerCase()));
  }, [items, query, filterFn]);

  return {
    query,
    setQuery,
    filtered,
    hasFilter: query.trim().length > 0,
    clear: () => setQuery(""),
  };
}
