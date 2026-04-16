import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { fetchCurrentUser, loginUser } from "../api/auth";
import { useAuthStore } from "../store/authStore";

export default function LoginPage() {
  const navigate = useNavigate();
  const setSession = useAuthStore((state) => state.setSession);
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: async (session) => {
      setError("");
      const user = await fetchCurrentUser();
      setSession({ token: session.access_token, user });
      navigate("/", { replace: true });
    },
    onError: (err) => {
      setError(err?.response?.data?.detail || "Login failed");
    },
  });

  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <Paper elevation={8} className="w-full max-w-md rounded-2xl bg-slate-900 p-8 text-slate-100">
        <Stack spacing={3}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Sign in
          </Typography>
          <Typography color="text.secondary">Connect to your WatchTower workspace.</Typography>

          {error ? <Alert severity="error">{error}</Alert> : null}

          <TextField
            label="Email"
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
            {loginMutation.isPending ? "Signing in..." : "Sign in"}
          </Button>

          <Stack direction="row" justifyContent="space-between">
            <Link to="/register" className="text-sky-400">Create account</Link>
            <Link to="/forgot-password" className="text-sky-400">Forgot password?</Link>
          </Stack>
        </Stack>
      </Paper>
    </Box>
  );
}
