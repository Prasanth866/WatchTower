import { AppBar, Box, Button, Container, Toolbar, Typography } from "@mui/material";
import { Activity, LogOut, Settings, Shield, Waves } from "lucide-react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

const navItems = [
  { to: "/", label: "Dashboard", icon: Activity },
  { to: "/triggers", label: "Triggers", icon: Settings },
  { to: "/admin", label: "Admin", icon: Shield, adminOnly: true },
];

export default function AppShell() {
  const navigate = useNavigate();
  const clearSession = useAuthStore((state) => state.clearSession);
  const user = useAuthStore((state) => state.user);

  return (
    <Box className="min-h-screen bg-slate-950 text-slate-100">
      <AppBar position="sticky" sx={{ bgcolor: "#0f172a", borderBottom: "1px solid #1e293b" }}>
        <Toolbar className="mx-auto flex w-full max-w-7xl items-center justify-between">
          <Box className="flex items-center gap-3">
            <Waves size={20} />
            <Typography variant="h6" component="span" sx={{ fontWeight: 700 }}>
              WatchTower Console
            </Typography>
          </Box>
          <Box className="flex items-center gap-2">
            {navItems
              .filter((item) => !item.adminOnly || user?.is_admin)
              .map((item) => {
                const Icon = item.icon;
                return (
                  <Button
                    key={item.to}
                    component={NavLink}
                    to={item.to}
                    color="inherit"
                    startIcon={<Icon size={16} />}
                    sx={{ textTransform: "none" }}
                  >
                    {item.label}
                  </Button>
                );
              })}
            <Button
              color="inherit"
              startIcon={<LogOut size={16} />}
              sx={{ textTransform: "none" }}
              onClick={() => {
                clearSession();
                navigate("/login", { replace: true });
              }}
            >
              Logout
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" className="py-8">
        <Outlet />
      </Container>
    </Box>
  );
}
