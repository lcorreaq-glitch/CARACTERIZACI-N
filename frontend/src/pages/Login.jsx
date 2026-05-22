import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { GraduationCap, ArrowRight, Loader2 } from "lucide-react";

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("lcorreaq@gmail.com");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  if (user) {
    return <Navigate to={user.must_change_password ? "/change-password" : "/"} replace />;
  }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const u = await login(email, password);
      toast.success(`Bienvenido, ${u.full_name}`);
      navigate(u.must_change_password ? "/change-password" : "/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error de inicio de sesión");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-2 bg-background">
      {/* Left: form */}
      <div className="flex flex-col justify-between p-8 md:p-14" data-testid="login-form-panel">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 grid place-items-center bg-[#0033A0] text-white rounded">
            <GraduationCap className="w-5 h-5" />
          </div>
          <div>
            <div className="font-display font-black tracking-tight text-base leading-none">IU Digital</div>
            <div className="label-eyebrow leading-none mt-1">de Antioquia</div>
          </div>
        </div>

        <div className="max-w-md w-full mx-auto md:mx-0">
          <p className="label-eyebrow mb-3">Plataforma analítica institucional</p>
          <h1 className="font-display font-black text-4xl md:text-5xl leading-[1.05] tracking-tighter mb-3">
            Caracterización y analítica académica
          </h1>
          <p className="text-muted-foreground text-sm md:text-base mb-10">
            Acceso restringido a personal institucional autorizado. Toda actividad queda registrada.
          </p>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <Label className="label-eyebrow mb-2 block">Correo institucional</Label>
              <Input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="usuario@iudigital.edu.co"
                className="h-11 rounded-sm"
                data-testid="login-email-input"
              />
            </div>
            <div>
              <Label className="label-eyebrow mb-2 block">Contraseña</Label>
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-11 rounded-sm"
                data-testid="login-password-input"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white text-sm font-medium tracking-wide"
              data-testid="login-submit-button"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Ingresar <ArrowRight className="ml-2 w-4 h-4" /></>}
            </Button>
          </form>

          <p className="text-xs text-muted-foreground mt-8">
            ¿Olvidó su contraseña? Solicite restablecimiento al administrador del sistema.
          </p>
        </div>

        <div className="mono text-[10px] text-muted-foreground tracking-wider uppercase">
          v1.0.0 · IU Digital de Antioquia © 2026
        </div>
      </div>

      {/* Right: hero image */}
      <div className="hidden md:block relative overflow-hidden border-l border-border">
        <img
          src="https://static.prod-images.emergentagent.com/jobs/50acd41d-6371-4d12-97eb-aa998af0d717/images/a6d3a263ce8d1ae97eba0273486fcc808dcb272ea7c882bf07eeac9923aa15a2.png"
          alt="Campus"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-tr from-[#0033A0]/55 via-transparent to-[#FFCD00]/25" />
        <div className="absolute inset-x-0 bottom-0 p-10 text-white">
          <div className="grid grid-cols-3 gap-6 max-w-xl">
            <div>
              <div className="kpi-num text-3xl">12.9K</div>
              <div className="text-xs uppercase tracking-widest opacity-80">Estudiantes</div>
            </div>
            <div>
              <div className="kpi-num text-3xl">17</div>
              <div className="text-xs uppercase tracking-widest opacity-80">Programas</div>
            </div>
            <div>
              <div className="kpi-num text-3xl">125</div>
              <div className="text-xs uppercase tracking-widest opacity-80">Municipios</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
