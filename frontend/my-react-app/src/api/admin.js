import { apiClient } from "./client";

export async function getAdminStats() {
  const { data } = await apiClient.get("/admin/stats");
  return data;
}

export async function listAdminUsers(skip = 0, limit = 25) {
  const { data } = await apiClient.get("/admin/users", { params: { skip, limit } });
  return data;
}

export async function toggleAdmin(userId) {
  const { data } = await apiClient.patch(`/admin/users/${userId}/toggle-admin`);
  return data;
}

export async function deleteAdminUser(userId) {
  await apiClient.delete(`/admin/users/${userId}`);
}

export async function listAdminSubscriptions(skip = 0, limit = 25) {
  const { data } = await apiClient.get("/admin/subscriptions", { params: { skip, limit } });
  return data;
}

export async function listAdminTriggers(skip = 0, limit = 25, activeOnly = false) {
  const { data } = await apiClient.get("/admin/triggers", {
    params: { skip, limit, active_only: activeOnly },
  });
  return data;
}

export async function getConnectionCounts() {
  const { data } = await apiClient.get("/admin/connections");
  return data;
}
