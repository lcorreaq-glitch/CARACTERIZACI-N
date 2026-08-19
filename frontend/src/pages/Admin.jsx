import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Trash2, UserPlus, Globe, Download, Eye, Pencil, Save, Shield, ShieldOff, Key, Power, PowerOff, Settings2, CheckCircle2, XCircle, Mail, Info, TrendingUp, Building2 } from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/context/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";

const ROLES = ["superadmin", "direccion", "decano", "coordinador", "profesor"];
const ROLE_LABELS = {
  superadmin: "Superadministrador",
  direccion: "Dirección",
  decano: "Decano",
  coordinador: "Coordinador",
  profesor: "Profesor",
};
const ROLE_DESCRIPTIONS = {
  superadmin: "Acceso total sin restricciones",
  direccion: "Ve todos los tableros y admin — NO gestiona usuarios ni permisos globales",
  decano: "Ve solo la facultad asignada (requiere facultad)",
  coordinador: "Ve solo su programa (o facultad si es coord. de facultad)",
  profesor: "Ve solo sus cursos asignados y sus estudiantes",
};

export default function Admin() {
  return (
    <div className="space-y-6" data-testid="admin-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Administración</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Gestión institucional</h1>
        <p className="text-sm text-muted-foreground mt-2">Usuarios, catálogos y relación docente–materia.</p>
      </header>

      <Tabs defaultValue="users">
        <TabsList className="rounded-sm flex-wrap h-auto">
          <TabsTrigger value="users" data-testid="tab-users">Usuarios & Roles</TabsTrigger>
          <TabsTrigger value="settings" data-testid="tab-settings">Permisos globales</TabsTrigger>
          <TabsTrigger value="docentes" data-testid="tab-docentes">Profesores</TabsTrigger>
          <TabsTrigger value="facultades" data-testid="tab-facultades">Facultades</TabsTrigger>
          <TabsTrigger value="programas" data-testid="tab-programas">Programas</TabsTrigger>
          <TabsTrigger value="materias" data-testid="tab-materias">Materias</TabsTrigger>
          <TabsTrigger value="periodos" data-testid="tab-periodos">Periodos</TabsTrigger>
          <TabsTrigger value="docente-materia" data-testid="tab-docente-materia">Docente–Materia</TabsTrigger>
          <TabsTrigger value="divipola" data-testid="tab-divipola">DIVIPOLA</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><ErrorBoundary><UsersTab /></ErrorBoundary></TabsContent>
        <TabsContent value="settings"><ErrorBoundary><SystemSettingsTab /></ErrorBoundary></TabsContent>
        <TabsContent value="docentes"><ErrorBoundary><DocentesTab /></ErrorBoundary></TabsContent>
        <TabsContent value="facultades"><ErrorBoundary><CatalogTab name="facultades" label="Facultad" /></ErrorBoundary></TabsContent>
        <TabsContent value="programas"><ErrorBoundary><ProgramasTab /></ErrorBoundary></TabsContent>
        <TabsContent value="materias"><ErrorBoundary><CatalogTab name="materias" label="Materia" showPrograma /></ErrorBoundary></TabsContent>
        <TabsContent value="periodos"><ErrorBoundary><CatalogTab name="periodos" label="Periodo" /></ErrorBoundary></TabsContent>
        <TabsContent value="docente-materia"><ErrorBoundary><DocenteMateriaTab /></ErrorBoundary></TabsContent>
        <TabsContent value="divipola"><ErrorBoundary><DivipolaTab /></ErrorBoundary></TabsContent>
      </Tabs>
    </div>
  );
}

function UsersTab() {
  const { user: current } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [facultades, setFacultades] = useState([]);
  const [programas, setProgramas] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "profesor", facultad_id: "", programa_id: "" });
  const [editUser, setEditUser] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [resetTarget, setResetTarget] = useState(null);
  const [resetPwd, setResetPwd] = useState("");

  const isSuperadmin = current?.role === "superadmin";

  const load = () => {
    setLoading(true);
    api.get("/admin/users")
      .then((r) => setUsers(r.data || []))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    load();
    api.get("/admin/facultades").then((r) => setFacultades(r.data || []));
    api.get("/admin/programas").then((r) => setProgramas((r.data?.items || r.data || []))).catch(() => {});
  }, []);

  // Programas filtered by selected facultad in the form
  const programasForFac = (facId) => facId ? programas.filter((p) => p.facultad_id === facId) : programas;

  const validateScope = (payload) => {
    if (payload.role === "decano" && !payload.facultad_id) {
      toast.error("El rol Decano requiere una facultad asignada");
      return false;
    }
    if (payload.role === "coordinador" && !payload.facultad_id && !payload.programa_id) {
      toast.error("El rol Coordinador requiere una facultad o programa asignado");
      return false;
    }
    return true;
  };

  const create = async () => {
    if (!form.email || !form.password || !form.full_name) return toast.error("Complete todos los campos");
    if (form.password.length < 6) return toast.error("La contraseña debe tener al menos 6 caracteres");
    if (!validateScope(form)) return;
    try {
      const payload = { ...form };
      if (!payload.facultad_id) delete payload.facultad_id;
      if (!payload.programa_id) delete payload.programa_id;
      await api.post("/admin/users", payload);
      toast.success("Usuario creado. Debe cambiar contraseña en el primer login.");
      setOpen(false);
      setForm({ email: "", password: "", full_name: "", role: "profesor", facultad_id: "", programa_id: "" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const startEdit = (u) => {
    setEditUser(u);
    setEditForm({
      full_name: u.full_name || "",
      role: u.role,
      active: u.active !== false,
      download_enabled: u.download_enabled === true,
      facultad_id: u.facultad_id || "",
      programa_id: u.programa_id || "",
    });
  };

  const saveEdit = async () => {
    if (!editUser) return;
    if (!validateScope(editForm)) return;
    try {
      const payload = { ...editForm };
      // Send empty string as null so backend can clear the field
      if (payload.facultad_id === "") payload.facultad_id = null;
      if (payload.programa_id === "") payload.programa_id = null;
      await api.patch(`/admin/users/${editUser.id}`, payload);
      toast.success("Usuario actualizado");
      setEditUser(null);
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const toggleActive = async (u) => {
    if (u.id === current?.id) return toast.error("No puede desactivar su propio usuario");
    try {
      const r = await api.post(`/admin/users/${u.id}/toggle-active`);
      toast.success(r.data.active ? "Usuario activado" : "Usuario desactivado");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const toggleDownload = async (u) => {
    try {
      const r = await api.post(`/admin/users/${u.id}/toggle-download`);
      toast.success(r.data.download_enabled ? "Descargas habilitadas" : "Descargas deshabilitadas");
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const doReset = async () => {
    if (!resetTarget) return;
    if (resetPwd && resetPwd.length < 6) return toast.error("Mínimo 6 caracteres");
    try {
      const r = await api.post(`/admin/users/${resetTarget.id}/reset-password`, { new_password: resetPwd || null });
      toast.success(`Contraseña reseteada: ${r.data.new_password}`);
      setResetTarget(null);
      setResetPwd("");
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const remove = async (u) => {
    if (!window.confirm(`¿Eliminar definitivamente al usuario ${u.email}? Esta acción no se puede deshacer.`)) return;
    try { await api.delete(`/admin/users/${u.id}`); toast.success("Eliminado"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const sendCreds = async (u) => {
    const already = u.credentials_sent_at ? `\n\nÚltimo envío: ${u.credentials_sent_at.slice(0, 16).replace("T", " ")}` : "";
    if (!window.confirm(`Enviar correo con credenciales a ${u.email}?\n\nSe generará una nueva contraseña temporal y se enviará por correo.${already}`)) return;
    try {
      const r = await api.post(`/config/send-credentials/${u.id}`, { reset_password: true });
      toast.success(`Correo enviado a ${r.data.email}`);
      load();
    } catch (e) {
      toast.error("Fallo el envío", { description: e?.response?.data?.detail || "Verifique la configuración SMTP en Configuración." });
    }
  };

  const filtered = users.filter((u) => {
    if (roleFilter !== "all" && u.role !== roleFilter) return false;
    if (statusFilter === "active" && u.active === false) return false;
    if (statusFilter === "inactive" && u.active !== false) return false;
    if (query) {
      const s = query.toLowerCase();
      const hay = [u.email, u.full_name].filter(Boolean).some((v) => v.toLowerCase().includes(s));
      if (!hay) return false;
    }
    return true;
  });

  const counts = {
    total: users.length,
    active: users.filter((u) => u.active !== false).length,
    inactive: users.filter((u) => u.active === false).length,
    superadmin: users.filter((u) => u.role === "superadmin").length,
    direccion: users.filter((u) => u.role === "direccion").length,
    decano: users.filter((u) => u.role === "decano").length,
    coordinador: users.filter((u) => u.role === "coordinador").length,
    profesor: users.filter((u) => u.role === "profesor").length,
  };

  const roleBadge = (r) => {
    const cls = {
      superadmin: "bg-[#E3000F]/10 text-[#E3000F] border-[#E3000F]/30",
      direccion: "bg-[#0033A0]/10 text-[#0033A0] border-[#0033A0]/30",
      decano: "bg-purple-500/10 text-purple-700 border-purple-500/30",
      coordinador: "bg-emerald-500/10 text-emerald-700 border-emerald-500/30",
      profesor: "bg-[#FFCD00]/20 text-[#7A6300] border-[#FFCD00]/40",
    }[r] || "bg-muted text-muted-foreground";
    return <Badge variant="outline" className={`text-[9px] uppercase tracking-widest rounded-sm ${cls}`}>{ROLE_LABELS[r] || r}</Badge>;
  };

  return (
    <div className="dense-card p-5 mt-4" data-testid="users-tab-panel">
      {/* KPI strip */}
      <div className="grid grid-cols-2 md:grid-cols-7 gap-3 mb-5">
        <StatCard label="Total" value={counts.total} />
        <StatCard label="Activos" value={counts.active} accent="text-emerald-700" />
        <StatCard label="Inactivos" value={counts.inactive} accent="text-[#E3000F]" />
        <StatCard label="Superadmin" value={counts.superadmin} accent="text-[#E3000F]" />
        <StatCard label="Dirección" value={counts.direccion} accent="text-[#0033A0]" />
        <StatCard label="Decanos" value={counts.decano} accent="text-purple-700" />
        <StatCard label="Coord./Prof." value={counts.coordinador + counts.profesor} accent="text-[#7A6300]" />
      </div>

      <div className="flex flex-wrap gap-3 items-end justify-between mb-4">
        <div className="flex flex-wrap gap-2 items-center">
          <Input
            placeholder="Buscar por nombre o correo…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded-sm w-64"
            data-testid="users-search"
          />
          <Select value={roleFilter} onValueChange={setRoleFilter}>
            <SelectTrigger className="rounded-sm w-40" data-testid="users-role-filter"><SelectValue placeholder="Rol" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los roles</SelectItem>
              {ROLES.map((r) => <SelectItem key={r} value={r}>{ROLE_LABELS[r] || r}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="rounded-sm w-36" data-testid="users-status-filter"><SelectValue placeholder="Estado" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              <SelectItem value="active">Activos</SelectItem>
              <SelectItem value="inactive">Inactivos</SelectItem>
            </SelectContent>
          </Select>
        </div>
        {isSuperadmin && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="admin-create-user-btn">
                <UserPlus className="w-4 h-4 mr-2" /> Crear usuario
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
              <DialogHeader><DialogTitle className="font-display">Crear usuario</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label className="label-eyebrow">Nombre completo</Label><Input className="rounded-sm" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} data-testid="new-user-name" /></div>
                <div><Label className="label-eyebrow">Email institucional</Label><Input type="email" className="rounded-sm" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="new-user-email" /></div>
                <div><Label className="label-eyebrow">Contraseña inicial</Label>
                  <Input type="password" className="rounded-sm" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="new-user-password" />
                  <p className="text-[10px] text-muted-foreground mt-1">El usuario deberá cambiarla al primer login (política institucional).</p>
                </div>
                <div>
                  <Label className="label-eyebrow">Rol</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v, facultad_id: "", programa_id: "" })}>
                    <SelectTrigger className="rounded-sm" data-testid="new-user-role"><SelectValue /></SelectTrigger>
                    <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>)}</SelectContent>
                  </Select>
                  <p className="text-[10px] text-muted-foreground mt-1 italic">{ROLE_DESCRIPTIONS[form.role]}</p>
                </div>
                {(form.role === "decano" || form.role === "coordinador") && (
                  <div className="border-l-2 border-purple-500/40 pl-3 py-2 bg-purple-500/5 rounded-sm space-y-3">
                    <p className="text-[10px] font-semibold text-purple-700 uppercase tracking-wider">
                      Scope obligatorio para {ROLE_LABELS[form.role]}
                    </p>
                    <div>
                      <Label className="label-eyebrow">
                        Facultad {form.role === "decano" && <span className="text-[#E3000F]">*</span>}
                      </Label>
                      <Select value={form.facultad_id || "__none__"} onValueChange={(v) => setForm({ ...form, facultad_id: v === "__none__" ? "" : v, programa_id: "" })}>
                        <SelectTrigger className="rounded-sm" data-testid="new-user-facultad">
                          <SelectValue placeholder="Seleccione una facultad…" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">— Sin asignar —</SelectItem>
                          {facultades.map((f) => <SelectItem key={f.id} value={f.id}>{f.nombre}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                    {form.role === "coordinador" && (
                      <div>
                        <Label className="label-eyebrow">
                          Programa <span className="text-muted-foreground text-[9px]">(o vacío si es coord. de facultad)</span>
                        </Label>
                        <Select value={form.programa_id || "__none__"} onValueChange={(v) => setForm({ ...form, programa_id: v === "__none__" ? "" : v })}>
                          <SelectTrigger className="rounded-sm" data-testid="new-user-programa">
                            <SelectValue placeholder={form.facultad_id ? "Seleccione un programa…" : "Primero elija facultad (opcional)"} />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="__none__">— Coord. de Facultad —</SelectItem>
                            {programasForFac(form.facultad_id).map((p) => (
                              <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}
                  </div>
                )}
              </div>
              <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid="new-user-submit">Crear</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>

      <div className="text-xs text-muted-foreground mb-2">
        Mostrando <b>{filtered.length}</b> de <b>{users.length}</b>
      </div>

      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="text-[10px] uppercase tracking-wider">Usuario</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Email</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Rol</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Facultad / Programa</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Estado</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Descargas</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Último ingreso</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider text-right">Acciones</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={8} className="text-center py-6 text-xs text-muted-foreground">Cargando…</TableCell></TableRow>}
            {!loading && filtered.map((u) => (
              <TableRow key={u.id} className={`hover:bg-muted/40 ${u.active === false ? "opacity-60" : ""}`} data-testid={`user-row-${u.id}`}>
                <TableCell className="text-xs font-medium">
                  {u.full_name}
                  {u.must_change_password && <Badge variant="outline" className="ml-2 text-[8px] bg-amber-500/10 text-amber-700 border-amber-500/40 rounded-sm">Debe cambiar contraseña</Badge>}
                  {u.id === current?.id && <Badge variant="outline" className="ml-2 text-[8px] rounded-sm">Tú</Badge>}
                </TableCell>
                <TableCell className="text-[11px]">{u.email}</TableCell>
                <TableCell>{roleBadge(u.role)}</TableCell>
                <TableCell className="text-[10px]">
                  {u.programa_nombre && <div><span className="text-muted-foreground">Programa:</span> <b>{u.programa_nombre}</b></div>}
                  {u.facultad_nombre && <div><span className="text-muted-foreground">Facultad:</span> <b>{u.facultad_nombre}</b></div>}
                  {!u.programa_nombre && !u.facultad_nombre && (u.role === "decano" || u.role === "coordinador")
                    ? <Badge variant="outline" className="text-[8px] bg-[#E3000F]/10 text-[#E3000F] border-[#E3000F]/40 rounded-sm">⚠ Sin asignar</Badge>
                    : (!u.programa_nombre && !u.facultad_nombre ? <span className="text-muted-foreground italic">—</span> : null)
                  }
                </TableCell>
                <TableCell>
                  {isSuperadmin ? (
                    <Switch
                      checked={u.active !== false}
                      onCheckedChange={() => toggleActive(u)}
                      disabled={u.id === current?.id}
                      data-testid={`toggle-active-${u.id}`}
                    />
                  ) : (
                    u.active !== false
                      ? <Badge variant="outline" className="text-[9px] bg-emerald-500/10 text-emerald-700 border-emerald-500/30 rounded-sm">Activo</Badge>
                      : <Badge variant="outline" className="text-[9px] bg-slate-500/10 text-slate-600 rounded-sm">Inactivo</Badge>
                  )}
                </TableCell>
                <TableCell>
                  {isSuperadmin ? (
                    <Switch
                      checked={u.download_enabled === true}
                      onCheckedChange={() => toggleDownload(u)}
                      data-testid={`toggle-download-${u.id}`}
                    />
                  ) : (
                    u.download_enabled
                      ? <CheckCircle2 className="w-4 h-4 text-emerald-600 inline" />
                      : <XCircle className="w-4 h-4 text-muted-foreground inline" />
                  )}
                </TableCell>
                <TableCell className="text-[10px] text-muted-foreground">
                  {u.last_login ? u.last_login.slice(0, 16).replace("T", " ") : <span className="italic">nunca</span>}
                </TableCell>
                <TableCell className="text-right">
                  {isSuperadmin && (
                    <>
                      <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => startEdit(u)} title="Editar" data-testid={`edit-user-${u.id}`}>
                        <Pencil className="w-3.5 h-3.5 text-[#0033A0]" />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => sendCreds(u)} title="Enviar credenciales por correo" data-testid={`send-creds-${u.id}`}>
                        <Mail className={`w-3.5 h-3.5 ${u.credentials_sent_at ? "text-emerald-600" : "text-[#0033A0]"}`} />
                      </Button>
                      <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setResetTarget(u)} title="Resetear contraseña" data-testid={`reset-pwd-${u.id}`}>
                        <Key className="w-3.5 h-3.5 text-amber-600" />
                      </Button>
                      {u.id !== current?.id && (
                        <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => remove(u)} title="Eliminar" data-testid={`delete-user-${u.id}`}>
                          <Trash2 className="w-3 h-3 text-[#E3000F]" />
                        </Button>
                      )}
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!loading && filtered.length === 0 && (
              <TableRow><TableCell colSpan={8} className="text-center py-6 text-xs text-muted-foreground">Sin usuarios con esos criterios</TableCell></TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editUser} onOpenChange={(v) => !v && setEditUser(null)}>
        <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto" data-testid="edit-user-dialog">
          <DialogHeader><DialogTitle className="font-display">Editar {editUser?.full_name}</DialogTitle></DialogHeader>
          {editUser && (
            <div className="space-y-3">
              <div><Label className="label-eyebrow">Nombre completo</Label>
                <Input className="rounded-sm" value={editForm.full_name || ""} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} data-testid="edit-user-name" />
              </div>
              <div><Label className="label-eyebrow">Email</Label>
                <Input className="rounded-sm bg-muted" value={editUser.email} disabled />
                <p className="text-[10px] text-muted-foreground mt-1">El correo no se puede modificar. Cree un usuario nuevo si es necesario.</p>
              </div>
              <div><Label className="label-eyebrow">Rol</Label>
                <Select value={editForm.role} onValueChange={(v) => setEditForm({ ...editForm, role: v, facultad_id: v === "profesor" || v === "superadmin" || v === "direccion" ? "" : editForm.facultad_id, programa_id: v === "profesor" || v === "superadmin" || v === "direccion" || v === "decano" ? "" : editForm.programa_id })}>
                  <SelectTrigger className="rounded-sm" data-testid="edit-user-role"><SelectValue /></SelectTrigger>
                  <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r}>{ROLE_LABELS[r]}</SelectItem>)}</SelectContent>
                </Select>
                <p className="text-[10px] text-muted-foreground mt-1 italic">{ROLE_DESCRIPTIONS[editForm.role]}</p>
              </div>
              {(editForm.role === "decano" || editForm.role === "coordinador") && (
                <div className="border-l-2 border-purple-500/40 pl-3 py-2 bg-purple-500/5 rounded-sm space-y-3">
                  <p className="text-[10px] font-semibold text-purple-700 uppercase tracking-wider">
                    Scope de {ROLE_LABELS[editForm.role]}
                  </p>
                  <div>
                    <Label className="label-eyebrow">
                      Facultad {editForm.role === "decano" && <span className="text-[#E3000F]">*</span>}
                    </Label>
                    <Select value={editForm.facultad_id || "__none__"} onValueChange={(v) => setEditForm({ ...editForm, facultad_id: v === "__none__" ? "" : v, programa_id: "" })}>
                      <SelectTrigger className="rounded-sm" data-testid="edit-user-facultad">
                        <SelectValue placeholder="Seleccione una facultad…" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="__none__">— Sin asignar —</SelectItem>
                        {facultades.map((f) => <SelectItem key={f.id} value={f.id}>{f.nombre}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                  {editForm.role === "coordinador" && (
                    <div>
                      <Label className="label-eyebrow">Programa <span className="text-muted-foreground text-[9px]">(vacío = coord. de facultad)</span></Label>
                      <Select value={editForm.programa_id || "__none__"} onValueChange={(v) => setEditForm({ ...editForm, programa_id: v === "__none__" ? "" : v })}>
                        <SelectTrigger className="rounded-sm" data-testid="edit-user-programa">
                          <SelectValue placeholder="Seleccione un programa…" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">— Coord. de Facultad —</SelectItem>
                          {programasForFac(editForm.facultad_id).map((p) => (
                            <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                </div>
              )}
              <div className="flex items-center justify-between border-t border-border pt-3">
                <div>
                  <Label className="label-eyebrow">Cuenta activa</Label>
                  <p className="text-[10px] text-muted-foreground">Puede iniciar sesión</p>
                </div>
                <Switch checked={editForm.active} onCheckedChange={(v) => setEditForm({ ...editForm, active: v })} disabled={editUser.id === current?.id} data-testid="edit-user-active" />
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label className="label-eyebrow">Descargas habilitadas</Label>
                  <p className="text-[10px] text-muted-foreground">Permite exportar Excel/CSV desde la app</p>
                </div>
                <Switch checked={editForm.download_enabled} onCheckedChange={(v) => setEditForm({ ...editForm, download_enabled: v })} data-testid="edit-user-download" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" className="rounded-sm" onClick={() => setEditUser(null)}>Cancelar</Button>
            <Button onClick={saveEdit} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid="save-user-edit">
              <Save className="w-3.5 h-3.5 mr-1" /> Guardar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password dialog */}
      <Dialog open={!!resetTarget} onOpenChange={(v) => { if (!v) { setResetTarget(null); setResetPwd(""); } }}>
        <DialogContent data-testid="reset-password-dialog">
          <DialogHeader><DialogTitle className="font-display">Resetear contraseña de {resetTarget?.full_name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div>
              <Label className="label-eyebrow">Nueva contraseña (opcional)</Label>
              <Input type="text" className="rounded-sm" value={resetPwd} onChange={(e) => setResetPwd(e.target.value)} placeholder="Dejar vacío para usar la predeterminada" data-testid="reset-pwd-input" />
              <p className="text-[10px] text-muted-foreground mt-1">
                Si se deja vacío, se asignará <span className="font-mono">IUDigital2026!</span>. El usuario será forzado a cambiarla al iniciar sesión.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" className="rounded-sm" onClick={() => setResetTarget(null)}>Cancelar</Button>
            <Button onClick={doReset} className="bg-amber-600 hover:bg-amber-700 text-white rounded-sm" data-testid="reset-pwd-confirm">
              <Key className="w-3.5 h-3.5 mr-1" /> Resetear
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ label, value, accent }) {
  return (
    <div className="border border-border rounded-sm p-3">
      <p className="label-eyebrow">{label}</p>
      <p className={`kpi-num text-2xl mt-1 ${accent || ""}`}>{(value || 0).toLocaleString("es-CO")}</p>
    </div>
  );
}

function SystemSettingsTab() {
  const { user } = useAuth();
  const isSuperadmin = user?.role === "superadmin";
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.get("/admin/system-settings")
      .then((r) => setSettings(r.data))
      .finally(() => setLoading(false));
  };
  useEffect(() => { load(); }, []);

  const toggle = async (key) => {
    if (!isSuperadmin) return toast.error("Solo el superadministrador puede modificar estos ajustes");
    try {
      const r = await api.patch("/admin/system-settings", { [key]: !settings[key] });
      setSettings(r.data);
      toast.success("Ajuste actualizado");
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const SWITCHES = [
    {
      key: "docente_downloads_globally_enabled",
      title: "Descargas globales para profesores/coord./decanos",
      desc: "Cuando está encendido, TODOS los profesores, coordinadores y decanos pueden descargar Excel/CSV, aunque su permiso individual esté apagado. Recomendado: dejar apagado y habilitar caso a caso.",
      icon: Download,
    },
    {
      key: "docente_ai_insights_enabled",
      title: "IA — Alertas tempranas para profesores/coord./decanos",
      desc: "Permite que los profesores, coordinadores y decanos accedan al módulo de Alertas tempranas y resúmenes con IA sobre sus estudiantes.",
      icon: Shield,
    },
    {
      key: "docente_can_see_all_periods",
      title: "Profesor puede ver periodos anteriores",
      desc: "Si está apagado, el profesor solo verá el periodo activo (2026-2). Enciéndalo para dar acceso al histórico completo de sus asignaciones.",
      icon: Eye,
    },
    {
      key: "allow_public_landing",
      title: "Landing pública sin login (futuro)",
      desc: "Si se activa, se mostrará una página pública institucional con indicadores agregados. Requiere una vista dedicada (no implementada aún).",
      icon: Globe,
    },
  ];

  return (
    <div className="space-y-4 mt-4" data-testid="system-settings-tab">
      <div className="dense-card p-5">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <p className="label-eyebrow text-[#0033A0]"><Settings2 className="w-3 h-3 inline mr-1" /> Permisos y controles globales</p>
            <h3 className="font-display font-bold text-lg tracking-tight mt-1">Configuración institucional</h3>
            <p className="text-xs text-muted-foreground mt-1">
              Estos toggles aplican a toda la plataforma. Los permisos individuales por usuario tienen prioridad sobre los globales apagados.
            </p>
          </div>
          {!isSuperadmin && (
            <Badge variant="outline" className="text-[10px] bg-amber-500/10 text-amber-700 border-amber-500/40 rounded-sm">
              Solo lectura — se requiere rol superadmin para modificar
            </Badge>
          )}
        </div>

        {loading && <p className="text-xs text-muted-foreground">Cargando ajustes…</p>}
        {!loading && settings && (
          <div className="space-y-3">
            {SWITCHES.map((s) => (
              <div key={s.key} className="flex items-start justify-between gap-4 p-4 border border-border rounded-sm hover:border-[#0033A0]/40 transition-soft">
                <div className="flex items-start gap-3 flex-1">
                  <div className={`h-9 w-9 grid place-items-center rounded ${settings[s.key] ? "bg-emerald-500/10 text-emerald-700" : "bg-muted text-muted-foreground"}`}>
                    <s.icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1">
                    <p className="font-display font-bold text-sm">{s.title}</p>
                    <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">{s.desc}</p>
                    <p className="text-[9px] text-muted-foreground mt-2 font-mono">{s.key}</p>
                  </div>
                </div>
                <Switch
                  checked={settings[s.key] === true}
                  onCheckedChange={() => toggle(s.key)}
                  disabled={!isSuperadmin}
                  data-testid={`setting-${s.key}`}
                />
              </div>
            ))}
          </div>
        )}
        {!loading && settings?.updated_at && (
          <p className="text-[10px] text-muted-foreground mt-4 border-t border-border pt-3">
            Última actualización: {settings.updated_at.slice(0, 19).replace("T", " ")}
            {settings.updated_by && <> · por <b>{settings.updated_by}</b></>}
          </p>
        )}
      </div>

      <div className="dense-card p-5">
        <p className="label-eyebrow text-[#0033A0]">Matriz de permisos por rol</p>
        <h3 className="font-display font-bold text-lg tracking-tight mt-1 mb-3">Referencia</h3>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-[10px] uppercase tracking-wider">Acción</TableHead>
                <TableHead className="text-[10px] uppercase tracking-wider text-center">Superadmin</TableHead>
                <TableHead className="text-[10px] uppercase tracking-wider text-center">Dirección</TableHead>
                <TableHead className="text-[10px] uppercase tracking-wider text-center">Decano</TableHead>
                <TableHead className="text-[10px] uppercase tracking-wider text-center">Coordinador</TableHead>
                <TableHead className="text-[10px] uppercase tracking-wider text-center">Profesor</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {[
                // Cada fila: [acción, super, direccion, decano, coord, profesor]
                ["Dashboards ejecutivo/académico/territorial (globales)", true, true, "facultad", "programa", false],
                ["Ver caracterización global", true, true, "facultad", "programa", false],
                ["Ver Mi Panel (con estudiantes)", true, true, "facultad", "programa", "sus grupos"],
                ["Alertas IA sobre estudiantes", true, true, "facultad", "programa", "sus grupos"],
                ["Cargas de Excel", true, true, false, false, false],
                ["Editar catálogos (facultades, programas, materias)", true, true, false, false, false],
                ["Crear/editar/eliminar usuarios", true, false, false, false, false],
                ["Permisos globales del sistema", true, false, false, false, false],
                ["Descargar Excel/CSV", true, true, "config", "config", "config"],
                ["Ver estudiantes fuera de su scope", true, true, false, false, false],
                ["Cambiar propia contraseña", true, true, true, true, true],
              ].map((row, idx) => (
                <TableRow key={idx}>
                  <TableCell className="text-xs">{row[0]}</TableCell>
                  {row.slice(1).map((v, i) => (
                    <TableCell key={i} className="text-center">
                      {v === true && <CheckCircle2 className="w-4 h-4 text-emerald-600 inline" />}
                      {v === false && <XCircle className="w-3.5 h-3.5 text-muted-foreground inline" />}
                      {v === "config" && <Badge variant="outline" className="text-[9px] rounded-sm bg-amber-500/10 text-amber-700 border-amber-500/40">Config</Badge>}
                      {v === "facultad" && <Badge variant="outline" className="text-[9px] rounded-sm bg-purple-500/10 text-purple-700 border-purple-500/40">Su facultad</Badge>}
                      {v === "programa" && <Badge variant="outline" className="text-[9px] rounded-sm bg-emerald-500/10 text-emerald-700 border-emerald-500/40">Su programa</Badge>}
                      {v === "sus grupos" && <Badge variant="outline" className="text-[9px] rounded-sm bg-[#FFCD00]/20 text-[#7A6300] border-[#FFCD00]/40">Sus grupos</Badge>}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

function CatalogTab({ name, label, showFacultad, showPrograma }) {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ nombre: "", codigo: "", facultad_id: null, programa_id: null });
  const [facs, setFacs] = useState([]);
  const [progs, setProgs] = useState([]);
  const [fichaId, setFichaId] = useState(null); // facultad_id para el modal de ficha
  const [editFacId, setEditFacId] = useState(null); // facultad_id para el modal de edición

  const load = () => { api.get(`/admin/${name}`).then((r) => setItems(r.data)); };
  useEffect(() => {
    load();
    if (showFacultad) api.get("/admin/facultades").then((r) => setFacs(r.data));
    if (showPrograma) api.get("/admin/programas").then((r) => setProgs(r.data));
  }, [name]);

  const create = async () => {
    try { await api.post(`/admin/${name}`, form); toast.success("Creado"); setOpen(false); setForm({ nombre: "", codigo: "", facultad_id: null, programa_id: null }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };
  const remove = async (id) => {
    if (!window.confirm("¿Eliminar?")) return;
    await api.delete(`/admin/${name}/${id}`); toast.success("Eliminado"); load();
  };

  const isFacultad = name === "facultades";

  return (
    <div className="dense-card p-5 mt-4">
      <div className="flex justify-between items-end mb-4">
        <div>
          <p className="label-eyebrow">{label}s</p>
          <h3 className="font-display font-bold text-lg tracking-tight">{items.length} registrados</h3>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid={`create-${name}-btn`}>
              <Plus className="w-4 h-4 mr-2" /> Nuevo {label}
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle className="font-display">Nuevo {label}</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div><Label className="label-eyebrow">Nombre</Label><Input className="rounded-sm" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} data-testid={`${name}-nombre`} /></div>
              <div><Label className="label-eyebrow">Código</Label><Input className="rounded-sm" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></div>
              {showFacultad && (
                <div>
                  <Label className="label-eyebrow">Facultad</Label>
                  <Select value={form.facultad_id || ""} onValueChange={(v) => setForm({ ...form, facultad_id: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                    <SelectContent>{facs.map((f) => <SelectItem key={f.id} value={f.id}>{f.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
              {showPrograma && (
                <div>
                  <Label className="label-eyebrow">Programa</Label>
                  <Select value={form.programa_id || ""} onValueChange={(v) => setForm({ ...form, programa_id: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                    <SelectContent>{progs.map((p) => <SelectItem key={p.id} value={p.id}>{p.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid={`${name}-submit`}>Crear</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <Table>
        <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Código</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
        <TableBody>
          {items.map((it) => (
            <TableRow key={it.id}>
              <TableCell className="text-xs">{it.nombre}</TableCell>
              <TableCell className="text-xs mono">{it.codigo || "—"}</TableCell>
              <TableCell className="text-right">
                {isFacultad && (
                  <>
                    <Button variant="ghost" size="sm" onClick={() => setFichaId(it.id)} title="Ver ficha" data-testid={`ficha-fac-${it.id}`}>
                      <Eye className="w-3.5 h-3.5 text-[#0033A0]" />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => setEditFacId(it.id)} title="Editar facultad" data-testid={`edit-fac-${it.id}`}>
                      <Pencil className="w-3.5 h-3.5 text-amber-700" />
                    </Button>
                  </>
                )}
                <Button variant="ghost" size="sm" onClick={() => remove(it.id)}><Trash2 className="w-3 h-3 text-[#E3000F]" /></Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {isFacultad && fichaId && <FichaFacultadDialog facultadId={fichaId} onClose={() => setFichaId(null)} />}
      {isFacultad && editFacId && (
        <EditFacultadDialog
          facultadId={editFacId}
          facultad={items.find((x) => x.id === editFacId)}
          onClose={() => setEditFacId(null)}
          onSaved={() => { setEditFacId(null); load(); }}
        />
      )}
    </div>
  );
}


// -------------- Ficha rica de Facultad --------------
function FichaFacultadDialog({ facultadId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/admin/facultades/${facultadId}/ficha`)
      .then((r) => setData(r.data))
      .catch(() => toast.error("No se pudo cargar la ficha"))
      .finally(() => setLoading(false));
  }, [facultadId]);

  return (
    <Dialog open={true} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="ficha-facultad-dialog">
        <DialogHeader>
          <DialogTitle className="font-display flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#0033A0]" />
            {loading ? "Cargando ficha…" : (data?.facultad?.nombre || "Facultad")}
          </DialogTitle>
          <DialogDescription>
            Vista completa de la facultad: KPIs académicos, decano, coordinadores, programas, tendencia por periodo y distribución territorial.
          </DialogDescription>
        </DialogHeader>
        {loading && <div className="p-8 text-center text-muted-foreground text-sm">Cargando información…</div>}
        {!loading && data && (
          <div className="space-y-5">
            {/* Descripción */}
            {data.facultad?.descripcion && (
              <div className="dense-card p-3 border-l-4 border-[#0033A0] bg-[#0033A0]/5">
                <p className="label-eyebrow text-[#0033A0] mb-1">Descripción</p>
                <p className="text-xs leading-relaxed whitespace-pre-line">{data.facultad.descripcion}</p>
              </div>
            )}

            {/* KPIs */}
            <div>
              <p className="label-eyebrow text-[#0033A0] mb-2">Indicadores académicos</p>
              <div className="grid grid-cols-3 md:grid-cols-6 gap-2">
                <StatCard label="Estudiantes" value={data.kpis.total_estudiantes} />
                <StatCard label="Promedio" value={data.kpis.promedio?.toFixed(2)} accent="text-[#0033A0]" />
                <StatCard label="% Aprobación" value={`${data.kpis.tasa_aprobacion}%`} accent="text-emerald-700" />
                <StatCard label="Riesgo académico" value={data.kpis.en_riesgo} accent="text-[#E3000F]" />
                <StatCard label="Alerta primer nivel" value={data.kpis.alerta_primer_nivel} accent="text-amber-700" />
                <StatCard label="Vulnerables" value={data.kpis.vulnerables} accent="text-amber-700" />
                <StatCard label="Rurales" value={data.kpis.rurales} />
                <StatCard label="Programas" value={data.kpis.n_programas} />
                <StatCard label="Docentes" value={data.kpis.n_docentes} />
                <StatCard label="Grupos" value={data.kpis.n_grupos} />
                <StatCard label="Víctimas" value={data.kpis.victimas} />
                <StatCard label="Discapacidad" value={data.kpis.discapacidad} />
                <StatCard label="Activos" value={data.kpis.activos} />
              </div>
            </div>

            {/* Decano / Coordinadores */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="dense-card p-4">
                <p className="label-eyebrow text-[#0033A0] mb-2">Decano(s) asignado(s)</p>
                {data.decanos?.length === 0 && <p className="text-xs text-muted-foreground italic">Sin decano asignado a esta facultad.</p>}
                <ul className="space-y-2">
                  {data.decanos?.map((d) => (
                    <li key={d.id} className="flex items-start gap-2 text-xs border-l-2 border-[#0033A0] pl-2">
                      <div>
                        <div className="font-semibold">{d.full_name}</div>
                        <div className="text-muted-foreground">{d.email}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="dense-card p-4">
                <p className="label-eyebrow text-[#0033A0] mb-2">Coordinadores ({data.coordinadores?.length || 0})</p>
                {data.coordinadores?.length === 0 && <p className="text-xs text-muted-foreground italic">Sin coordinadores asignados.</p>}
                <ul className="space-y-2 max-h-40 overflow-y-auto">
                  {data.coordinadores?.map((c) => (
                    <li key={c.id} className="text-xs border-l-2 border-amber-500 pl-2">
                      <div className="font-semibold">{c.full_name}</div>
                      <div className="text-muted-foreground">{c.email}</div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Programas */}
            <div>
              <p className="label-eyebrow text-[#0033A0] mb-2">Programas de la facultad ({data.programas?.length || 0})</p>
              <div className="dense-card p-2 max-h-64 overflow-y-auto">
                <Table>
                  <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Código</TableHead><TableHead className="text-right">Estudiantes</TableHead><TableHead className="text-right">Promedio</TableHead></TableRow></TableHeader>
                  <TableBody>
                    {data.programas?.map((p) => (
                      <TableRow key={p.id}>
                        <TableCell className="text-xs">{p.nombre}</TableCell>
                        <TableCell className="text-[10px] mono text-muted-foreground">{p.codigo || "—"}</TableCell>
                        <TableCell className="text-xs text-right">{p.n_estudiantes?.toLocaleString("es-CO")}</TableCell>
                        <TableCell className="text-xs text-right"><b>{p.promedio ? p.promedio.toFixed(2) : "—"}</b></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>

            {/* Distribución territorial */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="dense-card p-4">
                <p className="label-eyebrow text-[#0033A0] mb-2 flex items-center gap-2"><TrendingUp className="w-3 h-3" /> Tendencia por periodo</p>
                {data.tendencia?.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">Sin datos históricos.</p>
                ) : (
                  <Table>
                    <TableHeader><TableRow><TableHead>Periodo</TableHead><TableHead className="text-right">Promedio</TableHead><TableHead className="text-right">% Aprob.</TableHead><TableHead className="text-right">Notas</TableHead></TableRow></TableHeader>
                    <TableBody>
                      {data.tendencia?.map((t) => (
                        <TableRow key={t.periodo}>
                          <TableCell className="text-xs mono">{t.periodo}</TableCell>
                          <TableCell className="text-xs text-right"><b>{t.promedio}</b></TableCell>
                          <TableCell className="text-xs text-right text-emerald-700">{t.tasa_aprobacion}%</TableCell>
                          <TableCell className="text-xs text-right text-muted-foreground">{t.n_notas}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
              <div className="dense-card p-4">
                <p className="label-eyebrow text-[#0033A0] mb-2">Top departamentos de residencia</p>
                {data.distribucion_territorial?.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">Sin datos territoriales.</p>
                ) : (
                  <ul className="space-y-1">
                    {data.distribucion_territorial?.map((d) => (
                      <li key={d.departamento} className="text-xs flex items-center justify-between border-b border-border/40 pb-1">
                        <span>{d.departamento}</span>
                        <b>{d.n?.toLocaleString("es-CO")}</b>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}


// -------------- Edición de Facultad --------------
function EditFacultadDialog({ facultadId, facultad, onClose, onSaved }) {
  const [form, setForm] = useState({
    nombre: facultad?.nombre || "",
    descripcion: facultad?.descripcion || "",
    codigo: facultad?.codigo || "",
    decano_principal_id: facultad?.decano_principal_id || "",
  });
  const [decanos, setDecanos] = useState([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Cargar TODOS los usuarios con rol decano para poder asignar el principal
    api.get("/admin/users")
      .then((r) => setDecanos((r.data || []).filter((u) => u.role === "decano" && u.active !== false)))
      .catch(() => setDecanos([]));
    // Refrescar facultad por si el listado no trae descripcion/decano_principal_id
    api.get(`/admin/facultades/${facultadId}/ficha`)
      .then((r) => {
        const f = r.data?.facultad || {};
        setForm((prev) => ({
          nombre: f.nombre ?? prev.nombre,
          descripcion: f.descripcion ?? prev.descripcion ?? "",
          codigo: f.codigo ?? prev.codigo ?? "",
          decano_principal_id: f.decano_principal_id ?? prev.decano_principal_id ?? "",
        }));
      })
      .catch(() => {});
  }, [facultadId]);

  const save = async () => {
    if (!form.nombre.trim()) {
      toast.error("El nombre es obligatorio");
      return;
    }
    setSaving(true);
    try {
      await api.put(`/admin/facultades/${facultadId}`, {
        nombre: form.nombre.trim(),
        descripcion: form.descripcion,
        codigo: form.codigo || null,
        decano_principal_id: form.decano_principal_id || null,
      });
      toast.success("Facultad actualizada");
      onSaved?.();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Error al actualizar la facultad");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={true} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-lg" data-testid="edit-facultad-dialog">
        <DialogHeader>
          <DialogTitle className="font-display flex items-center gap-2">
            <Pencil className="w-4 h-4 text-amber-700" /> Editar facultad
          </DialogTitle>
          <DialogDescription>
            Modifica el nombre, la descripción y el decano principal de la facultad. Al cambiar el nombre se propagará a estudiantes, grupos y programas.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="label-eyebrow">Nombre <span className="text-[#E3000F]">*</span></Label>
            <Input
              className="rounded-sm"
              value={form.nombre}
              onChange={(e) => setForm({ ...form, nombre: e.target.value })}
              data-testid="edit-fac-nombre"
            />
          </div>
          <div>
            <Label className="label-eyebrow">Código</Label>
            <Input
              className="rounded-sm"
              value={form.codigo}
              onChange={(e) => setForm({ ...form, codigo: e.target.value })}
              placeholder="Opcional (ej. FCEAC)"
              data-testid="edit-fac-codigo"
            />
          </div>
          <div>
            <Label className="label-eyebrow">Decano principal</Label>
            <Select
              value={form.decano_principal_id || "__none__"}
              onValueChange={(v) => setForm({ ...form, decano_principal_id: v === "__none__" ? "" : v })}
            >
              <SelectTrigger className="rounded-sm" data-testid="edit-fac-decano">
                <SelectValue placeholder="Seleccionar decano principal…" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__none__">— Sin decano principal —</SelectItem>
                {decanos.length === 0 && (
                  <SelectItem value="__nodata__" disabled>
                    No hay usuarios con rol Decano
                  </SelectItem>
                )}
                {decanos.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.full_name} · {d.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-[10px] text-muted-foreground mt-1">
              El usuario seleccionado quedará vinculado a esta facultad automáticamente.
            </p>
          </div>
          <div>
            <Label className="label-eyebrow">Descripción</Label>
            <Textarea
              className="rounded-sm min-h-[100px]"
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              placeholder="Descripción, misión o áreas académicas de la facultad…"
              data-testid="edit-fac-descripcion"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} className="rounded-sm" data-testid="edit-fac-cancel">
            Cancelar
          </Button>
          <Button
            onClick={save}
            disabled={saving}
            className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white"
            data-testid="edit-fac-save"
          >
            <Save className="w-4 h-4 mr-2" /> {saving ? "Guardando…" : "Guardar cambios"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}




// -------------- Programas: vista rica con detalle --------------
function ProgramasTab() {
  const [items, setItems] = useState([]);
  const [facs, setFacs] = useState([]);
  const [q, setQ] = useState("");
  const [nivelFilter, setNivelFilter] = useState("all");
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState({});
  const [form, setForm] = useState({
    nombre: "", nombre_corto: "", codigo: "", facultad_id: "",
    nivel: "Pregrado", modalidad: "Virtual", estado: "Activo",
  });

  const load = () => api.get("/admin/programas").then((r) => setItems(r.data || []));
  useEffect(() => {
    load();
    api.get("/admin/facultades").then((r) => setFacs(r.data || []));
  }, []);

  const create = async () => {
    if (!form.nombre) return toast.error("El nombre es obligatorio");
    try {
      await api.post("/admin/programas", form);
      toast.success("Programa creado");
      setOpen(false);
      setForm({ nombre: "", nombre_corto: "", codigo: "", facultad_id: "", nivel: "Pregrado", modalidad: "Virtual", estado: "Activo" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const remove = async (id) => {
    if (!window.confirm("¿Eliminar este programa?")) return;
    await api.delete(`/admin/programas/${id}`);
    toast.success("Eliminado"); load();
  };

  const startEdit = (p) => {
    setEditForm({
      nombre: p.nombre || "", nombre_corto: p.nombre_corto || "",
      codigo: p.codigo || "", facultad_id: p.facultad_id || "",
      nivel: p.nivel || "Pregrado", modalidad: p.modalidad || "Virtual",
      estado: p.estado || "Activo",
    });
    setEditMode(true);
  };

  const saveEdit = async () => {
    if (!detail?.id) return;
    try {
      // Sync facultad_nombre based on facultad_id
      const fac = facs.find((f) => f.id === editForm.facultad_id);
      const payload = { ...editForm };
      if (fac) payload.facultad_nombre = fac.nombre;
      await api.put(`/admin/programas/${detail.id}`, payload);
      toast.success("Programa actualizado");
      setEditMode(false);
      await load();
      // Refresh detail with new data
      const refreshed = { ...detail, ...payload };
      setDetail(refreshed);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Error al guardar");
    }
  };

  const filtered = items.filter((p) => {
    if (nivelFilter !== "all" && (p.nivel || "").toLowerCase() !== nivelFilter.toLowerCase()) return false;
    if (!q) return true;
    const s = q.toLowerCase();
    return (p.nombre || "").toLowerCase().includes(s) ||
      (p.codigo || "").toLowerCase().includes(s) ||
      (p.facultad_nombre || "").toLowerCase().includes(s);
  });

  const nivelBadge = (n) => {
    const cls = {
      "Pregrado": "bg-[#0033A0]/10 text-[#0033A0] border-[#0033A0]/30",
      "Posgrado": "bg-purple-500/10 text-purple-700 border-purple-500/30",
      "Extensión Académica": "bg-[#FFCD00]/20 text-[#7A6300] border-[#FFCD00]/40",
    }[n] || "bg-muted text-muted-foreground border-border";
    return <Badge variant="outline" className={`text-[9px] uppercase tracking-wider rounded-sm ${cls}`}>{n || "Sin nivel"}</Badge>;
  };

  return (
    <div className="dense-card p-5 mt-4">
      <div className="flex flex-wrap gap-3 justify-between items-end mb-4">
        <div>
          <p className="label-eyebrow">Catálogo</p>
          <h3 className="font-display font-bold text-lg tracking-tight">
            {filtered.length} <span className="text-muted-foreground text-sm font-normal">de {items.length} programas</span>
          </h3>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <Input
            placeholder="Buscar por nombre, código o facultad…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="rounded-sm w-72"
            data-testid="programas-search"
          />
          <Select value={nivelFilter} onValueChange={setNivelFilter}>
            <SelectTrigger className="rounded-sm w-48" data-testid="programas-nivel-filter">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los niveles</SelectItem>
              <SelectItem value="Pregrado">Pregrado</SelectItem>
              <SelectItem value="Posgrado">Posgrado</SelectItem>
              <SelectItem value="Extensión Académica">Extensión Académica</SelectItem>
            </SelectContent>
          </Select>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="create-programa-btn">
                <Plus className="w-4 h-4 mr-2" /> Nuevo programa
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle className="font-display">Nuevo programa</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label className="label-eyebrow">Nombre</Label><Input className="rounded-sm" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="label-eyebrow">Nombre corto</Label><Input className="rounded-sm" value={form.nombre_corto} onChange={(e) => setForm({ ...form, nombre_corto: e.target.value })} /></div>
                  <div><Label className="label-eyebrow">Código SNIES</Label><Input className="rounded-sm" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} /></div>
                </div>
                <div>
                  <Label className="label-eyebrow">Facultad</Label>
                  <Select value={form.facultad_id} onValueChange={(v) => setForm({ ...form, facultad_id: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                    <SelectContent>{facs.map((f) => <SelectItem key={f.id} value={f.id}>{f.nombre}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <Label className="label-eyebrow">Nivel</Label>
                    <Select value={form.nivel} onValueChange={(v) => setForm({ ...form, nivel: v })}>
                      <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Pregrado">Pregrado</SelectItem>
                        <SelectItem value="Posgrado">Posgrado</SelectItem>
                        <SelectItem value="Extensión Académica">Extensión Académica</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="label-eyebrow">Modalidad</Label>
                    <Select value={form.modalidad} onValueChange={(v) => setForm({ ...form, modalidad: v })}>
                      <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Virtual">Virtual</SelectItem>
                        <SelectItem value="Presencial">Presencial</SelectItem>
                        <SelectItem value="Distancia">Distancia</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label className="label-eyebrow">Estado</Label>
                    <Select value={form.estado} onValueChange={(v) => setForm({ ...form, estado: v })}>
                      <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="Activo">Activo</SelectItem>
                        <SelectItem value="Inactivo">Inactivo</SelectItem>
                        <SelectItem value="Suspendido">Suspendido</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
              <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm">Crear</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="text-[10px] uppercase tracking-wider">Nombre</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider">Código</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider">Facultad</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider">Nivel</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider">Modalidad</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider">Estado</TableHead>
            <TableHead className="text-[10px] uppercase tracking-wider text-right"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((p) => (
            <TableRow key={p.id} className="hover:bg-muted/40">
              <TableCell className="text-xs font-medium">{p.nombre}</TableCell>
              <TableCell className="text-[11px] mono text-muted-foreground">{p.codigo || "—"}</TableCell>
              <TableCell className="text-[11px]">{p.facultad_corta || (p.facultad_nombre?.length > 30 ? p.facultad_nombre.slice(0, 28) + "…" : p.facultad_nombre) || "—"}</TableCell>
              <TableCell>{nivelBadge(p.nivel)}</TableCell>
              <TableCell className="text-[11px]">{p.modalidad || "—"}</TableCell>
              <TableCell>
                <Badge variant="outline" className={`text-[9px] uppercase tracking-wider rounded-sm ${p.estado === "Activo" ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/30" : "bg-muted text-muted-foreground"}`}>
                  {p.estado || "—"}
                </Badge>
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => setDetail(p)} data-testid={`programa-detail-${p.id}`} title="Ver detalle">
                  <Eye className="w-3.5 h-3.5" />
                </Button>
                <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => { setDetail(p); startEdit(p); }} data-testid={`programa-edit-${p.id}`} title="Editar">
                  <Pencil className="w-3.5 h-3.5 text-[#0033A0]" />
                </Button>
                <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => remove(p.id)} title="Eliminar">
                  <Trash2 className="w-3 h-3 text-[#E3000F]" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
          {filtered.length === 0 && (
            <TableRow><TableCell colSpan={7} className="text-center text-xs text-muted-foreground py-6">Sin programas con esos criterios</TableCell></TableRow>
          )}
        </TableBody>
      </Table>

      {/* Detalle modal */}
      <Dialog open={!!detail} onOpenChange={(v) => { if (!v) { setDetail(null); setEditMode(false); } }}>
        <DialogContent className="max-w-2xl" data-testid="programa-detail-dialog">
          <DialogHeader>
            <DialogTitle className="font-display tracking-tight flex items-center justify-between gap-4">
              <span>{editMode ? "Editar programa" : detail?.nombre}</span>
              {detail && !editMode && (
                <Button size="sm" variant="outline" className="rounded-sm" onClick={() => startEdit(detail)} data-testid="programa-modal-edit-btn">
                  <Pencil className="w-3 h-3 mr-1" /> Editar
                </Button>
              )}
            </DialogTitle>
          </DialogHeader>
          {detail && !editMode && (
            <div className="space-y-4">
              <div className="flex flex-wrap gap-2">
                {nivelBadge(detail.nivel)}
                <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">{detail.modalidad || "Sin modalidad"}</Badge>
                <Badge variant="outline" className={`text-[9px] uppercase tracking-wider rounded-sm ${detail.estado === "Activo" ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/30" : ""}`}>{detail.estado || "—"}</Badge>
              </div>

              <div className="grid grid-cols-2 gap-4 pt-2">
                <DetailRow label="Nombre completo" value={detail.nombre} />
                <DetailRow label="Nombre corto" value={detail.nombre_corto} />
                <DetailRow label="Código SNIES" value={detail.codigo} mono />
                <DetailRow label="Nivel académico" value={detail.nivel} />
                <DetailRow label="Modalidad" value={detail.modalidad} />
                <DetailRow label="Estado" value={detail.estado} />
                <DetailRow label="Facultad" value={detail.facultad_nombre} full />
                <DetailRow label="Facultad (corta)" value={detail.facultad_corta} />
                <DetailRow label="ID interno" value={detail.id} mono full />
              </div>

              <div className="pt-2 border-t border-border">
                <p className="label-eyebrow mb-2">Estadísticas</p>
                <ProgramaStats programa={detail.nombre} />
              </div>
            </div>
          )}

          {detail && editMode && (
            <div className="space-y-3">
              <div><Label className="label-eyebrow">Nombre completo</Label>
                <Input className="rounded-sm" value={editForm.nombre} onChange={(e) => setEditForm({ ...editForm, nombre: e.target.value })} data-testid="edit-nombre" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label className="label-eyebrow">Nombre corto</Label>
                  <Input className="rounded-sm" value={editForm.nombre_corto} onChange={(e) => setEditForm({ ...editForm, nombre_corto: e.target.value })} />
                </div>
                <div><Label className="label-eyebrow">Código SNIES</Label>
                  <Input className="rounded-sm" value={editForm.codigo} onChange={(e) => setEditForm({ ...editForm, codigo: e.target.value })} />
                </div>
              </div>
              <div>
                <Label className="label-eyebrow">Facultad</Label>
                <Select value={editForm.facultad_id} onValueChange={(v) => setEditForm({ ...editForm, facultad_id: v })}>
                  <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                  <SelectContent>{facs.map((f) => <SelectItem key={f.id} value={f.id}>{f.nombre}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <Label className="label-eyebrow">Nivel</Label>
                  <Select value={editForm.nivel} onValueChange={(v) => setEditForm({ ...editForm, nivel: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Pregrado">Pregrado</SelectItem>
                      <SelectItem value="Posgrado">Posgrado</SelectItem>
                      <SelectItem value="Extensión Académica">Extensión Académica</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="label-eyebrow">Modalidad</Label>
                  <Select value={editForm.modalidad} onValueChange={(v) => setEditForm({ ...editForm, modalidad: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Virtual">Virtual</SelectItem>
                      <SelectItem value="Presencial">Presencial</SelectItem>
                      <SelectItem value="Distancia">Distancia</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="label-eyebrow">Estado</Label>
                  <Select value={editForm.estado} onValueChange={(v) => setEditForm({ ...editForm, estado: v })}>
                    <SelectTrigger className="rounded-sm"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Activo">Activo</SelectItem>
                      <SelectItem value="Inactivo">Inactivo</SelectItem>
                      <SelectItem value="Suspendido">Suspendido</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-3 border-t border-border">
                <Button variant="outline" className="rounded-sm" onClick={() => setEditMode(false)}>Cancelar</Button>
                <Button className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" onClick={saveEdit} data-testid="programa-save-btn">
                  <Save className="w-3.5 h-3.5 mr-1" /> Guardar cambios
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function DetailRow({ label, value, mono, full }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="label-eyebrow">{label}</div>
      <div className={`text-sm mt-0.5 ${mono ? "font-mono text-xs" : ""}`}>{value || <span className="text-muted-foreground italic">Sin dato</span>}</div>
    </div>
  );
}

function ProgramaStats({ programa }) {
  const [stats, setStats] = useState(null);
  useEffect(() => {
    if (!programa) return;
    api.get(`/dashboards/executive?programa=${encodeURIComponent(programa.toUpperCase())}`)
      .then((r) => setStats(r.data?.kpis || null))
      .catch(() => setStats({}));
  }, [programa]);
  if (!stats) return <div className="text-xs text-muted-foreground italic">Calculando…</div>;
  return (
    <div className="grid grid-cols-4 gap-3">
      <div><span className="label-eyebrow block">Estudiantes</span><b className="kpi-num text-xl">{(stats.total || 0).toLocaleString("es-CO")}</b></div>
      <div><span className="label-eyebrow block">Matriculados</span><b className="kpi-num text-xl">{(stats.matriculados || 0).toLocaleString("es-CO")}</b></div>
      <div><span className="label-eyebrow block">Promedio</span><b className={`kpi-num text-xl ${(stats.promedio || 0) < 3 ? "text-[#E3000F]" : "text-emerald-700"}`}>{(stats.promedio || 0).toFixed(2)}</b></div>
      <div><span className="label-eyebrow block">Avance</span><b className="kpi-num text-xl">{(stats.avance_pct || 0).toFixed(0)}%</b></div>
    </div>
  );
}

function DocenteMateriaTab() {
  const [items, setItems] = useState([]);
  const [users, setUsers] = useState([]);
  const [materias, setMaterias] = useState([]);
  const [periodos, setPeriodos] = useState([]);
  const [form, setForm] = useState({ docente_id: "", materia_id: "", periodo: "" });
  const [open, setOpen] = useState(false);

  const load = () => Promise.all([
    api.get("/admin/docente-materia").then((r) => setItems(r.data)),
    api.get("/admin/users").then((r) => setUsers(r.data.filter((u) => u.role === "profesor"))),
    api.get("/admin/materias").then((r) => setMaterias(r.data)),
    api.get("/admin/periodos").then((r) => setPeriodos(r.data)),
  ]);
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.docente_id || !form.materia_id || !form.periodo) return toast.error("Complete todos los campos");
    try { await api.post("/admin/docente-materia", form); toast.success("Relación creada"); setOpen(false); setForm({ docente_id: "", materia_id: "", periodo: "" }); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const remove = async (id) => {
    await api.delete(`/admin/docente-materia/${id}`); toast.success("Eliminada"); load();
  };

  const docNombre = (id) => users.find((u) => u.id === id)?.full_name || id;
  const matNombre = (id) => materias.find((m) => m.id === id)?.nombre || id;

  return (
    <div className="dense-card p-5 mt-4">
      <div className="flex justify-between items-end mb-4">
        <div>
          <p className="label-eyebrow">Relación docente–materia</p>
          <h3 className="font-display font-bold text-lg tracking-tight">{items.length} relaciones</h3>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="create-dm-btn">
              <Plus className="w-4 h-4 mr-2" /> Nueva relación
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle className="font-display">Asignar docente a materia</DialogTitle></DialogHeader>
            <div className="space-y-3">
              <div>
                <Label className="label-eyebrow">Docente</Label>
                <Select value={form.docente_id} onValueChange={(v) => setForm({ ...form, docente_id: v })}>
                  <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar docente" /></SelectTrigger>
                  <SelectContent>{users.length === 0 ? <SelectItem disabled value="empty">No hay usuarios con rol docente</SelectItem> : users.map((u) => <SelectItem key={u.id} value={u.id}>{u.full_name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="label-eyebrow">Materia</Label>
                <Select value={form.materia_id} onValueChange={(v) => setForm({ ...form, materia_id: v })}>
                  <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar materia" /></SelectTrigger>
                  <SelectContent>{materias.length === 0 ? <SelectItem disabled value="empty">No hay materias creadas</SelectItem> : materias.map((m) => <SelectItem key={m.id} value={m.id}>{m.nombre}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <Label className="label-eyebrow">Periodo</Label>
                <Select value={form.periodo} onValueChange={(v) => setForm({ ...form, periodo: v })}>
                  <SelectTrigger className="rounded-sm"><SelectValue placeholder="Seleccionar periodo" /></SelectTrigger>
                  <SelectContent>{periodos.map((p) => <SelectItem key={p.id} value={p.nombre}>{p.nombre}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid="dm-submit">Crear</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
      <Table>
        <TableHeader><TableRow><TableHead>Docente</TableHead><TableHead>Materia</TableHead><TableHead>Periodo</TableHead><TableHead></TableHead></TableRow></TableHeader>
        <TableBody>
          {items.map((it) => (
            <TableRow key={it.id}>
              <TableCell className="text-xs">{docNombre(it.docente_id)}</TableCell>
              <TableCell className="text-xs">{matNombre(it.materia_id)}</TableCell>
              <TableCell className="text-xs mono">{it.periodo}</TableCell>
              <TableCell><Button variant="ghost" size="sm" onClick={() => remove(it.id)}><Trash2 className="w-3 h-3 text-[#E3000F]" /></Button></TableCell>
            </TableRow>
          ))}
          {items.length === 0 && (<TableRow><TableCell colSpan={4} className="text-xs text-center text-muted-foreground py-6">Sin relaciones creadas</TableCell></TableRow>)}
        </TableBody>
      </Table>
    </div>
  );
}


function DivipolaTab() {
  const [items, setItems] = useState([]);
  const [paises, setPaises] = useState([]);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filterPais, setFilterPais] = useState("all");
  const [form, setForm] = useState({ codigo: "", nombre: "", departamento: "", pais: "COLOMBIA", lat: 0, lon: 0 });

  const load = () => {
    api.get("/admin/divipola").then((r) => setItems(r.data));
    api.get("/admin/divipola/paises").then((r) => setPaises(r.data));
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await api.post("/admin/divipola", form);
      toast.success("Municipio agregado");
      setOpen(false);
      setForm({ codigo: "", nombre: "", departamento: "", pais: "COLOMBIA", lat: 0, lon: 0 });
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Error");
    }
  };

  const remove = async (id) => {
    if (!window.confirm("¿Eliminar este municipio?")) return;
    await api.delete(`/admin/divipola/${id}`);
    toast.success("Eliminado");
    load();
  };

  const downloadExport = (fmt) => {
    const token = localStorage.getItem("iud_token");
    fetch(`${API}/exports/divipola?fmt=${fmt}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob()).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `divipola_${new Date().toISOString().slice(0, 10)}.${fmt}`;
        a.click();
        URL.revokeObjectURL(url);
      });
  };

  const filtered = items.filter((it) => {
    if (filterPais !== "all" && it.pais !== filterPais) return false;
    if (search && !`${it.nombre} ${it.departamento} ${it.codigo}`.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="dense-card p-5 mt-4">
      <div className="flex justify-between items-end mb-4 flex-wrap gap-3">
        <div>
          <p className="label-eyebrow flex items-center gap-2"><Globe className="w-3 h-3" /> Catálogo DIVIPOLA / Países</p>
          <h3 className="font-display font-bold text-lg tracking-tight">{items.length} municipios · {paises.length} países</h3>
          <p className="text-xs text-muted-foreground mt-1">Códigos DANE para Colombia + ciudades internacionales. Editable.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport("xlsx")} data-testid="divipola-export-xlsx">
            <Download className="w-3.5 h-3.5 mr-2" /> Excel
          </Button>
          <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport("csv")}>
            <Download className="w-3.5 h-3.5 mr-2" /> CSV
          </Button>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="divipola-create-btn">
                <Plus className="w-4 h-4 mr-2" /> Nuevo municipio
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle className="font-display">Agregar municipio / ciudad</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="label-eyebrow">Código DANE</Label><Input className="rounded-sm" value={form.codigo} onChange={(e) => setForm({ ...form, codigo: e.target.value })} placeholder="05001" data-testid="divipola-codigo" /></div>
                  <div><Label className="label-eyebrow">País</Label><Input className="rounded-sm" value={form.pais} onChange={(e) => setForm({ ...form, pais: e.target.value })} placeholder="COLOMBIA" /></div>
                </div>
                <div><Label className="label-eyebrow">Nombre municipio</Label><Input className="rounded-sm" value={form.nombre} onChange={(e) => setForm({ ...form, nombre: e.target.value })} data-testid="divipola-nombre" /></div>
                <div><Label className="label-eyebrow">Departamento / región</Label><Input className="rounded-sm" value={form.departamento} onChange={(e) => setForm({ ...form, departamento: e.target.value })} placeholder="ANTIOQUIA" /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label className="label-eyebrow">Latitud</Label><Input type="number" step="0.0001" className="rounded-sm" value={form.lat} onChange={(e) => setForm({ ...form, lat: parseFloat(e.target.value) })} /></div>
                  <div><Label className="label-eyebrow">Longitud</Label><Input type="number" step="0.0001" className="rounded-sm" value={form.lon} onChange={(e) => setForm({ ...form, lon: parseFloat(e.target.value) })} /></div>
                </div>
              </div>
              <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid="divipola-submit">Crear</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-3 flex-wrap">
        <Input placeholder="Buscar por nombre, depto o código…" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-xs rounded-sm h-9" data-testid="divipola-search" />
        <Select value={filterPais} onValueChange={setFilterPais}>
          <SelectTrigger className="w-48 h-9 rounded-sm" data-testid="divipola-filter-pais"><SelectValue placeholder="País" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los países</SelectItem>
            {paises.filter((p) => p?.pais && p.pais.trim() !== "").map((p) => <SelectItem key={p.pais} value={p.pais}>{p.pais} ({p.n})</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="text-xs text-muted-foreground mb-2">Mostrando {filtered.length} de {items.length}</div>

      <div className="max-h-[500px] overflow-y-auto">
        <Table>
          <TableHeader className="sticky top-0 bg-card">
            <TableRow>
              <TableHead className="text-[10px] uppercase tracking-wider">Código</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Municipio</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Departamento</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">País</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Lat / Lon</TableHead>
              <TableHead className="text-[10px] uppercase tracking-wider">Fuente</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.slice(0, 500).map((it) => (
              <TableRow key={it.id}>
                <TableCell className="text-xs mono">{it.codigo}</TableCell>
                <TableCell className="text-xs font-medium">{it.nombre}</TableCell>
                <TableCell className="text-xs">{it.departamento}</TableCell>
                <TableCell><Badge variant="outline" className="text-[10px] rounded-sm uppercase tracking-wider">{it.pais}</Badge></TableCell>
                <TableCell className="text-[10px] text-muted-foreground mono">{it.lat?.toFixed(3)}, {it.lon?.toFixed(3)}</TableCell>
                <TableCell className="text-[10px] text-muted-foreground">{it.fuente}</TableCell>
                <TableCell><Button variant="ghost" size="sm" onClick={() => remove(it.id)}><Trash2 className="w-3 h-3 text-[#E3000F]" /></Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {filtered.length > 500 && <div className="text-xs text-muted-foreground text-center py-3">… y {filtered.length - 500} más. Use el filtro de país o búsqueda para refinar.</div>}
      </div>
    </div>
  );
}


// =============================================================================
// DOCENTES TAB — Vista enriquecida con documento, correos, grupos y estudiantes
// =============================================================================
function DocentesTab() {
  const [docentes, setDocentes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    api.get("/admin/docentes")
      .then((r) => setDocentes(r.data))
      .finally(() => setLoading(false));
  }, []);

  const openDetail = async (d) => {
    setSelected(d);
    setDetail(null);
    try {
      const r = await api.get(`/admin/docentes/${d.id}/grupos`);
      setDetail(r.data);
    } catch (e) {
      toast.error("Error al cargar detalle");
    }
  };

  const q = query.trim().toLowerCase();
  const filtered = q
    ? docentes.filter((d) =>
        [d.full_name, d.email, d.cedula, d.correo_personal, d.correo_institucional, d.iddoc]
          .filter(Boolean).some((v) => String(v).toLowerCase().includes(q))
      )
    : docentes;

  const exportCSV = () => {
    const cols = ["Documento", "Nombre", "Correo institucional", "Correo personal", "IDDOC", "Grupos", "Materias", "Estudiantes", "Programas", "Periodos"];
    const rows = filtered.map((d) => [
      d.cedula || "", d.full_name || "", d.correo_institucional || d.email || "",
      d.correo_personal || "", d.iddoc || "",
      d.n_grupos || 0, d.n_materias || 0, d.n_estudiantes || 0,
      (d.programas || []).join(" | "), (d.periodos || []).join(", "),
    ]);
    const csv = [cols, ...rows].map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `docentes_${new Date().toISOString().slice(0,10)}.csv`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4 mt-4" data-testid="docentes-tab">
      <div className="flex justify-between items-center gap-3 flex-wrap">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Cuerpo docente</p>
          <p className="text-2xl font-display font-black">{docentes.length} docentes</p>
          <p className="text-xs text-muted-foreground">Con documento, correos institucional/personal y asignación actual.</p>
        </div>
        <div className="flex gap-2 items-center">
          <Input
            placeholder="Buscar por nombre, cédula, correo…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="rounded-sm w-72"
            data-testid="docentes-search"
          />
          <Button variant="outline" size="sm" onClick={exportCSV} className="rounded-sm" data-testid="docentes-export">
            <Download className="w-3 h-3 mr-1" />Exportar CSV
          </Button>
        </div>
      </div>

      <div className="rounded-sm border overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Documento</TableHead>
              <TableHead>Nombre</TableHead>
              <TableHead>Correo institucional</TableHead>
              <TableHead>Correo personal</TableHead>
              <TableHead className="text-right">Grupos</TableHead>
              <TableHead className="text-right">Materias</TableHead>
              <TableHead className="text-right">Estudiantes</TableHead>
              <TableHead>Programas</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && <TableRow><TableCell colSpan={9} className="text-center py-8 text-xs text-muted-foreground">Cargando docentes…</TableCell></TableRow>}
            {!loading && filtered.slice(0, 500).map((d) => (
              <TableRow key={d.id} className="hover:bg-slate-50/50">
                <TableCell className="text-[11px] font-mono">{d.cedula || "—"}</TableCell>
                <TableCell className="text-xs font-medium">{d.full_name}</TableCell>
                <TableCell className="text-[11px] text-muted-foreground">{d.correo_institucional || d.email || "—"}</TableCell>
                <TableCell className="text-[11px] text-muted-foreground">{d.correo_personal || "—"}</TableCell>
                <TableCell className="text-right text-xs font-semibold">{d.n_grupos || 0}</TableCell>
                <TableCell className="text-right text-xs">{d.n_materias || 0}</TableCell>
                <TableCell className="text-right text-xs">{d.n_estudiantes || 0}</TableCell>
                <TableCell className="text-[10px] text-muted-foreground max-w-[220px] truncate" title={(d.programas || []).join(" | ")}>{(d.programas || []).slice(0, 2).join(" | ") || "—"}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="sm" onClick={() => openDetail(d)} data-testid={`docente-detail-${d.id}`}>
                    <Eye className="w-3 h-3" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {filtered.length > 500 && <div className="text-xs text-muted-foreground text-center py-3">Mostrando 500 de {filtered.length}. Usa el buscador para refinar.</div>}
      </div>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display">{selected?.full_name}</DialogTitle>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div><p className="label-eyebrow">Documento</p><p className="font-mono">{selected.cedula || "—"}</p></div>
                <div><p className="label-eyebrow">IDDOC</p><p className="font-mono">{selected.iddoc || "—"}</p></div>
                <div><p className="label-eyebrow">Correo institucional</p><p className="break-all">{selected.correo_institucional || selected.email || "—"}</p></div>
                <div><p className="label-eyebrow">Correo personal</p><p className="break-all">{selected.correo_personal || "—"}</p></div>
                <div><p className="label-eyebrow">Grupos</p><p className="text-lg font-black">{selected.n_grupos || 0}</p></div>
                <div><p className="label-eyebrow">Materias</p><p className="text-lg font-black">{selected.n_materias || 0}</p></div>
                <div><p className="label-eyebrow">Estudiantes</p><p className="text-lg font-black">{selected.n_estudiantes || 0}</p></div>
                <div><p className="label-eyebrow">Periodos</p><p>{(selected.periodos || []).join(", ") || "—"}</p></div>
              </div>

              <div>
                <p className="label-eyebrow mb-2">Grupos asignados</p>
                {!detail && <p className="text-xs text-muted-foreground">Cargando grupos…</p>}
                {detail && detail.length === 0 && <p className="text-xs text-muted-foreground italic">Este docente no tiene grupos asignados actualmente.</p>}
                {detail && detail.length > 0 && (
                  <div className="rounded-sm border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="text-[10px]">Código grupo</TableHead>
                          <TableHead className="text-[10px]">Asignatura</TableHead>
                          <TableHead className="text-[10px]">Programa</TableHead>
                          <TableHead className="text-[10px]">Periodo</TableHead>
                          <TableHead className="text-[10px] text-right">Estudiantes</TableHead>
                          <TableHead className="text-[10px]">Histórico</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detail.map((g) => (
                          <TableRow key={g.codigo_grupo}>
                            <TableCell className="text-[10px] font-mono">{g.codigo_grupo}</TableCell>
                            <TableCell className="text-[10px]">{g.asignatura_nombre}</TableCell>
                            <TableCell className="text-[10px] text-muted-foreground">{g.programa || "—"}</TableCell>
                            <TableCell className="text-[10px]">{g.periodo}</TableCell>
                            <TableCell className="text-[10px] text-right font-semibold">{g.n_estudiantes}</TableCell>
                            <TableCell className="text-[10px] text-muted-foreground">
                              {(g.historico_notas || []).map((h) => (
                                <div key={h.periodo}>{h.periodo}: <b>{h.promedio.toFixed(2)}</b> ({h.n})</div>
                              ))}
                              {(!g.historico_notas || g.historico_notas.length === 0) && <span className="italic">sin notas</span>}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
