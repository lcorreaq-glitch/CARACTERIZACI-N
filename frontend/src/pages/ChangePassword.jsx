import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import api from "@/lib/api";
import { toast } from "sonner";
import { Loader2, ShieldCheck } from "lucide-react";

export default function ChangePassword() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (next.length < 6) return toast.error("Mínimo 6 caracteres");
    if (next !== confirm) return toast.error("Las contraseñas no coinciden");
    setLoading(true);
    try {
      await api.post("/auth/change-password", { current_password: current, new_password: next });
      const updated = { ...user, must_change_password: false };
      localStorage.setItem("iud_user", JSON.stringify(updated));
      setUser(updated);
      toast.success("Contraseña actualizada");
      navigate("/");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid place-items-center bg-background p-6">
      <div className="w-full max-w-md">
        <div className="dense-card p-7 md:p-9">
          <div className="flex items-center gap-3 mb-7">
            <div className="h-10 w-10 grid place-items-center bg-[#FFCD00] text-black rounded">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <p className="label-eyebrow">Seguridad</p>
              <h1 className="font-display font-black text-xl leading-none">Cambio de contraseña</h1>
            </div>
          </div>
          <p className="text-sm text-muted-foreground mb-6">
            Es su primer ingreso. Por política institucional debe definir una nueva contraseña.
          </p>
          <form onSubmit={submit} className="space-y-4">
            <div>
              <Label className="label-eyebrow mb-2 block">Contraseña actual</Label>
              <Input type="password" required value={current} onChange={(e) => setCurrent(e.target.value)} className="h-11 rounded-sm" data-testid="cp-current-input" />
            </div>
            <div>
              <Label className="label-eyebrow mb-2 block">Nueva contraseña</Label>
              <Input type="password" required value={next} onChange={(e) => setNext(e.target.value)} className="h-11 rounded-sm" data-testid="cp-new-input" />
            </div>
            <div>
              <Label className="label-eyebrow mb-2 block">Confirmar</Label>
              <Input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} className="h-11 rounded-sm" data-testid="cp-confirm-input" />
            </div>
            <Button type="submit" disabled={loading} className="w-full h-11 rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="cp-submit-button">
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Actualizar contraseña"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
