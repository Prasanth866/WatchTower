import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Alert, Box, CircularProgress } from "@mui/material";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { fetchCurrentUser } from "./api/auth";
import AdminRoute from "./components/AdminRoute";
import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminPage from "./pages/AdminPage";
import DashboardPage from "./pages/DashboardPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import TopicPage from "./pages/TopicPage";
import TriggersPage from "./pages/TriggersPage";
import { useAuthStore } from "./store/authStore";

function SessionBootstrap({ children }) {
  const token = useAuthStore((state) => state.token);
  const setUser = useAuthStore((state) => state.setUser);
  const clearSession = useAuthStore((state) => state.clearSession);

  const userQuery = useQuery({
    queryKey: ["me", token],
    queryFn: fetchCurrentUser,
    enabled: Boolean(token),
    retry: false,
  });

  useEffect(() => {
    if (userQuery.data) {
      setUser(userQuery.data);
    }
  }, [setUser, userQuery.data]);

  useEffect(() => {
    if (userQuery.isError && token) {
      clearSession();
    }
  }, [clearSession, token, userQuery.isError]);

  if (token && userQuery.isLoading) {
    return (
      <Box className="flex min-h-screen items-center justify-center bg-slate-950">
        <CircularProgress />
      </Box>
    );
  }

  if (token && userQuery.isError) {
    return (
      <Box className="mx-auto mt-6 max-w-xl px-4">
        <Alert severity="warning">Your session expired. Please sign in again.</Alert>
      </Box>
    );
  }

  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <SessionBootstrap>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="topics/:topicId" element={<TopicPage />} />
            <Route path="triggers" element={<TriggersPage />} />
            <Route
              path="admin"
              element={
                <AdminRoute>
                  <AdminPage />
                </AdminRoute>
              }
            />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
          <Route path="/home" element={<Navigate to="/" replace />} />
        </Routes>
      </SessionBootstrap>
    </BrowserRouter>
  );
}
