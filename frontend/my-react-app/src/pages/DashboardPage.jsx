import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Stack,
  Typography,
} from "@mui/material";
import { ArrowRight, BellRing } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { listTopics } from "../api/topics";
import { listSubscriptions, subscribeTopic, unsubscribeTopic } from "../api/subscriptions";
import { useAuthStore } from "../store/authStore";

export default function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const user = useAuthStore((state) => state.user);

  const topicsQuery = useQuery({ queryKey: ["topics"], queryFn: listTopics });
  const subsQuery = useQuery({ queryKey: ["subscriptions"], queryFn: listSubscriptions });

  const subscribeMutation = useMutation({
    mutationFn: subscribeTopic,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscriptions"] }),
  });

  const unsubscribeMutation = useMutation({
    mutationFn: unsubscribeTopic,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["subscriptions"] }),
  });

  if (topicsQuery.isLoading || subsQuery.isLoading) {
    return (
      <Box className="flex items-center justify-center py-20">
        <CircularProgress />
      </Box>
    );
  }

  if (topicsQuery.isError || subsQuery.isError) {
    return <Alert severity="error">Failed to load dashboard data.</Alert>;
  }

  const subscriptions = new Set(subsQuery.data || []);

  return (
    <Stack spacing={4}>
      <Card className="rounded-2xl border border-slate-800 bg-slate-900/70">
        <CardContent>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            Welcome back{user?.email ? `, ${user.email}` : ""}
          </Typography>
          <Typography color="text.secondary" className="mt-2">
            Monitor topics, manage triggers, and watch live events in real time.
          </Typography>
        </CardContent>
      </Card>

      <Grid container spacing={2}>
        {topicsQuery.data?.map((topic) => {
          const subscribed = subscriptions.has(topic.name);
          return (
            <Grid size={{ xs: 12, md: 6, lg: 4 }} key={topic.name}>
              <Card className="h-full rounded-2xl border border-slate-800 bg-slate-900">
                <CardContent className="space-y-3">
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6" sx={{ fontWeight: 700 }}>
                      {topic.name}
                    </Typography>
                    <Chip label={topic.unit} size="small" color="info" />
                  </Stack>

                  <Typography color="text.secondary">{topic.description || "Live topic stream"}</Typography>
                  <Typography color="text.secondary" variant="body2">
                    Update interval: every {topic.interval_seconds}s
                  </Typography>

                  <Stack direction="row" spacing={1}>
                    <Button
                      variant={subscribed ? "outlined" : "contained"}
                      size="small"
                      startIcon={<BellRing size={14} />}
                      onClick={() =>
                        subscribed
                          ? unsubscribeMutation.mutate(topic.name)
                          : subscribeMutation.mutate(topic.name)
                      }
                    >
                      {subscribed ? "Unsubscribe" : "Subscribe"}
                    </Button>
                    <Button
                      variant="text"
                      size="small"
                      endIcon={<ArrowRight size={14} />}
                      onClick={() => navigate(`/topics/${encodeURIComponent(topic.name)}`)}
                    >
                      Open
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>
    </Stack>
  );
}
