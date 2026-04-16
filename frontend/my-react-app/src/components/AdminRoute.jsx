import { Navigate } from "react-router-dom";
import { useAuthStore } from "../store/authStore";

export default function AdminRoute({ children }) {
  const user = useAuthStore((state) => state.user);

  if (!user?.is_admin) {
    return <Navigate to="/" replace />;
  }

  return children;
}
