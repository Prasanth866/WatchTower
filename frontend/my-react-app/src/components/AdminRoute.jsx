import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export default function AdminRoute({ children }) {
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);

  if (!token) {
    return <Navigate to="/admin/login" replace />;
  }

  if (!user?.is_admin) {
    return <Navigate to="/admin/login" replace />;
  }

  return children;
}
