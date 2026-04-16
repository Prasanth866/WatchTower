import { useMemo } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Alert, Box, Card, CardContent, Chip, CircularProgress, Stack, Typography } from "@mui/material";
import { getTopicHistory } from "../api/topics";
import { useAuthStore } from "../store/authStore";
import { useTopicStream } from "../hooks/useTopicStream";
import { formatDate, formatNumber } from "../lib/formatters";

export default function TopicPage() {
  const { topicId } = useParams();
  const token = useAuthStore((state) => state.token);
  const topic = decodeURIComponent(topicId || "");

  const historyQuery = useQuery({
    queryKey: ["topic-history", topic],
    queryFn: () => getTopicHistory(topic, 120),
    enabled: Boolean(topic),
  });

  const stream = useTopicStream(topic, token);

  const mergedEvents = useMemo(() => {
    const history = historyQuery.data || [];
    const realtime = stream.events || [];
    return [...history, ...realtime].slice(-120).reverse();
  }, [historyQuery.data, stream.events]);

  if (historyQuery.isLoading) {
    return (
      <Box className="flex items-center justify-center py-20">
        <CircularProgress />
      </Box>
    );
  }

  if (historyQuery.isError) {
    return <Alert severity="error">Failed to load topic history.</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Card className="rounded-2xl border border-slate-800 bg-slate-900">
        <CardContent>
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {topic}
            </Typography>
            <Chip label={`WebSocket: ${stream.status}`} color={stream.status === "connected" ? "success" : "warning"} />
          </Stack>
          {stream.error ? <Alert severity="warning" className="mt-3">{stream.error}</Alert> : null}
        </CardContent>
      </Card>

      <Card className="rounded-2xl border border-slate-800 bg-slate-900">
        <CardContent className="space-y-2">
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            Latest Events
          </Typography>
          {mergedEvents.length === 0 ? (
            <Typography color="text.secondary">No events yet.</Typography>
          ) : (
            mergedEvents.map((event, idx) => (
              <Box
                key={`${event.id || idx}-${event.timestamp}`}
                className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2"
              >
                <Typography>{formatDate(event.timestamp)}</Typography>
                <Typography sx={{ fontWeight: 700 }}>{formatNumber(event.value)} {event.unit || ""}</Typography>
              </Box>
            ))
          )}
        </CardContent>
      </Card>
    </Stack>
  );
}
