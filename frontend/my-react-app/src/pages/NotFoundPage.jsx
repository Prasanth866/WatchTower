import { Box, Button, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <Box className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <Stack spacing={2} alignItems="center">
        <Typography variant="h3" sx={{ fontWeight: 800 }}>404</Typography>
        <Typography>Page not found.</Typography>
        <Button variant="contained" onClick={() => navigate("/")}>Back to dashboard</Button>
      </Stack>
    </Box>
  );
}
