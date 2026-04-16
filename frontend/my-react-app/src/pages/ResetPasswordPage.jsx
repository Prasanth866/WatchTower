import { useMemo, useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { resetPassword } from "../api/auth";

function useTokenFromQuery() {
  const location = useLocation();
  return useMemo(() => {
    const params = new URLSearchParams(location.search);
    return params.get("token") || "";
  }, [location.search]);
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const token = useTokenFromQuery();
  const [form, setForm] = useState({ new_password: "", confirm_password: "" });
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: resetPassword,
    onSuccess: (data) => {
      setError("");
      setMessage(data.message || "Password reset successfully.");
      setTimeout(() => navigate("/login", { replace: true }), 900);
    },
    onError: (err) => {
      setError(err?.response?.data?.detail || "Could not reset password");
    },
  });

  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <Paper elevation={8} className="w-full max-w-md rounded-2xl bg-slate-900 p-8 text-slate-100">
        <Stack spacing={3}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Reset Password
          </Typography>
          {message ? <Alert severity="success">{message}</Alert> : null}
          {error ? <Alert severity="error">{error}</Alert> : null}
          {!token ? <Alert severity="warning">Missing reset token in URL.</Alert> : null}
          <TextField
            label="New password"
            type="password"
            value={form.new_password}
            onChange={(e) => setForm((prev) => ({ ...prev, new_password: e.target.value }))}
          />
          <TextField
            label="Confirm password"
            type="password"
            value={form.confirm_password}
            onChange={(e) => setForm((prev) => ({ ...prev, confirm_password: e.target.value }))}
          />
          <Button
            variant="contained"
            disabled={!token || mutation.isPending}
            onClick={() => mutation.mutate({ token, ...form })}
          >
            {mutation.isPending ? "Resetting..." : "Reset password"}
          </Button>
          <Link to="/login" className="text-sky-400">Back to login</Link>
        </Stack>
      </Paper>
    </Box>
  );
}
