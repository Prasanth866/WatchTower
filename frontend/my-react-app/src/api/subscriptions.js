import { apiClient } from "./client";

export async function listSubscriptions() {
  const { data } = await apiClient.get("/subscriptions/");
  return data;
}

export async function subscribeTopic(topic) {
  const { data } = await apiClient.post(`/subscriptions/${encodeURIComponent(topic)}`);
  return data;
}

export async function unsubscribeTopic(topic) {
  await apiClient.delete(`/subscriptions/${encodeURIComponent(topic)}`);
}
