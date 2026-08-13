import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import api from "@/lib/api";
import { toast } from "sonner";
import { Loader2, ShieldCheck, Eye, EyeOff, Info, LogOut } from "lucide-react";

/**
 * Cambio de contraseña — diseño alineado con la portada institucional de la IU Digital.
 * Split screen: form (izq, fondo crema) + hero fotográfico (der, con acento amarillo).
 */
export default function ChangePassword() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState({ current: false, next: false, confirm: false });

  const isProfesor = user?.role === "profesor";
  const cedula = user?.documento || "";

  const handleLogout = () => {
    if (typeof logout === "function") {
      logout();
    } else {
      localStorage.removeItem("iud_user");
      localStorage.removeItem("iud_token");
      setUser(null);
    }
    navigate("/login", { replace: true });
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!current) return toast.error("Ingrese su contraseña actual");
    if (next.length < 8) return toast.error("La nueva contraseña debe tener al menos 8 caracteres");
    if (next === current) return toast.error("La nueva contraseña debe ser diferente a la actual");
    if (next !== confirm) return toast.error("Las contraseñas nueva y confirmación no coinciden");
    setLoading(true);
    try {
      await api.post("/auth/change-password", { current_password: current, new_password: next });
      const updated = { ...user, must_change_password: false };
      localStorage.setItem("iud_user", JSON.stringify(updated));
      setUser(updated);
      toast.success("Contraseña actualizada correctamente");
      navigate(isProfesor ? "/mi-panel" : "/");
    } catch (err) {
      const detail = err?.response?.data?.detail || "Error al actualizar la contraseña";
      toast.error(detail);
      if (typeof detail === "string" && detail.toLowerCase().includes("actual")) {
        setCurrent("");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid md:grid-cols-[1fr_1fr] bg-[#FAF7EE]" data-testid="cp-page">
      {/* Left: FORM */}
      <div className="relative flex flex-col justify-between p-8 md:p-14">
        {/* Dots branding */}
        <div className="absolute top-8 left-8 flex gap-1.5" aria-hidden>
          <span className="w-2.5 h-2.5 rounded-full bg-[#E3000F]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#FFCD00]" />
          <span className="w-2.5 h-2.5 rounded-full bg-[#0033A0]" />
        </div>

        <div className="flex justify-between items-start pt-4">
          <div className="flex items-center gap-3">
            <div className="h-11 w-11 grid place-items-center bg-[#FFCD00] text-black rounded shadow-sm">
              <ShieldCheck className="w-5 h-5" strokeWidth={2.5} />
            </div>
            <div>
              <p className="label-eyebrow text-[#0033A0]">Seguridad</p>
              <h1 className="font-display font-black text-lg leading-none tracking-tight">Cambio de contraseña</h1>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="text-[10px] uppercase tracking-widest text-muted-foreground hover:text-[#0033A0] transition-soft flex items-center gap-1"
            data-testid="cp-logout-btn"
          >
            <LogOut className="w-3 h-3" /> Salir
          </button>
        </div>

        <div className="max-w-md w-full mx-auto md:mx-0 py-6">
          <p className="label-eyebrow mb-2 text-[#0033A0]">Primer ingreso · Política institucional</p>
          <h2 className="font-display font-black text-3xl md:text-4xl leading-[1.04] tracking-tighter mb-2 text-[#111]">
            Defina su nueva
            <span className="block text-[#0033A0]">contraseña</span>
          </h2>
          <div className="h-1.5 w-20 bg-[#FFCD00] rounded-full mb-5" aria-hidden />

          {user?.full_name && (
            <p className="text-[11px] text-muted-foreground mb-4">
              Ingresado como <b className="text-foreground">{user.full_name}</b>
              {cedula ? <> · cédula <code className="font-mono">{cedula}</code></> : null}
              {user.email ? <> · {user.email}</> : null}
            </p>
          )}

          {isProfesor && cedula && (
            <Alert className="mb-5 border-[#0033A0]/30 bg-[#0033A0]/5">
              <Info className="w-4 h-4 text-[#0033A0]" />
              <AlertDescription className="text-xs">
                Su <b>contraseña actual</b> es su <b>número de cédula</b> (<code className="font-mono">{cedula}</code>).
                Ingréselo tal cual, sin espacios ni puntos. Si el navegador auto-llenó otro valor,
                bórrelo y digítelo manualmente.
              </AlertDescription>
            </Alert>
          )}
          {isProfesor && !cedula && (
            <Alert className="mb-5 border-amber-300 bg-amber-50/60">
              <Info className="w-4 h-4 text-amber-600" />
              <AlertDescription className="text-xs">
                Su usuario no tiene cédula registrada. Si no recuerda su contraseña, pulse <b>Salir</b>
                arriba y solicite reset al administrador.
              </AlertDescription>
            </Alert>
          )}

          <form
            onSubmit={submit}
            className="space-y-4"
            autoComplete="off"
            data-testid="cp-form"
          >
            {/* Anti-autofill trap */}
            <input type="text" name="_fake_user" autoComplete="username" style={{ display: "none" }} />
            <input type="password" name="_fake_pass" autoComplete="current-password" style={{ display: "none" }} />

            <PasswordField
              label="Contraseña actual"
              value={current}
              onChange={setCurrent}
              show={show.current}
              onToggle={() => setShow({ ...show, current: !show.current })}
              placeholder={isProfesor && cedula ? `Ej: ${cedula}` : ""}
              testId="cp-current-input"
              autoFocus
              autoComplete="new-password"
              name="_current_pwd"
            />

            <PasswordField
              label="Nueva contraseña (mínimo 8 caracteres)"
              value={next}
              onChange={setNext}
              show={show.next}
              onToggle={() => setShow({ ...show, next: !show.next })}
              placeholder="Elija una contraseña segura"
              testId="cp-new-input"
              autoComplete="new-password"
              name="_new_pwd"
            />

            <PasswordField
              label="Confirmar nueva contraseña"
              value={confirm}
              onChange={setConfirm}
              show={show.confirm}
              onToggle={() => setShow({ ...show, confirm: !show.confirm })}
              placeholder="Repita la contraseña nueva"
              testId="cp-confirm-input"
              autoComplete="new-password"
              name="_confirm_pwd"
            />

            <ul className="text-[11px] text-muted-foreground space-y-0.5 pl-1">
              <li className={next.length >= 8 ? "text-emerald-600" : ""}>• Al menos 8 caracteres</li>
              <li className={next && next !== current ? "text-emerald-600" : ""}>• Diferente a la contraseña actual</li>
              <li className={next && next === confirm ? "text-emerald-600" : ""}>• Confirmación coincide</li>
            </ul>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-12 rounded-sm bg-[#0033A0] hover:bg-[#002478] text-white font-semibold tracking-wide shadow-md mt-2"
              data-testid="cp-submit-button"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Actualizar contraseña"}
            </Button>
          </form>
        </div>

        {/* Footer branding highlight */}
        <div className="flex items-center relative w-fit">
          <span className="absolute inset-0 -mx-2 my-1 bg-[#FFCD00] rounded-full -z-0" aria-hidden />
          <span className="relative z-10 mono text-[11px] tracking-wide text-black font-semibold px-2">
            www.iudigital.edu.co
          </span>
        </div>
      </div>

      {/* Right: HERO */}
      <div className="hidden md:block relative overflow-hidden">
        <div className="absolute inset-0 bg-[#1a1a1a]" />
        <img
          src="/img/hero-people.jpg"
          alt="Comunidad IU Digital de Antioquia"
          className="absolute inset-0 w-full h-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-gradient-to-b from-black/72 via-black/30 to-black/60" />

        <div className="absolute top-8 right-8 z-10">
          <div className="relative inline-block">
            <div className="bg-white text-[#0033A0] px-4 py-1.5 rounded-full font-semibold text-sm shadow-lg">
              digitalidad próxima
            </div>
            <div className="absolute -bottom-1.5 left-6 w-3 h-3 bg-white rotate-45 shadow-sm" />
          </div>
        </div>

        <div className="absolute inset-x-0 top-16 md:top-24 px-8 md:px-14 z-10 max-w-xl">
          <p className="label-eyebrow text-white/85 mb-2">Bienvenido/a a la plataforma</p>
          <h3 className="font-display font-black text-white text-4xl md:text-5xl leading-[0.98] tracking-tighter drop-shadow-lg">
            Un solo paso<br />para comenzar
          </h3>
          <p className="mt-3 text-xl md:text-2xl font-display font-bold text-[#FFCD00] tracking-tight drop-shadow">
            Su seguridad es prioridad
          </p>
          <p className="mt-4 text-sm text-white/90 max-w-md leading-relaxed">
            Por política institucional, en su primer ingreso debe reemplazar la contraseña temporal
            por una personal y segura. Esta credencial protege el acceso a información académica
            sensible.
          </p>
        </div>

        {/* Bottom yellow band with mission */}
        <div className="absolute inset-x-0 bottom-0 z-10">
          <div className="bg-[#FFCD00] px-8 md:px-14 py-4 text-black">
            <p className="font-display font-bold text-sm md:text-base leading-tight">
              Educación pública, flexible y con presencia territorial.
            </p>
            <p className="text-xs opacity-80 mt-0.5">
              ORD No 74 de 2017 · Vigilada MinEducación
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function PasswordField({ label, value, onChange, show, onToggle, placeholder, testId, autoFocus, autoComplete, name }) {
  return (
    <div>
      <Label className="label-eyebrow mb-2 block">{label}</Label>
      <div className="relative">
        <Input
          type={show ? "text" : "password"}
          required
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          autoComplete={autoComplete || "off"}
          name={name}
          className="h-12 rounded-sm pr-10 bg-white border-[#0033A0]/15 focus-visible:ring-[#0033A0]/30"
          data-testid={testId}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-[#0033A0]"
          tabIndex={-1}
          aria-label={show ? "Ocultar" : "Mostrar"}
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}
