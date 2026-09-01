import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "@/lib/apiClient";

export type DemoAccount = { email: string; role: string };

export type DemoState = {
  enabled: boolean;
  loading: boolean;
  loginEmail: string;
  loginPassword: string;
  accounts: DemoAccount[];
};

const defaultState: DemoState = {
  enabled: false,
  loading: true,
  loginEmail: "",
  loginPassword: "",
  accounts: [],
};

const DemoContext = createContext<DemoState>(defaultState);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DemoState>(defaultState);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const info = await api.info();
        const demo = info?.demo;
        if (cancelled) return;
        setState({
          enabled: Boolean(demo?.enabled),
          loading: false,
          loginEmail: demo?.loginEmail || "",
          loginPassword: demo?.loginPassword || "",
          accounts: Array.isArray(demo?.accounts) ? demo.accounts : [],
        });
      } catch {
        if (!cancelled) {
          setState({ ...defaultState, loading: false });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo(() => state, [state]);
  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo(): DemoState {
  return useContext(DemoContext);
}
