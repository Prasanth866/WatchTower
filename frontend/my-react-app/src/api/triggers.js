import { apiClient } from "./client";

export async function listTriggers() {
  const { data } = await apiClient.get("/triggers/");
  return data;
}

export async function createTrigger(payload) {
  const { data } = await apiClient.post("/triggers/", payload);
  return data;
}

export async function updateTrigger(triggerId, payload) {
  const { data } = await apiClient.patch(`/triggers/${triggerId}`, payload);
  return data;
}

export async function deleteTrigger(triggerId) {
  await apiClient.delete(`/triggers/${triggerId}`);
}
