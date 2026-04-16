import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchCurrentUser, loginUser } from "../api/auth";
import { useAuthStore } from "../store/authStore";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: async (session) => {
      try {
        setError("");
        setSession({ token: session.access_token, user: null });
        const user = await fetchCurrentUser(session.access_token);

        if (!user?.is_admin) {
          clearSession();
          setError("This account is not an admin account.");
          return;
        }

        setSession({ token: session.access_token, user });
        navigate("/admin", { replace: true });
      } catch (err) {
        clearSession();
        setError(err?.response?.data?.detail || "Admin sign in failed");
      }
    },
    onError: (err) => {
      clearSession();
      setError(err?.response?.data?.detail || "Admin sign in failed");
    },
  });

  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <Paper elevation={8} className="w-full max-w-md rounded-2xl bg-slate-900 p-8 text-slate-100">
        <Stack spacing={3}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Admin sign in
          </Typography>
          <Typography color="text.secondary">Use an admin account to access control features.</Typography>

          {error ? <Alert severity="error">{error}</Alert> : null}

          <TextField
            label="Admin email"
            type="email"
            value={form.email}
            onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
            fullWidth
            required
          />
          <TextField
            label="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
            fullWidth
            required
          />

          <Button
            variant="contained"
            size="large"
            onClick={() => loginMutation.mutate(form)}
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending ? "Signing in..." : "Sign in as admin"}
          </Button>

          <Link to="/login" className="text-sky-400">Back to user sign in</Link>
        </Stack>
      </Paper>
    </Box>
  );
}
