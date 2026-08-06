import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Trash2, UserPlus, Globe, Download, Eye, Pencil, Save } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";

const ROLES = ["superadmin", "admin", "docente", "viewer"];

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
          <TabsTrigger value="users" data-testid="tab-users">Usuarios</TabsTrigger>
          <TabsTrigger value="docentes" data-testid="tab-docentes">Docentes</TabsTrigger>
          <TabsTrigger value="facultades" data-testid="tab-facultades">Facultades</TabsTrigger>
          <TabsTrigger value="programas" data-testid="tab-programas">Programas</TabsTrigger>
          <TabsTrigger value="materias" data-testid="tab-materias">Materias</TabsTrigger>
          <TabsTrigger value="periodos" data-testid="tab-periodos">Periodos</TabsTrigger>
          <TabsTrigger value="docente-materia" data-testid="tab-docente-materia">Docente–Materia</TabsTrigger>
          <TabsTrigger value="divipola" data-testid="tab-divipola">DIVIPOLA</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><ErrorBoundary><UsersTab /></ErrorBoundary></TabsContent>
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
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "viewer" });

  const load = () => { api.get("/admin/users").then((r) => setUsers(r.data)); };
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await api.post("/admin/users", form);
      toast.success("Usuario creado");
      setOpen(false);
      setForm({ email: "", password: "", full_name: "", role: "viewer" });
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  const remove = async (id) => {
    if (!window.confirm("¿Eliminar usuario?")) return;
    try { await api.delete(`/admin/users/${id}`); toast.success("Eliminado"); load(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
  };

  return (
    <div className="dense-card p-5 mt-4">
      <div className="flex justify-between items-end mb-4">
        <div>
          <p className="label-eyebrow">Usuarios del sistema</p>
          <h3 className="font-display font-bold text-lg tracking-tight">{users.length} registrados</h3>
        </div>
        {current?.role === "superadmin" && (
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="admin-create-user-btn">
                <UserPlus className="w-4 h-4 mr-2" /> Crear usuario
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle className="font-display">Crear usuario</DialogTitle></DialogHeader>
              <div className="space-y-3">
                <div><Label className="label-eyebrow">Nombre</Label><Input className="rounded-sm" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} data-testid="new-user-name" /></div>
                <div><Label className="label-eyebrow">Email</Label><Input type="email" className="rounded-sm" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="new-user-email" /></div>
                <div><Label className="label-eyebrow">Contraseña inicial</Label><Input type="password" className="rounded-sm" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} data-testid="new-user-password" /></div>
                <div>
                  <Label className="label-eyebrow">Rol</Label>
                  <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                    <SelectTrigger className="rounded-sm" data-testid="new-user-role"><SelectValue /></SelectTrigger>
                    <SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter><Button onClick={create} className="bg-[#0033A0] hover:bg-[#002A85] text-white rounded-sm" data-testid="new-user-submit">Crear</Button></DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nombre</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Rol</TableHead>
            <TableHead>Estado</TableHead>
            <TableHead>Creado</TableHead>
            <TableHead></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {users.map((u) => (
            <TableRow key={u.id}>
              <TableCell className="text-xs font-medium">{u.full_name}</TableCell>
              <TableCell className="text-xs">{u.email}</TableCell>
              <TableCell><Badge variant="outline" className="text-[10px] uppercase tracking-widest rounded-sm">{u.role}</Badge></TableCell>
              <TableCell><Badge variant={u.active ? "default" : "secondary"} className="text-[10px] rounded-sm">{u.active ? "Activo" : "Inactivo"}</Badge></TableCell>
              <TableCell className="text-[10px] text-muted-foreground">{u.created_at?.slice(0, 10)}</TableCell>
              <TableCell>
                {current?.role === "superadmin" && current.id !== u.id && (
                  <Button variant="ghost" size="sm" onClick={() => remove(u.id)} data-testid={`delete-user-${u.id}`}>
                    <Trash2 className="w-3 h-3 text-[#E3000F]" />
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function CatalogTab({ name, label, showFacultad, showPrograma }) {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ nombre: "", codigo: "", facultad_id: null, programa_id: null });
  const [facs, setFacs] = useState([]);
  const [progs, setProgs] = useState([]);

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
        <TableHeader><TableRow><TableHead>Nombre</TableHead><TableHead>Código</TableHead><TableHead></TableHead></TableRow></TableHeader>
        <TableBody>
          {items.map((it) => (
            <TableRow key={it.id}>
              <TableCell className="text-xs">{it.nombre}</TableCell>
              <TableCell className="text-xs mono">{it.codigo || "—"}</TableCell>
              <TableCell><Button variant="ghost" size="sm" onClick={() => remove(it.id)}><Trash2 className="w-3 h-3 text-[#E3000F]" /></Button></TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
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
    api.get("/admin/users").then((r) => setUsers(r.data.filter((u) => u.role === "docente"))),
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
