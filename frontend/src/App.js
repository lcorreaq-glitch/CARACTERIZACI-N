import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { Toaster } from "@/components/ui/sonner";
import Login from "@/pages/Login";
import ChangePassword from "@/pages/ChangePassword";
import AppLayout from "@/pages/AppLayout";
import Executive from "@/pages/Executive";
import Academic from "@/pages/Academic";
import Territorial from "@/pages/Territorial";
import Historical from "@/pages/Historical";
import Caracterizacion from "@/pages/Caracterizacion";
import Insights from "@/pages/Insights";
import Docente from "@/pages/Docente";
import Upload from "@/pages/Upload";
import Admin from "@/pages/Admin";
import Grupos from "@/pages/Grupos";
import Configuracion from "@/pages/Configuracion";
import "@/App.css";

function Protected({ children, requireAdmin = false }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) return <div className="min-h-screen grid place-items-center text-sm text-muted-foreground">Cargando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }
  if (requireAdmin && !["superadmin", "admin"].includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function IndexByRole() {
  const { user } = useAuth();
  if (user?.role === "profesor" || user?.role === "docente") return <Navigate to="/mi-panel" replace />;
  return <Executive />;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-right" richColors />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/change-password" element={
            <Protected>
              <ChangePassword />
            </Protected>
          } />
          <Route path="/" element={<Protected><AppLayout /></Protected>}>
            <Route index element={<IndexByRole />} />
            <Route path="mi-panel" element={<Docente />} />
            <Route path="caracterizacion" element={<Caracterizacion />} />
            <Route path="academico" element={<Academic />} />
            <Route path="territorial" element={<Territorial />} />
            <Route path="historico" element={<Historical />} />
            <Route path="insights" element={<Insights />} />
            <Route path="cargas" element={<Protected requireAdmin><Upload /></Protected>} />
            <Route path="grupos" element={<Protected requireAdmin><Grupos /></Protected>} />
            <Route path="admin" element={<Protected requireAdmin><Admin /></Protected>} />
            <Route path="configuracion" element={<Protected requireAdmin><Configuracion /></Protected>} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
