import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { UploadCloud, FileSpreadsheet, Loader2, AlertTriangle, RotateCcw, CheckCircle2 } from "lucide-react";

export default function Upload() {
  const [file, setFile] = useState(null);
  const [periodo, setPeriodo] = useState("");
  const [periodos, setPeriodos] = useState([]);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploads, setUploads] = useState([]);

  const loadAll = () => {
    api.get("/admin/periodos").then((r) => setPeriodos(r.data || []));
    api.get("/uploads/").then((r) => setUploads(r.data || []));
  };
  useEffect(() => { loadAll(); }, []);

  const doPreview = async () => {
    if (!file) return toast.error("Seleccione un archivo");
    setLoading(true);
    setPreview(null);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const r = await api.post("/uploads/preview", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setPreview(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error de previsualización");
    } finally {
      setLoading(false);
    }
  };

  const ingest = async () => {
    if (!periodo) return toast.error("Seleccione un periodo");
    if (preview?.missing_required?.length) return toast.error("Faltan columnas obligatorias");
    setLoading(true);
    const fd = new FormData();
    fd.append("file", file);
    fd.append("periodo", periodo);
    try {
      const r = await api.post("/uploads/ingest", fd, { headers: { "Content-Type": "multipart/form-data" } });
      toast.success(`Cargados ${r.data.inserted} estudiantes en ${r.data.periodo}`);
      setFile(null); setPreview(null);
      loadAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error al cargar");
    } finally {
      setLoading(false);
    }
  };

  const rollback = async (id) => {
    if (!window.confirm("¿Revertir esta carga? Se eliminarán los registros asociados.")) return;
    try {
      await api.post(`/uploads/rollback/${id}`);
      toast.success("Carga revertida");
      loadAll();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error");
    }
  };

  return (
    <div className="space-y-6" data-testid="upload-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Cargas Excel</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Ingesta de archivos</h1>
        <p className="text-sm text-muted-foreground mt-2">Cargue el archivo de caracterización sociodemográfica institucional. La ingesta valida estructura y versiona por periodo.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-5 lg:col-span-5">
          <div className="flex items-center gap-2 mb-3">
            <UploadCloud className="w-4 h-4 text-[#0033A0]" />
            <p className="label-eyebrow">Nuevo archivo</p>
          </div>
          <h3 className="font-display font-bold text-lg tracking-tight mb-5">Cargar caracterización</h3>

          <Label className="label-eyebrow mb-2 block">Periodo académico</Label>
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="mb-4 rounded-sm" data-testid="upload-periodo-select">
              <SelectValue placeholder="Seleccione periodo" />
            </SelectTrigger>
            <SelectContent>
              {periodos.map((p) => <SelectItem key={p.id} value={p.nombre}>{p.nombre}</SelectItem>)}
            </SelectContent>
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
          {!preview && <div className="text-sm text-muted-foreground italic">Seleccione un archivo para previsualizar.</div>}
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
                      {Object.keys(preview.preview[0] || {}).slice(0, 6).map((c) => (
                        <TableHead key={c} className="text-[10px] uppercase tracking-wider">{c}</TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preview.preview.slice(0, 5).map((row, i) => (
                      <TableRow key={i}>
                        {Object.keys(preview.preview[0] || {}).slice(0, 6).map((c) => (
                          <TableCell key={c} className="text-xs">{String(row[c] || "").slice(0, 40)}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}
        </div>

        <div className="dense-card p-5 lg:col-span-12">
          <p className="label-eyebrow">Histórico</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-4">Cargas realizadas</h3>
          <Table>
            <TableHeader>
              <TableRow>
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
                  <TableCell className="text-xs font-medium">{u.filename}</TableCell>
                  <TableCell><span className="mono text-xs">{u.periodo}</span></TableCell>
                  <TableCell className="text-right kpi-num text-sm">{u.inserted.toLocaleString("es-CO")}</TableCell>
                  <TableCell className="text-right text-xs text-[#E3000F]">{u.errores}</TableCell>
                  <TableCell className="text-xs">{u.uploaded_by}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{new Date(u.created_at).toLocaleString("es-CO")}</TableCell>
                  <TableCell>
                    {!u.rolled_back ? (
                      <Button size="sm" variant="ghost" onClick={() => rollback(u.id)} data-testid={`upload-rollback-${u.id}`}>
                        <RotateCcw className="w-3 h-3 mr-1" /> Revertir
                      </Button>
                    ) : <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Revertida</span>}
                  </TableCell>
                </TableRow>
              ))}
              {uploads.length === 0 && (<TableRow><TableCell colSpan={7} className="text-center text-xs text-muted-foreground py-6">Sin cargas registradas</TableCell></TableRow>)}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
