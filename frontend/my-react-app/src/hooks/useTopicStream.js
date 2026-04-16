import { useEffect, useMemo, useState } from "react";
import { WS_BASE_URL } from "../config/api";

export function useTopicStream(topic, token) {
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const wsUrl = useMemo(() => {
    if (!topic || !token) {
      return null;
    }
    const encodedTopic = encodeURIComponent(topic);
    const encodedToken = encodeURIComponent(token);
    return `${WS_BASE_URL}/ws/${encodedTopic}?token=${encodedToken}`;
  }, [topic, token]);

  useEffect(() => {
    if (!wsUrl) {
      return undefined;
    }

    let ws;
    let reconnectTimer;
    let shouldReconnect = true;
    let attempts = 0;

    const connect = () => {
      setStatus("connecting");
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        attempts = 0;
        setStatus("connected");
        setError(null);
      };

      ws.onmessage = (message) => {
        try {
          const payload = JSON.parse(message.data);
          if (payload.type === "ping") {
            return;
          }
          setEvents((prev) => [...prev.slice(-119), payload]);
        } catch {
          setError("Malformed realtime payload");
        }
      };

      ws.onerror = () => {
        setStatus("error");
      };

      ws.onclose = () => {
        if (!shouldReconnect) {
          return;
        }
        setStatus("reconnecting");
        const delay = Math.min(1000 * 2 ** attempts, 15000);
        attempts += 1;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
      if (ws) {
        ws.close();
      }
    };
  }, [wsUrl]);

  return { events, status, error };
}
