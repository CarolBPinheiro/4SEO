import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AuthProvider } from "@/contexts/AuthContext";
import { BillingProvider } from "@/contexts/BillingContext";
import { StoreProvider } from "@/contexts/StoreContext";
import AppLayout from "@/components/layout/AppLayout";
import ProtectedRoute from "@/components/layout/ProtectedRoute";
import SubscriptionRoute from "@/components/layout/SubscriptionRoute";
import AdminRoute from "@/components/layout/AdminRoute";

import MarketingRedirect from "./screens/MarketingRedirect";
import Login from "./screens/Login";
import Dashboard from "./screens/Dashboard";
import TermosPesquisa from "./screens/TermosPesquisa";
import Historico from "./screens/Historico";
import Integracoes from "./screens/Integracoes";
import Analise from "./screens/Analise";
import PanoramaSEO from "./screens/PanoramaSEO";
import NotFound from "./screens/NotFound";
import AdminLayout from "./screens/admin/AdminLayout";
import AdminOverviewPage from "./screens/admin/AdminOverviewPage";
import AdminUsersPage from "./screens/admin/AdminUsersPage";
import AdminUserDetailPage from "./screens/admin/AdminUserDetailPage";
import AdminSubscriptionsPage from "./screens/admin/AdminSubscriptionsPage";
import AdminHealthPage from "./screens/admin/AdminHealthPage";
import AdminAuditPage from "./screens/admin/AdminAuditPage";
import AdminContentPage from "./screens/admin/AdminContentPage";

const queryClient = new QueryClient();

function ProtectedApp({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute>
      <BillingProvider>
        <StoreProvider>
          <AppLayout>{children}</AppLayout>
        </StoreProvider>
      </BillingProvider>
    </ProtectedRoute>
  );
}

const App = () => (
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <AuthProvider>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <Routes>
              <Route path="/" element={<MarketingRedirect />} />
              <Route path="/login" element={<Login />} />
              <Route path="/dashboard" element={<ProtectedApp><Dashboard /></ProtectedApp>} />
              <Route
                path="/termos"
                element={
                  <ProtectedApp>
                    <SubscriptionRoute>
                      <TermosPesquisa />
                    </SubscriptionRoute>
                  </ProtectedApp>
                }
              />
              <Route
                path="/historico"
                element={
                  <ProtectedApp>
                    <SubscriptionRoute>
                      <Historico />
                    </SubscriptionRoute>
                  </ProtectedApp>
                }
              />
              <Route
                path="/integracoes"
                element={
                  <ProtectedApp>
                    <SubscriptionRoute>
                      <Integracoes />
                    </SubscriptionRoute>
                  </ProtectedApp>
                }
              />
              <Route
                path="/analise"
                element={
                  <ProtectedApp>
                    <SubscriptionRoute>
                      <Analise />
                    </SubscriptionRoute>
                  </ProtectedApp>
                }
              />
              <Route
                path="/panorama"
                element={
                  <ProtectedApp>
                    <SubscriptionRoute>
                      <PanoramaSEO />
                    </SubscriptionRoute>
                  </ProtectedApp>
                }
              />

              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <AdminLayout />
                  </AdminRoute>
                }
              >
                <Route index element={<AdminOverviewPage />} />
                <Route path="users" element={<AdminUsersPage />} />
                <Route path="users/:userId" element={<AdminUserDetailPage />} />
                <Route path="subscriptions" element={<AdminSubscriptionsPage />} />
                <Route path="health" element={<AdminHealthPage />} />
                <Route path="audit" element={<AdminAuditPage />} />
                <Route path="conteudo" element={<AdminContentPage />} />
              </Route>

              <Route path="/app" element={<Navigate to="/analise" replace />} />
              <Route path="/keywords" element={<Navigate to="/termos" replace />} />
              <Route path="/shopify" element={<Navigate to="/integracoes" replace />} />
              <Route path="/nuvemshop" element={<Navigate to="/analise" replace />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </TooltipProvider>
    </QueryClientProvider>
  </ErrorBoundary>
);

export default App;
