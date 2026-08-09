import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { toast } from "sonner";
import {
  Mail, Bot, CheckCircle2, AlertTriangle, ExternalLink,
  Send, Users, Shield, Eye, EyeOff, Loader2, KeyRound,
} from "lucide-react";

export default function Configuracion() {
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";
  const [tab, setTab] = useState("smtp");
  const [overview, setOverview] = useState(null);

  useEffect(() => {
    api.get("/config/overview").then(r => setOverview(r.data)).catch(() => {});
  }, []);

  if (!isSuperadmin) {
    return (
      <div className="p-6" data-testid="config-not-allowed">
        <Alert variant="destructive">
          <Shield className="w-4 h-4" />
          <AlertTitle>Sin permiso</AlertTitle>
          <AlertDescription>Solo el Superadministrador puede acceder a Configuración.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="page-configuracion">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Configuración</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">
          Parámetros del sistema
        </h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-3xl">
          Configure el envío de correos institucionales (Gmail SMTP) y el proveedor de IA
          (Emergent Universal Key o Google Gemini propio). Los cambios se aplican inmediatamente.
        </p>
      </header>

      {overview && <OverviewCards data={overview} />}

      <Tabs value={tab} onValueChange={setTab} className="space-y-4">
        <TabsList className="rounded-sm">
          <TabsTrigger value="smtp" data-testid="tab-smtp"><Mail className="w-3.5 h-3.5 mr-2" />Correo (Gmail)</TabsTrigger>
          <TabsTrigger value="ai" data-testid="tab-ai"><Bot className="w-3.5 h-3.5 mr-2" />IA (Emergent / Gemini)</TabsTrigger>
          <TabsTrigger value="envios" data-testid="tab-envios"><Send className="w-3.5 h-3.5 mr-2" />Envío de credenciales</TabsTrigger>
        </TabsList>

        <TabsContent value="smtp"><SMTPPanel onSaved={() => api.get("/config/overview").then(r => setOverview(r.data))} /></TabsContent>
        <TabsContent value="ai"><AIPanel onSaved={() => api.get("/config/overview").then(r => setOverview(r.data))} /></TabsContent>
        <TabsContent value="envios"><EnviosPanel /></TabsContent>
      </Tabs>
    </div>
  );
}

function OverviewCards({ data }) {
  const cards = [
    { label: "SMTP", ok: data.smtp_enabled, hint: data.smtp_from || "no configurado", icon: Mail },
    { label: "IA activa", ok: data.ai_enabled, hint: `Proveedor: ${data.ai_provider}`, icon: Bot },
    { label: "Emergent Key", ok: data.emergent_key_present, hint: data.emergent_key_present ? "detectada" : "ausente", icon: KeyRound },
    { label: "Gemini Key", ok: data.gemini_key_present, hint: data.gemini_key_present ? "configurada" : "sin definir", icon: KeyRound },
    { label: "Docentes notificados", ok: data.docentes_credentials_sent > 0, hint: `${data.docentes_credentials_sent} / ${data.docentes_total}`, icon: Users },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {cards.map((c) => (
        <div key={c.label} className="dense-card p-3" data-testid={`overview-${c.label.toLowerCase().replace(/\s+/g, "-")}`}>
          <div className="flex items-center gap-2 mb-1">
            <c.icon className="w-3.5 h-3.5 text-muted-foreground" />
            <p className="label-eyebrow">{c.label}</p>
          </div>
          <div className="flex items-center gap-2">
            {c.ok
              ? <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              : <AlertTriangle className="w-4 h-4 text-amber-600" />}
            <span className="text-xs">{c.hint}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SMTPPanel({ onSaved }) {
  const [cfg, setCfg] = useState(null);
  const [testTo, setTestTo] = useState("");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showPw, setShowPw] = useState(false);

  const load = () => api.get("/config/smtp").then(r => setCfg(r.data));
  useEffect(() => { load(); }, []);

  if (!cfg) return <div className="p-4 text-sm text-muted-foreground">Cargando…</div>;

  const set = (k, v) => setCfg({ ...cfg, [k]: v });

  const save = async () => {
    setSaving(true);
    try {
      // Enviar solo lo que cambió, dejamos password si el usuario ingresó algo nuevo
      const payload = {
        smtp_host: cfg.smtp_host, smtp_port: cfg.smtp_port,
        smtp_user: cfg.smtp_user, smtp_from_name: cfg.smtp_from_name,
        smtp_enabled: !!cfg.smtp_enabled,
      };
      if (cfg._new_password) payload.smtp_password = cfg._new_password;
      const r = await api.patch("/config/smtp", payload);
      setCfg({ ...r.data, _new_password: "" });
      toast.success("Configuración SMTP guardada");
      onSaved?.();
    } catch (e) {
      toast.error("Error al guardar", { description: e.response?.data?.detail || e.message });
    } finally {
      setSaving(false);
    }
  };

  const sendTest = async () => {
    if (!testTo) { toast.error("Ingrese un correo destino"); return; }
    setTesting(true);
    try {
      const r = await api.post("/config/smtp/test", { to_email: testTo });
      toast.success(r.data.message || "Correo de prueba enviado");
    } catch (e) {
      toast.error("Fallo el envío de prueba", { description: e.response?.data?.detail || e.message });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Instrucciones */}
      <div className="dense-card p-5 lg:col-span-1 order-2 lg:order-1">
        <p className="label-eyebrow text-[#0033A0]">Instrucciones</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Cómo obtener el App Password de Gmail</h3>
        <ol className="text-xs space-y-3 text-muted-foreground list-decimal ml-4">
          <li>
            Inicie sesión en la cuenta institucional Gmail que hará de remitente
            (ej. <code>notificaciones@iudigital.edu.co</code>).
          </li>
          <li>
            Active la <b>verificación en 2 pasos</b> en{" "}
            <a className="text-[#0033A0] inline-flex items-center gap-1" href="https://myaccount.google.com/security" target="_blank" rel="noreferrer">
              Seguridad de Google <ExternalLink className="w-3 h-3" />
            </a>.
          </li>
          <li>
            Vaya a{" "}
            <a className="text-[#0033A0] inline-flex items-center gap-1" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">
              myaccount.google.com/apppasswords <ExternalLink className="w-3 h-3" />
            </a>.
          </li>
          <li>Elija <b>Otra</b> como aplicación y escriba <code>IU Digital Analítica</code>.</li>
          <li>Copie los <b>16 caracteres</b> que Google le muestra (sin espacios) y péguelos en <b>Contraseña de aplicación</b> aquí al lado.</li>
          <li>Active el switch <b>SMTP habilitado</b> y guarde.</li>
          <li>Envíese un correo de prueba a usted mismo antes de habilitar envíos masivos.</li>
        </ol>
        <Alert className="mt-4 border-amber-300 bg-amber-50/60 dark:bg-amber-500/5">
          <AlertTriangle className="w-4 h-4 text-amber-600" />
          <AlertTitle className="text-xs">Nunca use su contraseña normal</AlertTitle>
          <AlertDescription className="text-[11px]">
            Gmail bloquea el acceso de SMTP con contraseñas regulares. Solo funcionan los App Passwords.
          </AlertDescription>
        </Alert>
      </div>

      {/* Formulario */}
      <div className="dense-card p-5 lg:col-span-2 order-1 lg:order-2 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="label-eyebrow text-[#0033A0]">Servidor SMTP</p>
            <h3 className="font-display font-bold text-lg tracking-tight">Gmail institucional</h3>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="smtp-enabled" className="text-xs">SMTP habilitado</Label>
            <Switch id="smtp-enabled" checked={!!cfg.smtp_enabled} onCheckedChange={(v) => set("smtp_enabled", v)} data-testid="smtp-enabled-switch" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Host">
            <Input value={cfg.smtp_host || ""} onChange={(e) => set("smtp_host", e.target.value)} className="rounded-sm" data-testid="smtp-host" />
          </Field>
          <Field label="Puerto">
            <Input type="number" value={cfg.smtp_port || 587} onChange={(e) => set("smtp_port", parseInt(e.target.value || 587))} className="rounded-sm" data-testid="smtp-port" />
          </Field>
          <Field label="Correo remitente (Gmail)">
            <Input placeholder="notificaciones@iudigital.edu.co" value={cfg.smtp_user || ""} onChange={(e) => set("smtp_user", e.target.value)} className="rounded-sm" data-testid="smtp-user" />
          </Field>
          <Field label="Nombre visible del remitente">
            <Input placeholder="IU Digital Analítica" value={cfg.smtp_from_name || ""} onChange={(e) => set("smtp_from_name", e.target.value)} className="rounded-sm" data-testid="smtp-from-name" />
          </Field>
          <Field label={
            <span className="flex items-center justify-between w-full">
              <span>App Password (16 caracteres)</span>
              {cfg.smtp_password_mask && <span className="text-[10px] text-muted-foreground mono">Actual: {cfg.smtp_password_mask}</span>}
            </span>
          } full>
            <div className="relative">
              <Input
                type={showPw ? "text" : "password"}
                placeholder={cfg.smtp_password_mask ? "Dejar en blanco para conservar" : "xxxx xxxx xxxx xxxx (péguelo sin espacios)"}
                value={cfg._new_password || ""}
                onChange={(e) => set("_new_password", e.target.value.replace(/\s+/g, ""))}
                className="rounded-sm pr-9"
                data-testid="smtp-password"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </Field>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-border">
          <Button onClick={save} disabled={saving} className="rounded-sm bg-[#0033A0]" data-testid="save-smtp">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            Guardar configuración
          </Button>
        </div>

        <div className="border-t border-border pt-4">
          <p className="label-eyebrow text-[#0033A0] mb-2">Probar envío</p>
          <div className="flex gap-2">
            <Input placeholder="prueba@ejemplo.com" value={testTo} onChange={(e) => setTestTo(e.target.value)} className="rounded-sm max-w-xs" data-testid="smtp-test-to" />
            <Button variant="outline" onClick={sendTest} disabled={testing || !cfg.smtp_enabled} className="rounded-sm" data-testid="smtp-test-send">
              {testing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
              Enviar correo de prueba
            </Button>
          </div>
          {!cfg.smtp_enabled && (
            <p className="text-[11px] text-amber-700 mt-2">Habilite SMTP y guarde antes de enviar la prueba.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function AIPanel({ onSaved }) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const load = () => api.get("/config/ai").then(r => setCfg(r.data));
  useEffect(() => { load(); }, []);
  if (!cfg) return <div className="p-4 text-sm text-muted-foreground">Cargando…</div>;

  const set = (k, v) => setCfg({ ...cfg, [k]: v });
  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ai_provider: cfg.ai_provider,
        ai_enabled: !!cfg.ai_enabled,
        gemini_model: cfg.gemini_model,
        openai_model: cfg.openai_model,
      };
      if (cfg._new_gemini_key) payload.gemini_api_key = cfg._new_gemini_key;
      const r = await api.patch("/config/ai", payload);
      setCfg({ ...r.data, _new_gemini_key: "" });
      toast.success("Configuración de IA guardada");
      onSaved?.();
    } catch (e) {
      toast.error("Error al guardar", { description: e.response?.data?.detail || e.message });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="dense-card p-5 lg:col-span-1 order-2 lg:order-1">
        <p className="label-eyebrow text-[#0033A0]">Instrucciones</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Cómo obtener la API Key de Google Gemini</h3>
        <ol className="text-xs space-y-3 text-muted-foreground list-decimal ml-4">
          <li>
            Vaya a{" "}
            <a className="text-[#0033A0] inline-flex items-center gap-1" href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer">
              Google AI Studio <ExternalLink className="w-3 h-3" />
            </a>{" "}con una cuenta Google institucional.
          </li>
          <li>Pulse <b>Create API key</b> y seleccione un proyecto de Google Cloud (o cree uno).</li>
          <li>Copie la clave (empieza con <code>AIza…</code>) y péguela aquí al lado.</li>
          <li>Elija el modelo. Recomendado: <code>gemini-2.0-flash</code> (rápido y económico).</li>
          <li>Cambie el <b>Proveedor</b> a <b>Google Gemini</b> y guarde.</li>
        </ol>
        <Alert className="mt-4 border-blue-300 bg-blue-50/60 dark:bg-blue-500/5">
          <Bot className="w-4 h-4 text-blue-600" />
          <AlertTitle className="text-xs">Provisional: Emergent Universal Key</AlertTitle>
          <AlertDescription className="text-[11px]">
            Actualmente el sistema opera con la Emergent Universal Key (sin costo directo). Puede
            mantenerla mientras prueba Gemini. Al migrar a Google Cloud, cambie el proveedor.
          </AlertDescription>
        </Alert>
      </div>

      <div className="dense-card p-5 lg:col-span-2 order-1 lg:order-2 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="label-eyebrow text-[#0033A0]">Proveedor de IA</p>
            <h3 className="font-display font-bold text-lg tracking-tight">Motor de análisis inteligente</h3>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="ai-enabled" className="text-xs">IA activa</Label>
            <Switch id="ai-enabled" checked={!!cfg.ai_enabled} onCheckedChange={(v) => set("ai_enabled", v)} data-testid="ai-enabled-switch" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Proveedor" full>
            <Select value={cfg.ai_provider || "emergent"} onValueChange={(v) => set("ai_provider", v)}>
              <SelectTrigger className="rounded-sm" data-testid="ai-provider"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="emergent">Emergent Universal Key (por defecto, sin costo directo)</SelectItem>
                <SelectItem value="gemini_google">Google Gemini (API Key propia, para migrar a GCP)</SelectItem>
              </SelectContent>
            </Select>
          </Field>
          <Field label="Modelo Gemini (si aplica)">
            <Input value={cfg.gemini_model || "gemini-2.0-flash"} onChange={(e) => set("gemini_model", e.target.value)} className="rounded-sm" data-testid="ai-gemini-model" />
          </Field>
          <Field label="Modelo OpenAI vía Emergent">
            <Input value={cfg.openai_model || "gpt-4o"} onChange={(e) => set("openai_model", e.target.value)} className="rounded-sm" data-testid="ai-openai-model" />
          </Field>
          <Field label={
            <span className="flex items-center justify-between w-full">
              <span>Google Gemini API Key</span>
              {cfg.gemini_api_key_mask && <span className="text-[10px] text-muted-foreground mono">Actual: {cfg.gemini_api_key_mask}</span>}
            </span>
          } full>
            <div className="relative">
              <Input
                type={showKey ? "text" : "password"}
                placeholder={cfg.gemini_api_key_mask ? "Dejar en blanco para conservar" : "AIza..."}
                value={cfg._new_gemini_key || ""}
                onChange={(e) => set("_new_gemini_key", e.target.value)}
                className="rounded-sm pr-9"
                data-testid="ai-gemini-key"
              />
              <button type="button" onClick={() => setShowKey(!showKey)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
                {showKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </Field>
        </div>

        <div className="border-t border-border pt-3 flex items-center justify-between">
          <div className="text-[11px] text-muted-foreground">
            Emergent Key detectada: {cfg.emergent_key_present ? <b className="text-emerald-700">Sí</b> : <b className="text-amber-700">No</b>}
          </div>
          <Button onClick={save} disabled={saving} className="rounded-sm bg-[#0033A0]" data-testid="save-ai">
            {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <CheckCircle2 className="w-4 h-4 mr-2" />}
            Guardar configuración IA
          </Button>
        </div>
      </div>
    </div>
  );
}

function EnviosPanel() {
  const [sending, setSending] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [result, setResult] = useState(null);
  const [onlyMissing, setOnlyMissing] = useState(true);

  const sendBulk = async () => {
    if (!window.confirm(`¿Enviar credenciales ${onlyMissing ? "a los docentes que aún NO han recibido" : "a TODOS los docentes activos (regenera contraseña)"}?`)) return;
    setSending(true); setResult(null);
    try {
      const r = await api.post("/config/send-credentials-bulk", { role: "profesor", only_missing: onlyMissing });
      setResult(r.data);
      toast.success(`Envío completado: ${r.data.sent} exitosos, ${r.data.failed} fallidos`);
    } catch (e) {
      toast.error("Error en envío masivo", { description: e.response?.data?.detail || e.message });
    } finally {
      setSending(false);
    }
  };

  const resetInitialCedula = async () => {
    if (!window.confirm("¿Resetear la contraseña de TODOS los docentes a su CÉDULA?\n\nEsta acción:\n• Deja la contraseña inicial = número de cédula\n• Marca 'debe cambiar contraseña al primer ingreso' en todos\n• NO envía correos\n\nÚtil cuando aún no hay correo institucional.")) return;
    setResetting(true);
    try {
      const r = await api.post("/config/reset-initial-passwords", { role: "profesor", strategy: "cedula" });
      toast.success(`Reset completado: ${r.data.reset} docentes actualizados. ${r.data.skipped_without_cedula} omitidos sin cédula.`);
    } catch (e) {
      toast.error("Error al resetear", { description: e.response?.data?.detail || e.message });
    } finally {
      setResetting(false);
    }
  };

  const downloadCreds = async () => {
    try {
      const r = await api.get("/config/initial-credentials.xlsx", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = `credenciales_iniciales_profesor_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success("Excel descargado");
    } catch (e) {
      toast.error("Error al descargar", { description: e.response?.data?.detail || e.message });
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="dense-card p-5 lg:col-span-1">
        <p className="label-eyebrow text-[#0033A0]">Guía rápida</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-3">Entrega de credenciales</h3>
        <ol className="text-xs space-y-3 text-muted-foreground list-decimal ml-4">
          <li>
            <b>Si aún NO tiene correo institucional</b>: use el botón <b>&quot;Contraseña inicial = cédula&quot;</b>{" "}
            y descargue el Excel para entregarlas físicamente o por WhatsApp/correo personal.
          </li>
          <li>
            <b>Si YA tiene Gmail institucional</b>: configure SMTP en la pestaña anterior y use{" "}
            <b>&quot;Enviar credenciales masivo&quot;</b>. Cada docente recibirá una contraseña única generada aleatoriamente por correo.
          </li>
          <li>En ambos casos, cada docente deberá <b>cambiar la contraseña en el primer ingreso</b>.</li>
          <li>Para reenviar a uno solo, use el botón <b>Mail</b> en la fila del usuario en Administración.</li>
        </ol>
        <Alert className="mt-4 border-blue-300 bg-blue-50/60 dark:bg-blue-500/5">
          <AlertTriangle className="w-4 h-4 text-blue-600" />
          <AlertTitle className="text-xs">Regla institucional</AlertTitle>
          <AlertDescription className="text-[11px]">
            Los docentes pueden ingresar con <b>su número de cédula como usuario</b>. El correo es opcional
            para login (solo se usa como contacto).
          </AlertDescription>
        </Alert>
      </div>

      <div className="dense-card p-5 lg:col-span-2 space-y-5">
        {/* Bloque 1: modo cédula */}
        <div className="border border-amber-200 bg-amber-50/40 dark:bg-amber-500/5 rounded-sm p-4">
          <p className="label-eyebrow text-amber-800 dark:text-amber-300 mb-2">Modo sin correo institucional</p>
          <h4 className="font-display font-bold text-base tracking-tight mb-2">Contraseña inicial = número de cédula</h4>
          <p className="text-xs text-muted-foreground mb-3">
            Cada docente ingresa con <b>su cédula como usuario</b> y <b>su cédula como contraseña</b>. Al primer
            ingreso el sistema le pedirá cambiarla por una nueva. Genere el Excel para entrega física.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={resetInitialCedula} disabled={resetting} className="rounded-sm" data-testid="reset-cedula-btn">
              {resetting ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <KeyRound className="w-4 h-4 mr-2" />}
              Resetear todos a contraseña = cédula
            </Button>
            <Button onClick={downloadCreds} className="rounded-sm bg-[#0033A0]" data-testid="download-creds-xlsx">
              <Send className="w-4 h-4 mr-2" /> Descargar Excel de credenciales
            </Button>
          </div>
        </div>

        {/* Bloque 2: envío por correo */}
        <div>
          <p className="label-eyebrow text-[#0033A0]">Envío por correo (requiere SMTP)</p>
          <h4 className="font-display font-bold text-base tracking-tight mb-2">Envío masivo · Docentes</h4>

          <div className="flex items-center gap-3 mb-3">
            <Switch checked={onlyMissing} onCheckedChange={setOnlyMissing} data-testid="only-missing-switch" />
            <div>
              <p className="text-xs font-medium">Solo docentes sin credenciales enviadas previamente</p>
              <p className="text-[10px] text-muted-foreground">
                {onlyMissing
                  ? "Enviará solo a quienes aún no reciben (comportamiento seguro y recomendado)."
                  : "Enviará a TODOS los docentes activos, regenerando la contraseña de cada uno."}
              </p>
            </div>
          </div>

          <Button onClick={sendBulk} disabled={sending} className="rounded-sm bg-[#0033A0]" data-testid="send-bulk-btn">
            {sending ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Send className="w-4 h-4 mr-2" />}
            Enviar credenciales masivo
          </Button>

          {result && (
            <div className="border border-border rounded-sm p-3 space-y-2 mt-3">
              <p className="text-xs">
                <b>{result.sent}</b> enviados · <b>{result.failed}</b> fallidos · Total objetivo: {result.total_target}
              </p>
              {result.failed > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-amber-700">Ver fallidos ({result.failed_list?.length || 0})</summary>
                  <ul className="mt-2 space-y-1 max-h-40 overflow-y-auto">
                    {(result.failed_list || []).map((f, i) => (
                      <li key={i} className="text-[11px]">
                        <b>{f.email || f.id}</b> — <span className="text-muted-foreground">{f.error}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, full, children }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      {children}
    </div>
  );
}
