import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { ArrowRight, Loader2 } from "lucide-react";

/**
 * Diseño alineado con la "Hoja de ruta para profesores" — IU Digital de Antioquia.
 * - Foto institucional (hero) con overlay oscuro sutil
 * - Tipografía blanca en display + acento amarillo (#FFCD00) al estilo portada
 * - Tag "digitalidad próxima" (speech-bubble amarillo)
 * - Logo institucional circular con anillos azul / rojo / amarillo
 */
export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [authError, setAuthError] = useState(false);

  if (user) {
    return <Navigate to={user.must_change_password ? "/change-password" : "/"} replace />;
  }

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setAuthError(false);
    try {
      const u = await login(email, password);
      toast.success(`Bienvenido, ${u.full_name}`);
      navigate(u.must_change_password ? "/change-password" : "/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error de inicio de sesión");
      setAuthError(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-[1fr_1.15fr] bg-[#FAF7EE]" data-testid="login-page">
      {/* ============ Left: FORM ============ */}
      <div className="relative flex flex-col justify-between p-8 md:p-14 bg-[#FAF7EE]" data-testid="login-form-panel">
        {/* Decorative dots (top-left, matching PDF branding) */}
        <div className="absolute top-8 left-8 flex gap-1.5" aria-hidden>
          <span className="w-2.5 h-2.5 rounded-full bg-[#E3000F]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#FFCD00]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#0033A0]" />
        </div>

        {/* Logo mark (top-right in small breakpoint) */}
        <div className="flex justify-end items-start pt-4">
          <InstitutionalLogo compact />
        </div>

        <div className="max-w-md w-full mx-auto md:mx-0 py-8">
          <p className="label-eyebrow mb-3 text-[#0033A0]">Plataforma analítica institucional</p>
          <h1 className="font-display font-black text-4xl md:text-5xl leading-[1.02] tracking-tighter mb-2 text-[#111]">
            Caracterización <br /> y analítica
            <span className="block text-[#0033A0]">académica</span>
          </h1>
          {/* Amarillo accent underline like the PDF cover */}
          <div className="h-1.5 w-24 bg-[#FFCD00] rounded-full mb-6" aria-hidden />

          <p className="text-muted-foreground text-sm md:text-base mb-8 max-w-sm">
            Bienvenido al Aplicativo de Caracterización y Analítica Académica. Ingresa con tus datos institucionales para continuar.
          </p>

          <form onSubmit={submit} className="space-y-5" data-testid="login-form">
            <div>
              <Label className="label-eyebrow mb-2 block">Usuario</Label>
              <Input
                type="text"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Cédula o correo institucional"
                className="h-12 rounded-sm bg-white border-[#0033A0]/15 focus-visible:ring-[#0033A0]/30"
                data-testid="login-email-input"
                autoComplete="username"
              />
              <p className="text-[10px] text-muted-foreground mt-1.5">
                Profesores: ingresa con tu <b>número de identificación</b>. Personal administrativo: ingresa con tu correo institucional.
              </p>
            </div>
            <div>
              <Label className="label-eyebrow mb-2 block">Contraseña</Label>
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="h-12 rounded-sm bg-white border-[#0033A0]/15 focus-visible:ring-[#0033A0]/30"
                data-testid="login-password-input"
                autoComplete="current-password"
              />
              {authError && (
                <p className="text-[10px] text-[#E3000F] mt-1.5" data-testid="login-auth-hint">
                  Si tu navegador auto-llenó una contraseña anterior, bórrala y escríbela nuevamente.
                </p>
              )}
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-sm bg-[#0033A0] hover:bg-[#002478] text-white text-sm font-semibold tracking-wide shadow-md transition-all"
              data-testid="login-submit-button"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <>Ingresar <ArrowRight className="ml-2 w-4 h-4" /></>}
            </Button>
          </form>

          <p className="text-xs text-muted-foreground mt-8">
            ¿Olvidaste tu contraseña? Solicita apoyo para restablecerla.
          </p>
        </div>

        {/* Footer: URL con marca de resaltado amarillo (como en la portada) */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
          <div className="inline-flex items-center relative">
            <span className="absolute inset-0 -mx-2 my-1 bg-[#FFCD00] rounded-full -z-0" aria-hidden />
            <span className="relative z-10 mono text-[11px] tracking-wide text-black font-semibold px-2">
              www.iudigital.edu.co
            </span>
          </div>
          <div className="mono text-[10px] text-muted-foreground tracking-wider uppercase">
            v1.0.0 · IU Digital de Antioquia © 2026
          </div>
        </div>
      </div>

      {/* ============ Right: HERO (portada style) ============ */}
      <div className="hidden md:block relative overflow-hidden" data-testid="login-hero-panel">
        {/* Dark background base */}
        <div className="absolute inset-0 bg-[#1a1a1a]" />
        {/* People photo */}
        <img
          src="/img/hero-people.jpg"
          alt="Comunidad IU Digital de Antioquia"
          className="absolute inset-0 w-full h-full object-cover object-[70%_center]"
        />
        {/* Dark gradient overlay (bottom to top) so headline reads well */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/25 to-black/55" />

        {/* "digitalidad próxima" speech-bubble tag (top-right) */}
        <div className="absolute top-8 right-8 z-10">
          <SpeechBubble>digitalidad próxima</SpeechBubble>
        </div>

        {/* Big headline over image (portada style) */}
        <div className="absolute inset-x-0 top-16 md:top-24 px-8 md:px-14 z-10">
          <h2 className="font-display font-black text-white text-5xl md:text-6xl xl:text-7xl leading-[0.98] tracking-tighter drop-shadow-lg">
            Cada estudiante,<br />un territorio
          </h2>
          <p className="mt-3 text-2xl md:text-3xl font-display font-bold text-[#FFCD00] tracking-tight drop-shadow">
            IU Digital de Antioquia
          </p>
        </div>

        {/* KPIs strip (bottom) */}
        <div className="absolute inset-x-0 bottom-0 px-8 md:px-14 pb-8 md:pb-10 z-10">
          <div className="grid grid-cols-3 gap-4 max-w-xl bg-black/45 backdrop-blur-sm rounded-sm p-4 border border-white/10">
            <KpiTile value="16.4K" label="Estudiantes" />
            <KpiTile value="34" label="Programas" />
            <KpiTile value="573" label="Municipios" />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ============ Subcomponents ============ */

function KpiTile({ value, label }) {
  return (
    <div>
      <div className="kpi-num text-3xl text-white font-display font-black tracking-tight">{value}</div>
      <div className="text-[10px] uppercase tracking-widest text-white/75 mt-0.5">{label}</div>
    </div>
  );
}

/** Speech-bubble tag ala "digitalidad próxima" */
function SpeechBubble({ children }) {
  return (
    <div className="relative inline-block">
      <div className="bg-white text-[#0033A0] px-4 py-1.5 rounded-full font-semibold text-sm shadow-lg">
        {children}
      </div>
      {/* Tail */}
      <div className="absolute -bottom-1.5 left-6 w-3 h-3 bg-white rotate-45 shadow-sm" />
    </div>
  );
}

/**
 * IU Digital logo circular con anillos color institucional
 * (aproxima el logotipo de la portada: círculo con arco azul/rojo/amarillo).
 */
function InstitutionalLogo({ compact = false }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 60 60" className={compact ? "w-11 h-11" : "w-14 h-14"} aria-hidden>
        {/* Yellow ring (bottom) */}
        <path d="M 8 34 A 22 22 0 0 0 52 34" stroke="#FFCD00" strokeWidth="4" fill="none" strokeLinecap="round" />
        {/* Blue ring (top-left) */}
        <path d="M 8 30 A 22 22 0 0 1 30 8" stroke="#0033A0" strokeWidth="4" fill="none" strokeLinecap="round" />
        {/* Red ring (top-right) */}
        <path d="M 30 8 A 22 22 0 0 1 52 30" stroke="#E3000F" strokeWidth="4" fill="none" strokeLinecap="round" />
        {/* Center IU */}
        <text x="30" y="37" textAnchor="middle" fontSize="16" fontWeight="900" fill="#111" fontFamily="Cabinet Grotesk, sans-serif">IU</text>
      </svg>
      <div className={compact ? "text-[10px] leading-tight" : "text-xs leading-tight"}>
        <div className="font-display font-black text-[#0033A0] tracking-tight">IU Digital</div>
        <div className="text-muted-foreground uppercase tracking-widest text-[9px]">de Antioquia</div>
      </div>
    </div>
  );
}
