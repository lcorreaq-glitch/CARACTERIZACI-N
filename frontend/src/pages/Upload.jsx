import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  UploadCloud, FileSpreadsheet, Loader2, AlertTriangle, RotateCcw, CheckCircle2,
  Download, FileDown, GraduationCap, Users, BookOpen, Database
} from "lucide-react";
import { useFilters, buildQuery } from "./AppLayout";

function tokenizedDownload(path, filename) {
  const token = localStorage.getItem("iud_token");
  fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } })
    .then((r) => {
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    })
    .catch((e) => toast.error(`Error en descarga: ${e.message}`));
}

export default function Upload() {
  const [uploads, setUploads] = useState([]);
  const loadAll = () => api.get("/uploads/").then((r) => setUploads(r.data || [])).catch(() => {});
  useEffect(() => { loadAll(); }, []);

  return (
    <div className="space-y-6" data-testid="upload-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Cargas y descargas</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Gestión de datos</h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-3xl">
          Suba archivos Excel para estudiantes, notas históricas y la relación docente–materia.
          También puede descargar plantillas vacías y exportar la base actual con los filtros activos.
        </p>
      </header>

      <Tabs defaultValue="fullrefresh">
        <TabsList className="rounded-sm flex-wrap h-auto">
          <TabsTrigger value="fullrefresh" data-testid="upl-tab-fullrefresh">
            <RotateCcw className="w-4 h-4 mr-2" /> Refresh completo
          </TabsTrigger>
          <TabsTrigger value="estudiantes" data-testid="upl-tab-estudiantes">
            <Users className="w-4 h-4 mr-2" /> Estudiantes
          </TabsTrigger>
          <TabsTrigger value="notas" data-testid="upl-tab-notas">
            <GraduationCap className="w-4 h-4 mr-2" /> Notas históricas
          </TabsTrigger>
          <TabsTrigger value="docente-materia" data-testid="upl-tab-dm">
            <BookOpen className="w-4 h-4 mr-2" /> Docente – Materia
          </TabsTrigger>
          <TabsTrigger value="descargas" data-testid="upl-tab-descargas">
            <Database className="w-4 h-4 mr-2" /> Descargar BD
          </TabsTrigger>
        </TabsList>

        <TabsContent value="fullrefresh" className="mt-4">
          <FullRefreshTab onDone={loadAll} />
        </TabsContent>
        <TabsContent value="estudiantes" className="mt-4">
          <StudentsUpload onIngestDone={loadAll} />
        </TabsContent>
        <TabsContent value="notas" className="mt-4">
          <SimpleUpload
            title="Cargar notas históricas"
            description="Ingesta de notas (cédula × periodo × materia × docente). Crea materias y docentes automáticamente si no existen."
            templateType="notas"
            ingestPath="/uploads/notas"
            testidPrefix="notas"
            onIngestDone={loadAll}
          />
        </TabsContent>
        <TabsContent value="docente-materia" className="mt-4">
          <SimpleUpload
            title="Cargar relación docente – materia"
            description="Asignación masiva de docentes a materias por periodo. Si el docente no existe, se crea con rol 'docente' y contraseña inicial IUDigital2026!."
            templateType="docente_materia"
            ingestPath="/uploads/docente-materia-bulk"
            testidPrefix="dm"
            onIngestDone={loadAll}
          />
        </TabsContent>
        <TabsContent value="descargas" className="mt-4">
          <DownloadsTab />
        </TabsContent>
      </Tabs>

      <div className="dense-card p-5">
        <p className="label-eyebrow">Histórico</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-4">Cargas realizadas ({uploads.length})</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tipo</TableHead>
              <TableHead>Archivo</TableHead>
              <TableHead>Periodo</TableHead>
              <TableHead className="text-right">Insertados</TableHead>
              <TableHead className="text-right">Errores</TableHead>
              <TableHead>Por</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {uploads.map((u) => (
              <TableRow key={u.id}>
                <TableCell><Badge variant="outline" className="text-[10px] uppercase tracking-wider rounded-sm">{u.tipo || "estudiantes"}</Badge></TableCell>
                <TableCell className="text-xs font-medium">{u.filename}</TableCell>
                <TableCell><span className="mono text-xs">{u.periodo || "—"}</span></TableCell>
                <TableCell className="text-right kpi-num text-sm">{(u.inserted || 0).toLocaleString("es-CO")}</TableCell>
                <TableCell className="text-right text-xs text-[#E3000F]">{u.errores || 0}</TableCell>
                <TableCell className="text-xs">{u.uploaded_by}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{new Date(u.created_at).toLocaleString("es-CO")}</TableCell>
                <TableCell>
                  {(u.tipo === undefined || u.tipo === "estudiantes") && !u.rolled_back && (
                    <Button size="sm" variant="ghost" onClick={async () => {
                      if (!window.confirm("¿Revertir esta carga? Se eliminarán los registros asociados.")) return;
                      try { await api.post(`/uploads/rollback/${u.id}`); toast.success("Carga revertida"); loadAll(); }
                      catch (e) { toast.error(e?.response?.data?.detail || "Error"); }
                    }} data-testid={`upload-rollback-${u.id}`}>
                      <RotateCcw className="w-3 h-3 mr-1" /> Revertir
                    </Button>
                  )}
                  {u.rolled_back && <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Revertida</span>}
                </TableCell>
              </TableRow>
            ))}
            {uploads.length === 0 && (<TableRow><TableCell colSpan={8} className="text-center text-xs text-muted-foreground py-6">Sin cargas registradas</TableCell></TableRow>)}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

/* ============================================================
 * Estudiantes (carga completa con periodo y previsualización)
 * ============================================================ */
function StudentsUpload({ onIngestDone }) {
  const [file, setFile] = useState(null);
  const [periodo, setPeriodo] = useState("");
  const [periodos, setPeriodos] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { api.get("/admin/periodos").then((r) => setPeriodos(r.data || [])); }, []);

  const doPreview = async () => {
    if (!file) return toast.error("Seleccione un archivo");
    setLoading(true); setPreview(null);
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api.post("/uploads/preview", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(r.data);
    } catch (err) { toast.error(err?.response?.data?.detail || "Error de previsualización"); }
    finally { setLoading(false); }
  };

  const ingest = async () => {
    if (!periodo) return toast.error("Seleccione un periodo");
    if (preview?.missing_required?.length) return toast.error("Faltan columnas obligatorias");
    setLoading(true);
    const fd = new FormData(); fd.append("file", file); fd.append("periodo", periodo);
    try {
      const r = await api.post("/uploads/ingest", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Cargados ${r.data.inserted} estudiantes en ${r.data.periodo}`);
      setFile(null); setPreview(null);
      onIngestDone?.();
    } catch (err) { toast.error(err?.response?.data?.detail || "Error al cargar"); }
    finally { setLoading(false); }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <div className="dense-card p-5 lg:col-span-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><UploadCloud className="w-4 h-4 text-[#0033A0]" /><p className="label-eyebrow">Nuevo archivo</p></div>
          <Button variant="outline" size="sm" className="rounded-sm h-8 text-xs" onClick={() => tokenizedDownload("/api/uploads/template/estudiantes", "plantilla_estudiantes.xlsx")} data-testid="tpl-estudiantes-btn">
            <FileDown className="w-3.5 h-3.5 mr-1" /> Plantilla
          </Button>
        </div>
        <h3 className="font-display font-bold text-lg tracking-tight mb-5">Cargar caracterización</h3>

        <Label className="label-eyebrow mb-2 block">Periodo académico</Label>
        <Select value={periodo} onValueChange={setPeriodo}>
          <SelectTrigger className="mb-4 rounded-sm" data-testid="upload-periodo-select"><SelectValue placeholder="Seleccione periodo" /></SelectTrigger>
          <SelectContent>{periodos.map((p) => <SelectItem key={p.id} value={p.nombre}>{p.nombre}</SelectItem>)}</SelectContent>
        </Select>

        <Label className="label-eyebrow mb-2 block">Archivo Excel (.xlsx)</Label>
        <Input type="file" accept=".xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0])} className="rounded-sm mb-4" data-testid="upload-file-input" />

        <div className="flex gap-2">
          <Button variant="outline" onClick={doPreview} disabled={!file || loading} className="rounded-sm" data-testid="upload-preview-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><FileSpreadsheet className="w-4 h-4 mr-2" /> Previsualizar</>}
          </Button>
          <Button onClick={ingest} disabled={!preview || loading || preview?.missing_required?.length} className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white flex-1" data-testid="upload-ingest-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle2 className="w-4 h-4 mr-2" /> Confirmar carga</>}
          </Button>
        </div>
      </div>

      <div className="dense-card p-5 lg:col-span-7" data-testid="upload-preview-panel">
        <p className="label-eyebrow">Previsualización</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-4">Estructura del archivo</h3>
        {!preview && <div className="text-sm text-muted-foreground italic">Seleccione un archivo y previsualice para ver columnas, filas y muestras.</div>}
        {preview && (
          <div className="space-y-3">
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div><span className="label-eyebrow block">Archivo</span><b className="text-xs">{preview.filename}</b></div>
              <div><span className="label-eyebrow block">Filas</span><b>{preview.total_rows.toLocaleString("es-CO")}</b></div>
              <div><span className="label-eyebrow block">Columnas</span><b>{preview.total_columns}</b></div>
            </div>
            {preview.missing_required?.length > 0 && (
              <div className="border border-[#E3000F]/40 bg-[#E3000F]/5 p-3 rounded text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-[#E3000F] mt-0.5" />
                <div>
                  <b className="text-[#E3000F]">Faltan columnas obligatorias:</b>
                  <div>{preview.missing_required.join(", ")}</div>
                </div>
              </div>
            )}
            <div className="overflow-x-auto border border-border rounded">
              <Table>
                <TableHeader>
                  <TableRow>
                    {Object.keys(preview.preview[0] || {}).slice(0, 6).map((c) => (<TableHead key={c} className="text-[10px] uppercase tracking-wider">{c}</TableHead>))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {preview.preview.slice(0, 5).map((row, i) => (
                    <TableRow key={i}>
                      {Object.keys(preview.preview[0] || {}).slice(0, 6).map((c) => (<TableCell key={c} className="text-xs">{String(row[c] || "").slice(0, 40)}</TableCell>))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================
 * Carga simple (notas / docente-materia)
 * ============================================================ */
function SimpleUpload({ title, description, templateType, ingestPath, testidPrefix, onIngestDone }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const ingest = async () => {
    if (!file) return toast.error("Seleccione un archivo");
    setLoading(true); setResult(null);
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api.post(ingestPath, fd, { headers: { "Content-Type": "multipart/form-data" } });
      setResult(r.data);
      toast.success(`Cargados ${r.data.inserted} registros${r.data.docentes_creados ? ` · ${r.data.docentes_creados} docente(s) creados` : ""}${r.data.materias_creadas ? ` · ${r.data.materias_creadas} materia(s) creadas` : ""}`);
      onIngestDone?.();
    } catch (err) { toast.error(err?.response?.data?.detail || "Error al cargar"); }
    finally { setLoading(false); }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      <div className="dense-card p-5 lg:col-span-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><UploadCloud className="w-4 h-4 text-[#0033A0]" /><p className="label-eyebrow">Nuevo archivo</p></div>
          <Button variant="outline" size="sm" className="rounded-sm h-8 text-xs" onClick={() => tokenizedDownload(`/api/uploads/template/${templateType}`, `plantilla_${templateType}.xlsx`)} data-testid={`tpl-${testidPrefix}-btn`}>
            <FileDown className="w-3.5 h-3.5 mr-1" /> Plantilla
          </Button>
        </div>
        <h3 className="font-display font-bold text-lg tracking-tight">{title}</h3>
        <p className="text-xs text-muted-foreground mt-1 mb-5">{description}</p>

        <Label className="label-eyebrow mb-2 block">Archivo Excel (.xlsx)</Label>
        <Input type="file" accept=".xlsx,.xls" onChange={(e) => setFile(e.target.files?.[0])} className="rounded-sm mb-4" data-testid={`${testidPrefix}-file-input`} />

        <Button onClick={ingest} disabled={!file || loading} className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white w-full" data-testid={`${testidPrefix}-ingest-btn`}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><CheckCircle2 className="w-4 h-4 mr-2" /> Confirmar carga</>}
        </Button>
      </div>

      <div className="dense-card p-5 lg:col-span-7">
        <p className="label-eyebrow">Resultado de la carga</p>
        <h3 className="font-display font-bold text-lg tracking-tight mb-4">Resumen</h3>
        {!result && <div className="text-sm text-muted-foreground italic">Aún no se ha procesado ningún archivo en esta sesión.</div>}
        {result && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><span className="label-eyebrow block">Insertados</span><b className="kpi-num text-2xl text-emerald-700">{(result.inserted || 0).toLocaleString("es-CO")}</b></div>
              {result.duplicados !== undefined && (<div><span className="label-eyebrow block">Duplicados</span><b className="kpi-num text-2xl text-amber-700">{result.duplicados}</b></div>)}
              <div><span className="label-eyebrow block">Errores</span><b className="kpi-num text-2xl text-[#E3000F]">{result.errores || 0}</b></div>
              {result.docentes_creados !== undefined && (<div><span className="label-eyebrow block">Docentes creados</span><b className="kpi-num text-2xl">{result.docentes_creados}</b></div>)}
              {result.materias_creadas !== undefined && (<div><span className="label-eyebrow block">Materias creadas</span><b className="kpi-num text-2xl">{result.materias_creadas}</b></div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================
 * Descargas y backup
 * ============================================================ */
function DownloadsTab() {
  const { filters } = useFilters();
  const filterQs = buildQuery(filters);
  const hasFilters = Object.keys(filters || {}).length > 0;
  const ts = new Date().toISOString().slice(0, 10);
  const [stats, setStats] = useState({});

  useEffect(() => {
    api.get("/uploads/backup-stats").then((r) => setStats(r.data || {})).catch(() => {});
  }, []);

  const backups = [
    { key: "students", label: "Estudiantes completos", desc: "16.4k estudiantes con caracterización socio-demográfica, académica y territorial." },
    { key: "grupos", label: "Grupos activos", desc: "1.3k grupos periodo 2026-2 con docente, asignatura, día/hora y programa." },
    { key: "matriculas", label: "Matrículas", desc: "92k cédula × grupo × periodo, con estado y correos del estudiante." },
    { key: "historico_notas", label: "Notas históricas", desc: "169k notas 2025-2 y 2026-1 con área, docente, aprobada, créditos y estado." },
    { key: "docentes", label: "Docentes", desc: "399 docentes con documento, correo institucional, correo personal, IDDOC." },
    { key: "docente_materia", label: "Docente-materia", desc: "737 relaciones únicas docente × asignatura × periodo × grupo." },
    { key: "programas", label: "Catálogo programas SNIES", desc: "59 programas con código SNIES, facultad, nivel y modalidad." },
    { key: "facultades", label: "Facultades", desc: "5 facultades institucionales." },
  ];

  const downloads = [
    {
      group: "Plantillas vacías",
      items: [
        { key: "tpl-est", label: "Plantilla estudiantes (.xlsx)", path: "/api/uploads/template/estudiantes", file: "plantilla_estudiantes.xlsx", desc: "Estructura para carga masiva del Excel maestro" },
        { key: "tpl-not", label: "Plantilla notas históricas (.xlsx)", path: "/api/uploads/template/notas", file: "plantilla_notas.xlsx", desc: "Cédula × Periodo × Materia × Docente × Nota" },
        { key: "tpl-dm", label: "Plantilla docente–materia (.xlsx)", path: "/api/uploads/template/docente_materia", file: "plantilla_docente_materia.xlsx", desc: "Asignación masiva de docentes a materias por periodo" },
      ],
    },
    {
      group: "Datos actuales (respeta filtros globales activos)",
      items: [
        { key: "exp-est-xlsx", label: "Base de estudiantes (.xlsx)", path: `/api/exports/students?fmt=xlsx&${filterQs}`, file: `estudiantes_${ts}.xlsx`, desc: hasFilters ? "Solo registros filtrados" : "Base completa (12.927 registros)" },
        { key: "exp-est-csv", label: "Base de estudiantes (.csv)", path: `/api/exports/students?fmt=csv&${filterQs}`, file: `estudiantes_${ts}.csv`, desc: "Versión CSV ligera" },
        { key: "exp-not", label: "Histórico de notas (.xlsx)", path: `/api/exports/notas?fmt=xlsx&${filterQs}`, file: `notas_${ts}.xlsx`, desc: "Notas registradas vía cargas" },
        { key: "exp-dm", label: "Catálogo docente–materia (.xlsx)", path: "/api/exports/docente-materia?fmt=xlsx", file: `docente_materia_${ts}.xlsx`, desc: "Relación actual de asignaciones" },
        { key: "exp-divi", label: "Catálogo DIVIPOLA (.xlsx)", path: "/api/exports/divipola?fmt=xlsx", file: `divipola_${ts}.xlsx`, desc: "Municipios + ciudades internacionales" },
      ],
    },
  ];

  return (
    <div className="space-y-4">
      {/* Backup completo de la BD por colección */}
      <div className="dense-card p-5">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="label-eyebrow">Backup completo</p>
            <h3 className="font-display font-bold text-lg tracking-tight">Descargar base de datos por colección</h3>
            <p className="text-[11px] text-muted-foreground mt-1">Exporta la colección completa como Excel (sin filtros aplicados). Útil para respaldar la BD antes de una recarga.</p>
          </div>
          <Badge variant="outline" className="rounded-sm text-[10px]">{Object.values(stats).reduce((a, b) => a + (b || 0), 0).toLocaleString("es-CO")} registros totales</Badge>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {backups.map((b) => (
            <button
              key={b.key}
              onClick={() => tokenizedDownload(`/api/uploads/backup/${b.key}`, `${b.key}_${ts}.xlsx`)}
              data-testid={`backup-${b.key}`}
              className="text-left p-4 border border-border rounded hover:border-[#0033A0] hover:bg-[#0033A0]/5 transition-soft group"
            >
              <div className="flex items-center justify-between mb-2">
                <Database className="w-4 h-4 text-[#0033A0] group-hover:scale-110 transition-transform" />
                <Badge variant="outline" className="text-[9px] uppercase tracking-widest rounded-sm">{(stats[b.key] || 0).toLocaleString("es-CO")}</Badge>
              </div>
              <p className="text-xs font-semibold leading-tight mb-1">{b.label}</p>
              <p className="text-[10px] text-muted-foreground leading-snug">{b.desc}</p>
            </button>
          ))}
        </div>
      </div>

      {hasFilters && (
        <div className="dense-card p-4 border-[#0033A0]/30 bg-[#0033A0]/5">
          <p className="text-xs flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-[#0033A0]" />
            <b className="text-[#0033A0]">Hay {Object.keys(filters).length} filtro(s) activo(s):</b>
            <span className="text-muted-foreground">{Object.entries(filters).map(([k, v]) => `${k}=${v}`).join(", ")}</span>
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">Las descargas de "Datos actuales" se generarán SOLO con esos registros. Para descargar todo, limpie los filtros desde la barra superior.</p>
        </div>
      )}

      {downloads.map((grp) => (
        <div key={grp.group} className="dense-card p-5">
          <p className="label-eyebrow">{grp.group}</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-4">{grp.items.length} elemento(s)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {grp.items.map((it) => (
              <button
                key={it.key}
                onClick={() => tokenizedDownload(it.path, it.file)}
                data-testid={`download-${it.key}`}
                className="text-left p-4 border border-border rounded hover:border-[#0033A0] hover:bg-[#0033A0]/5 transition-soft group"
              >
                <div className="flex items-center justify-between mb-2">
                  <Download className="w-4 h-4 text-[#0033A0] group-hover:scale-110 transition-transform" />
                  <Badge variant="outline" className="text-[9px] uppercase tracking-widest rounded-sm">{it.path.includes("template") ? "Plantilla" : "Backup"}</Badge>
                </div>
                <p className="text-xs font-semibold leading-tight mb-1">{it.label}</p>
                <p className="text-[10px] text-muted-foreground leading-snug">{it.desc}</p>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}


// ============================================================================
// FULL REFRESH TAB · Recarga completa de la BD desde archivos maestros
// ============================================================================
function FullRefreshTab({ onDone }) {
  const [files, setFiles] = useState({});
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [confirmed, setConfirmed] = useState(false);

  const slots = [
    { key: "carac", label: "Caracterización estudiantes", filename: "carac.xlsx", desc: "16.4k estudiantes con datos socio-demográficos, académicos y territoriales.", accept: ".xlsx" },
    { key: "asignacion", label: "Asignación de grupos", filename: "estdoc.csv", desc: "Grupos 2026-2 con docente, asignatura, día/hora, matriculados y correos.", accept: ".csv" },
    { key: "notas_25_2", label: "Notas 2025-2", filename: "notas_25_2.xlsx", desc: "Notas históricas cerradas del periodo 2025-2 (84.8k registros).", accept: ".xlsx" },
    { key: "notas_26_1", label: "Notas 2026-1", filename: "notas_26_2.xlsx", desc: "Notas históricas cerradas del periodo 2026-1 (84.5k registros).", accept: ".xlsx" },
    { key: "programas", label: "Catálogo de programas SNIES", filename: "progs.xlsx", desc: "5 facultades y 59 programas con código SNIES, nivel y modalidad.", accept: ".xlsx" },
  ];

  const upload = async () => {
    if (!confirmed) {
      toast.error("Debes confirmar el borrado y recarga de datos");
      return;
    }
    const anyFile = Object.values(files).some(Boolean);
    if (!anyFile) {
      toast.error("Selecciona al menos un archivo");
      return;
    }
    setRunning(true);
    setResult(null);
    const fd = new FormData();
    Object.entries(files).forEach(([k, f]) => f && fd.append(k, f));
    try {
      const r = await api.post("/uploads/full-refresh", fd, { timeout: 600000 });
      setResult(r.data);
      toast.success("Recarga completa exitosa");
      onDone && onDone();
    } catch (e) {
      toast.error(`Error en recarga: ${e.response?.data?.detail?.slice?.(0, 200) || e.message}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="dense-card p-5 border-2 border-amber-200 bg-amber-50/50">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <p className="font-display font-bold text-amber-900">Recarga completa de la base de datos</p>
            <p className="text-xs text-amber-800 leading-relaxed">
              Este flujo <b>reemplaza los archivos maestros</b> en <code className="text-[10px] bg-amber-100 px-1 rounded">/app/uploads_user/</code> y ejecuta <code className="text-[10px] bg-amber-100 px-1 rounded">load_real_data.py</code>,
              que <b>WIPE + REBUILD</b> las colecciones <b>students, grupos, matriculas, historico_notas, docente_materia</b> y los <b>docentes</b> auto-creados.
              Los superadmin y el docente demo se preservan. Solo debes subir los archivos que <b>cambiaron</b>: los demás se conservan del snapshot anterior.
              Este proceso puede tardar <b>60-120 segundos</b>.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {slots.map((s) => (
          <div key={s.key} className="dense-card p-4">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="text-xs font-semibold">{s.label}</p>
                <p className="text-[10px] text-muted-foreground">{s.filename}</p>
              </div>
              {files[s.key] && <Badge variant="outline" className="text-[9px] text-emerald-700 border-emerald-700/40 rounded-sm">Cargado</Badge>}
            </div>
            <p className="text-[10px] text-muted-foreground mb-3">{s.desc}</p>
            <Input
              type="file"
              accept={s.accept}
              onChange={(e) => setFiles((prev) => ({ ...prev, [s.key]: e.target.files?.[0] }))}
              className="rounded-sm text-xs"
              data-testid={`fullref-${s.key}`}
            />
          </div>
        ))}
      </div>

      <div className="dense-card p-4 flex items-start justify-between gap-4">
        <label className="flex items-start gap-2 text-xs cursor-pointer flex-1">
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-0.5" data-testid="fullref-confirm" />
          <span>
            Entiendo que este proceso <b>elimina y recrea</b> todos los estudiantes, grupos, matrículas, notas y docentes.
            Los superadmins y el docente demo se conservan.
          </span>
        </label>
        <Button onClick={upload} disabled={running || !confirmed} className="rounded-sm bg-[#0033A0] text-white" data-testid="fullref-run">
          {running ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" />Recargando…</> : <><RotateCcw className="w-4 h-4 mr-2" />Ejecutar recarga</>}
        </Button>
      </div>

      {result && (
        <div className="dense-card p-5 border-emerald-200 bg-emerald-50/40">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-700" />
            <p className="font-display font-bold text-emerald-900">Recarga completada</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3 text-xs mb-4">
            {Object.entries(result.stats || {}).map(([k, v]) => (
              <div key={k}>
                <p className="label-eyebrow">{k}</p>
                <p className="kpi-num text-lg">{v.toLocaleString("es-CO")}</p>
              </div>
            ))}
          </div>
          {result.stdout_tail && (
            <details className="text-[10px] mt-3">
              <summary className="cursor-pointer text-muted-foreground">Ver salida del script</summary>
              <pre className="bg-slate-900 text-slate-100 p-3 rounded-sm mt-2 overflow-x-auto text-[10px]">{result.stdout_tail.join("\n")}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
