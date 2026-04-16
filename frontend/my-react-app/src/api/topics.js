import { apiClient } from "./client";

export async function listTopics() {
  const { data } = await apiClient.get("/topics/");
  return data;
}

export async function getTopicHistory(topic, limit = 120) {
  const { data } = await apiClient.get(`/topics/${encodeURIComponent(topic)}/history`, {
    params: { limit },
  });
  return data;
}
