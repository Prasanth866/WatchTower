import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import {
  deleteAdminUser,
  getAdminStats,
  getConnectionCounts,
  listAdminSubscriptions,
  listAdminTriggers,
  listAdminUsers,
  toggleAdmin,
} from "../api/admin";

export default function AdminPage() {
  const queryClient = useQueryClient();

  const statsQuery = useQuery({ queryKey: ["admin-stats"], queryFn: getAdminStats });
  const usersQuery = useQuery({ queryKey: ["admin-users"], queryFn: () => listAdminUsers(0, 25) });
  const subscriptionsQuery = useQuery({
    queryKey: ["admin-subscriptions"],
    queryFn: () => listAdminSubscriptions(0, 25),
  });
  const triggersQuery = useQuery({
    queryKey: ["admin-triggers"],
    queryFn: () => listAdminTriggers(0, 25, false),
  });
  const connectionsQuery = useQuery({ queryKey: ["admin-connections"], queryFn: getConnectionCounts });

  const toggleMutation = useMutation({
    mutationFn: toggleAdmin,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAdminUser,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  if (
    statsQuery.isLoading ||
    usersQuery.isLoading ||
    subscriptionsQuery.isLoading ||
    triggersQuery.isLoading ||
    connectionsQuery.isLoading
  ) {
    return (
      <Box className="flex items-center justify-center py-20">
        <CircularProgress />
      </Box>
    );
  }

  if (
    statsQuery.isError ||
    usersQuery.isError ||
    subscriptionsQuery.isError ||
    triggersQuery.isError ||
    connectionsQuery.isError
  ) {
    return <Alert severity="error">Failed to load admin data.</Alert>;
  }

  const stats = statsQuery.data;

  return (
    <Stack spacing={3}>
      <Grid container spacing={2}>
        {Object.entries(stats).map(([label, value]) => (
          <Grid size={{ xs: 12, md: 6, lg: 2.4 }} key={label}>
            <Card className="rounded-2xl border border-slate-800 bg-slate-900">
              <CardContent>
                <Typography color="text.secondary" variant="body2">
                  {label}
                </Typography>
                <Typography variant="h5" sx={{ fontWeight: 700 }}>
                  {value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Card className="rounded-2xl border border-slate-800 bg-slate-900">
        <CardContent className="space-y-2">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Users
          </Typography>
          {usersQuery.data?.users?.map((user) => (
            <Box key={user.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 px-3 py-2">
              <Typography>{user.email}</Typography>
              <Stack direction="row" spacing={1}>
                <Button size="small" variant="outlined" onClick={() => toggleMutation.mutate(user.id)}>
                  {user.is_admin ? "Revoke admin" : "Make admin"}
                </Button>
                <Button size="small" color="error" variant="outlined" onClick={() => deleteMutation.mutate(user.id)}>
                  Delete
                </Button>
              </Stack>
            </Box>
          ))}
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card className="rounded-2xl border border-slate-800 bg-slate-900">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Connection Counts
              </Typography>
              <Divider className="my-2" />
              {Object.entries(connectionsQuery.data || {}).map(([topic, count]) => (
                <Typography key={topic}>{topic}: {count}</Typography>
              ))}
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card className="rounded-2xl border border-slate-800 bg-slate-900">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Latest Admin Data
              </Typography>
              <Divider className="my-2" />
              <Typography variant="body2" color="text.secondary">
                Subscriptions loaded: {subscriptionsQuery.data?.length || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Triggers loaded: {triggersQuery.data?.length || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
