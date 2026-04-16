import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { registerUser } from "../api/auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");

  const registerMutation = useMutation({
    mutationFn: registerUser,
    onSuccess: () => {
      setError("");
      navigate("/login", { replace: true });
    },
    onError: (err) => {
      setError(err?.response?.data?.detail || "Registration failed");
    },
  });

  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <Paper elevation={8} className="w-full max-w-md rounded-2xl bg-slate-900 p-8 text-slate-100">
        <Stack spacing={3}>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            Create account
          </Typography>
          <Typography color="text.secondary">Use a strong password with uppercase, lowercase, number, and symbol.</Typography>

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
            helperText="8-72 chars, includes uppercase, lowercase, number, special character"
          />

          <Button
            variant="contained"
            size="large"
            onClick={() => registerMutation.mutate(form)}
            disabled={registerMutation.isPending}
          >
            {registerMutation.isPending ? "Creating account..." : "Create account"}
          </Button>

          <Link to="/login" className="text-sky-400">Already have an account? Sign in</Link>
        </Stack>
      </Paper>
    </Box>
  );
}
