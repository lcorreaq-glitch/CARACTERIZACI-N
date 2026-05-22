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
import { Plus, Trash2, UserPlus, Globe, Download } from "lucide-react";
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
          <TabsTrigger value="facultades" data-testid="tab-facultades">Facultades</TabsTrigger>
          <TabsTrigger value="programas" data-testid="tab-programas">Programas</TabsTrigger>
          <TabsTrigger value="materias" data-testid="tab-materias">Materias</TabsTrigger>
          <TabsTrigger value="periodos" data-testid="tab-periodos">Periodos</TabsTrigger>
          <TabsTrigger value="docente-materia" data-testid="tab-docente-materia">Docente–Materia</TabsTrigger>
          <TabsTrigger value="divipola" data-testid="tab-divipola">DIVIPOLA</TabsTrigger>
        </TabsList>
        <TabsContent value="users"><ErrorBoundary><UsersTab /></ErrorBoundary></TabsContent>
        <TabsContent value="facultades"><ErrorBoundary><CatalogTab name="facultades" label="Facultad" /></ErrorBoundary></TabsContent>
        <TabsContent value="programas"><ErrorBoundary><CatalogTab name="programas" label="Programa" showFacultad /></ErrorBoundary></TabsContent>
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
