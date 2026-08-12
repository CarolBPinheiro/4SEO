import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useAuth } from "./AuthContext";
import { useBilling } from "./BillingContext";
import { api } from "@/lib/apiClient";
import { getToken } from "@/lib/apiClient";

export interface StoreInfo {
  platform: "shopify" | "nuvemshop" | "vtex" | "lojaintegrada" | null;
  name: string;
  url: string;
  storeId: string;
}

interface StoreContextType {
  store: StoreInfo | null;
  connected: boolean;
  loading: boolean;
  setStore: (store: StoreInfo | null) => void;
  refreshStatus: () => Promise<void>;
  disconnect: () => Promise<void>;
}

const StoreContext = createContext<StoreContextType | null>(null);

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const { hasActiveSubscription, loading: billingLoading } = useBilling();
  const [store, setStoreState] = useState<StoreInfo | null>(null);
  const [loading, setLoading] = useState(false);

  const setStore = useCallback((info: StoreInfo | null) => {
    setStoreState(info);
    if (info) {
      localStorage.setItem("4seo_store", JSON.stringify(info));
    } else {
      localStorage.removeItem("4seo_store");
    }
  }, []);

  const disconnect = useCallback(async () => {
    await api.integrations.disconnect();
    setStore(null);
  }, [setStore]);

  const refreshStatus = useCallback(async () => {
    if (!user || !hasActiveSubscription) {
      setStore(null);
      return;
    }
    if (!getToken()) return;
    setLoading(true);
    try {
      const data = await api.integrations.status();
      if (data?.connected && data.platform) {
        setStore({
          platform: data.platform,
          name: data.store_name || data.shop_url || "Loja",
          url: data.shop_url || "",
          storeId: data.store_id || "",
        });
      } else {
        setStore(null);
      }
    } catch {
      // Sem assinatura ou falha de rede — mantém estado seguro
    } finally {
      setLoading(false);
    }
  }, [user, hasActiveSubscription, setStore]);

  useEffect(() => {
    const saved = localStorage.getItem("4seo_store");
    if (saved) {
      try {
        setStoreState(JSON.parse(saved));
      } catch {
        localStorage.removeItem("4seo_store");
      }
    }
  }, []);

  useEffect(() => {
    if (billingLoading) return;
    if (user && getToken() && hasActiveSubscription) {
      void refreshStatus();
    } else {
      setStore(null);
    }
  }, [user, hasActiveSubscription, billingLoading]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <StoreContext.Provider
      value={{
        store,
        connected: !!store?.platform && hasActiveSubscription,
        loading,
        setStore,
        refreshStatus,
        disconnect,
      }}
    >
      {children}
    </StoreContext.Provider>
  );
}

export function useStore() {
  const context = useContext(StoreContext);
  if (!context) throw new Error("useStore must be used within StoreProvider");
  return context;
}
