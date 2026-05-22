import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Plus, Trash2, UserPlus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

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
        <TabsList className="rounded-sm">
          <TabsTrigger value="users" data-testid="tab-users">Usuarios</TabsTrigger>
          <TabsTrigger value="facultades" data-testid="tab-facultades">Facultades</TabsTrigger>
          <TabsTrigger value="programas" data-testid="tab-programas">Programas</TabsTrigger>
          <TabsTrigger value="materias" data-testid="tab-materias">Materias</TabsTrigger>
          <TabsTrigger value="periodos" data-testid="tab-periodos">Periodos</TabsTrigger>
          <TabsTrigger value="docente-materia" data-testid="tab-docente-materia">Docente–Materia</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><UsersTab /></TabsContent>
        <TabsContent value="facultades"><CatalogTab name="facultades" label="Facultad" /></TabsContent>
        <TabsContent value="programas"><CatalogTab name="programas" label="Programa" showFacultad /></TabsContent>
        <TabsContent value="materias"><CatalogTab name="materias" label="Materia" showPrograma /></TabsContent>
        <TabsContent value="periodos"><CatalogTab name="periodos" label="Periodo" /></TabsContent>
        <TabsContent value="docente-materia"><DocenteMateriaTab /></TabsContent>
      </Tabs>
    </div>
  );
}

function UsersTab() {
  const { user: current } = useAuth();
  const [users, setUsers] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", full_name: "", role: "viewer" });

  const load = () => api.get("/admin/users").then((r) => setUsers(r.data));
  useEffect(load, []);

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

  const load = () => api.get(`/admin/${name}`).then((r) => setItems(r.data));
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
