import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import api from "@/lib/api";
import { toast } from "sonner";
import { Loader2, ShieldCheck, Eye, EyeOff, Info } from "lucide-react";

export default function ChangePassword() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [show, setShow] = useState({ current: false, next: false, confirm: false });

  const isProfesor = user?.role === "profesor";
  const cedula = user?.documento || "";

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
      // Si el error es contraseña actual incorrecta, borro el campo para forzar nuevo tipeo (evita autofill fantasma).
      if (typeof detail === "string" && detail.toLowerCase().includes("actual")) {
        setCurrent("");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-background p-6">
      <div className="w-full max-w-md">
        <div className="dense-card p-7 md:p-9">
          <div className="flex items-center gap-3 mb-6">
            <div className="h-10 w-10 grid place-items-center bg-[#FFCD00] text-black rounded">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="label-eyebrow">Seguridad</p>
              <h1 className="font-display font-black text-xl leading-none">Cambio de contraseña</h1>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            Es su primer ingreso. Por política institucional debe definir una nueva contraseña.
          </p>

          {isProfesor && cedula && (
            <Alert className="mb-5 border-blue-300 bg-blue-50/60 dark:bg-blue-500/5">
              <Info className="w-4 h-4 text-blue-600" />
              <AlertDescription className="text-xs">
                Su <b>contraseña actual</b> es su <b>número de cédula</b> (<code className="font-mono">{cedula}</code>).
                Ingréselo tal cual, sin espacios ni puntos. Si el navegador auto-llenó otro valor,
                bórrelo y digítelo manualmente.
              </AlertDescription>
            </Alert>
          )}

          {/* Trampa para evitar que Chrome autofill "current-password" con contraseñas guardadas de otras sesiones. */}
          <form
            onSubmit={submit}
            className="space-y-4"
            autoComplete="off"
            data-testid="cp-form"
          >
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
              // Autocomplete new-password para evitar que el navegador rellene con clave vieja
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

            {/* Indicadores de validación en vivo */}
            <ul className="text-[11px] text-muted-foreground space-y-0.5 pl-1">
              <li className={next.length >= 8 ? "text-emerald-600" : ""}>• Al menos 8 caracteres</li>
              <li className={next && next !== current ? "text-emerald-600" : ""}>• Diferente a la contraseña actual</li>
              <li className={next && next === confirm ? "text-emerald-600" : ""}>• Confirmación coincide</li>
            </ul>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-11 rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white"
              data-testid="cp-submit-button"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Actualizar contraseña"}
            </Button>
          </form>
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
          className="h-11 rounded-sm pr-10"
          data-testid={testId}
        />
        <button
          type="button"
          onClick={onToggle}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          tabIndex={-1}
          aria-label={show ? "Ocultar" : "Mostrar"}
        >
          {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
        </button>
      </div>
    </div>
  );
}
