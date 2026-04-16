import { useState } from "react";
import { Alert, Box, Button, Paper, Stack, TextField, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: forgotPassword,
    onSuccess: (data) => {
      setError("");
      setMessage(data.message || "If that email exists, a reset link has been sent.");
    },
    onError: (err) => {
      setError(err?.response?.data?.detail || "Unable to submit password reset request");
    },
  });

  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8">
      <Paper elevation={8} className="w-full max-w-md rounded-2xl bg-slate-900 p-8 text-slate-100">
        <Stack spacing={3}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Forgot Password
          </Typography>
          {message ? <Alert severity="success">{message}</Alert> : null}
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button variant="contained" onClick={() => mutation.mutate(email)} disabled={mutation.isPending}>
            {mutation.isPending ? "Sending..." : "Send reset link"}
          </Button>
          <Link to="/login" className="text-sky-400">Back to login</Link>
        </Stack>
      </Paper>
    </Box>
  );
}
