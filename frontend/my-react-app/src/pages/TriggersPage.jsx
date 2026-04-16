import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Grid,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTrigger, deleteTrigger, listTriggers, updateTrigger } from "../api/triggers";
import { listTopics } from "../api/topics";
import { formatDate } from "../lib/formatters";

export default function TriggersPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    topic: "",
    threshold_value: "",
    threshold_direction: "above",
    cooldown_minutes: 60,
    notification_count: 5,
  });

  const triggersQuery = useQuery({ queryKey: ["triggers"], queryFn: listTriggers });
  const topicsQuery = useQuery({ queryKey: ["topics"], queryFn: listTopics });

  const createMutation = useMutation({
    mutationFn: createTrigger,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["triggers"] });
      setForm((prev) => ({ ...prev, threshold_value: "" }));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => updateTrigger(id, payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["triggers"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTrigger,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["triggers"] }),
  });

  const formError = useMemo(() => {
    if (!form.topic) {
      return "Topic is required";
    }
    if (!form.threshold_value) {
      return "Threshold is required";
    }
    return "";
  }, [form]);

  if (triggersQuery.isLoading || topicsQuery.isLoading) {
    return (
      <Box className="flex items-center justify-center py-20">
        <CircularProgress />
      </Box>
    );
  }

  if (triggersQuery.isError || topicsQuery.isError) {
    return <Alert severity="error">Failed to load triggers.</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Card className="rounded-2xl border border-slate-800 bg-slate-900">
        <CardContent className="space-y-3">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Create Trigger
          </Typography>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <TextField
                fullWidth
                select
                label="Topic"
                value={form.topic}
                onChange={(e) => setForm((prev) => ({ ...prev, topic: e.target.value }))}
              >
                {topicsQuery.data?.map((topic) => (
                  <MenuItem key={topic.name} value={topic.name}>
                    {topic.name}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <TextField
                fullWidth
                label="Threshold"
                type="number"
                value={form.threshold_value}
                onChange={(e) => setForm((prev) => ({ ...prev, threshold_value: e.target.value }))}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 2 }}>
              <TextField
                fullWidth
                select
                label="Direction"
                value={form.threshold_direction}
                onChange={(e) => setForm((prev) => ({ ...prev, threshold_direction: e.target.value }))}
              >
                <MenuItem value="above">Above</MenuItem>
                <MenuItem value="below">Below</MenuItem>
              </TextField>
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <Button
                className="h-full w-full"
                variant="contained"
                disabled={Boolean(formError) || createMutation.isPending}
                onClick={() =>
                  createMutation.mutate({
                    ...form,
                    threshold_value: Number(form.threshold_value),
                  })
                }
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </Button>
            </Grid>
          </Grid>
          {formError ? <Alert severity="warning">{formError}</Alert> : null}
        </CardContent>
      </Card>

      <Card className="rounded-2xl border border-slate-800 bg-slate-900">
        <CardContent className="space-y-2">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Existing Triggers
          </Typography>
          {triggersQuery.data?.length === 0 ? (
            <Typography color="text.secondary">No triggers yet.</Typography>
          ) : (
            triggersQuery.data.map((trigger) => (
              <Box
                key={trigger.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-800 px-3 py-2"
              >
                <Stack>
                  <Typography sx={{ fontWeight: 700 }}>
                    {trigger.topic} {trigger.threshold_direction} {trigger.threshold_value}
                  </Typography>
                  <Typography color="text.secondary" variant="body2">
                    Created {formatDate(trigger.created_at)}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2">Active</Typography>
                  <Switch
                    checked={Boolean(trigger.is_active)}
                    onChange={(e) =>
                      updateMutation.mutate({ id: trigger.id, payload: { is_active: e.target.checked } })
                    }
                  />
                  <Button
                    color="error"
                    variant="outlined"
                    onClick={() => deleteMutation.mutate(trigger.id)}
                  >
                    Delete
                  </Button>
                </Stack>
              </Box>
            ))
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
