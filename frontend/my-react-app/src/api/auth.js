import { apiClient } from "./client";

export async function registerUser(payload) {
  const { data } = await apiClient.post("/auth/register", payload);
  return data;
}

export async function loginUser({ email, password }) {
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const { data } = await apiClient.post("/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function fetchCurrentUser(token) {
  const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
  const { data } = await apiClient.get("/auth/me", { headers });
  return data;
}

export async function forgotPassword(email) {
  const { data } = await apiClient.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(payload) {
  const { data } = await apiClient.post("/auth/reset-password", payload);
  return data;
}

export async function updateNotificationPreference(emailNotifications) {
  const { data } = await apiClient.patch("/auth/notifications", {
    email_notifications: emailNotifications,
  });
  return data;
}
