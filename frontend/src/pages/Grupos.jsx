import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Eye, Search, Filter, X, Download, FileText, User, Info } from "lucide-react";
import { useFilters } from "@/pages/AppLayout";
import { useAuth } from "@/context/AuthContext";

export default function Grupos() {
  const { filters, setFilter, opts: globalOpts } = useFilters();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [programa, setPrograma] = useState("all");
  const [periodo, setPeriodo] = useState("all");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [opts, setOpts] = useState({ programas: [], periodos: [] });

  const canDownload = user?.role === "superadmin" || user?.role === "direccion" || user?.download_enabled === true;

  useEffect(() => {
    api.get("/dashboards/filters").then((r) => setOpts({
      programas: r.data.programas || [],
      periodos: r.data.periodos || [],
    }));
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q) params.append("q", q);
    if (programa !== "all") params.append("programa", programa);
    if (periodo !== "all") params.append("periodo", periodo);
    // Sync with global filters (docente_id and codigo_grupo from filter chips)
    if (filters.docente_id) params.append("docente_id", filters.docente_id);
    if (filters.codigo_grupo) params.append("codigo_grupo", filters.codigo_grupo);
    api.get(`/admin/grupos?${params.toString()}`)
      .then((r) => {
        setItems(r.data.items || []);
        setTotal(r.data.total || 0);
      })
      .finally(() => setLoading(false));
  }, [q, programa, periodo, filters.docente_id, filters.codigo_grupo]);

  const openDetail = async (codigo) => {
    setDetail({ loading: true });
    const r = await api.get(`/admin/grupos/${encodeURIComponent(codigo)}`);
    setDetail(r.data);
  };

  const descargarGrupo = async (codigo, fmt = "xlsx") => {
    if (!canDownload) {
      toast.error("No tiene permiso de descarga. Contacte al administrador.");
      return;
    }
    try {
      const url = `/api/exports/grupo/${encodeURIComponent(codigo)}?fmt=${fmt}`;
      const token = localStorage.getItem("iud_token");
      const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
      if (!resp.ok) throw new Error(resp.status === 403 ? "Sin permiso" : `Error ${resp.status}`);
      const blob = await resp.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `grupo_${codigo}.${fmt}`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success("Descarga completada");
    } catch (e) {
      toast.error("Error al descargar: " + e.message);
    }
  };

  const docenteSel = (globalOpts.docentes || []).find((d) => d.id === filters.docente_id);
  const hasGlobalFilter = !!(filters.docente_id || filters.codigo_grupo);

  return (
    <div className="space-y-6" data-testid="grupos-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Catálogo académico</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Grupos</h1>
        <p className="text-sm text-muted-foreground mt-2">
          {total.toLocaleString("es-CO")} grupos activos con docente, asignatura y estudiantes matriculados.
        </p>
      </header>

      {/* Chip de filtro global activo */}
      {hasGlobalFilter && (
        <div className="dense-card p-3 border-l-4 border-l-[#0033A0] bg-[#0033A0]/5 flex items-center justify-between gap-3" data-testid="global-filter-banner">
          <div className="flex items-center gap-2 text-xs">
            <Filter className="w-4 h-4 text-[#0033A0]" />
            <span className="text-[#0033A0] font-semibold">Filtro global activo:</span>
            {docenteSel && (
              <Badge variant="outline" className="rounded-sm bg-white text-[#0033A0] border-[#0033A0]/40">
                <User className="w-3 h-3 mr-1" /> {docenteSel.nombre}
              </Badge>
            )}
            {filters.codigo_grupo && (
              <Badge variant="outline" className="rounded-sm bg-white text-[#0033A0] border-[#0033A0]/40 font-mono text-[10px]">
                {filters.codigo_grupo}
              </Badge>
            )}
            <span className="text-muted-foreground italic">Mostrando solo grupos que coinciden con el filtro global.</span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={() => { setFilter("docente_id", null); setFilter("codigo_grupo", null); }}
            data-testid="clear-global-filter-grupos"
          >
            <X className="w-3 h-3 mr-1" /> Limpiar filtro global
          </Button>
        </div>
      )}

      <div className="dense-card p-5">
        <div className="flex flex-wrap gap-3 items-end mb-4">
          <div className="flex-1 min-w-64">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Buscar por código, asignatura, docente o programa…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="rounded-sm pl-9"
                data-testid="grupos-search"
              />
            </div>
          </div>
          <Select value={programa} onValueChange={setPrograma}>
            <SelectTrigger className="rounded-sm w-64" data-testid="grupos-programa"><SelectValue placeholder="Programa" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los programas</SelectItem>
              {opts.programas.map((p) => <SelectItem key={p} value={p}>{p.length > 40 ? p.slice(0, 38) + "…" : p}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger className="rounded-sm w-36" data-testid="grupos-periodo"><SelectValue placeholder="Periodo" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos</SelectItem>
              {opts.periodos.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="text-xs text-muted-foreground">
            Mostrando <b>{items.length.toLocaleString("es-CO")}</b> de <b>{total.toLocaleString("es-CO")}</b>
          </div>
        </div>

        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[10px] uppercase tracking-wider">Código grupo</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Cód. asig.</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Asignatura</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Docente</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Día</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Hora</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Periodo</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider text-right">Est.</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom.</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider text-right">Acciones</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((g) => (
                  <TableRow key={g.codigo_grupo} className="hover:bg-muted/40 cursor-pointer" onClick={() => openDetail(g.codigo_grupo)}>
                    <TableCell className="text-[10px] mono">{g.codigo_grupo}</TableCell>
                    <TableCell className="text-[10px] mono text-muted-foreground">{g.asignatura_codigo || "—"}</TableCell>
                    <TableCell className="text-xs font-medium" title={g.asignatura_nombre}>{g.asignatura_nombre?.slice(0, 34)}{g.asignatura_nombre?.length > 34 && "…"}</TableCell>
                    <TableCell className="text-[11px]" title={`${g.docente_nombre}\n${g.docente_email || ""}\nCédula: ${g.docente_cedula || "—"}`}>
                      <div className="truncate max-w-[180px]">{g.docente_nombre || "—"}</div>
                      <div className="text-[9px] text-muted-foreground truncate max-w-[180px]">{g.docente_email || "—"}</div>
                    </TableCell>
                    <TableCell className="text-[11px]">{g.programa?.slice(0, 30) || "—"}</TableCell>
                    <TableCell className="text-[10px]">{g.dia || "—"}</TableCell>
                    <TableCell className="text-[10px]">{g.hora || "—"}</TableCell>
                    <TableCell><Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">{g.periodo}</Badge></TableCell>
                    <TableCell className="text-right">
                      <span className="kpi-num text-sm">{(g.total_estudiantes || 0).toLocaleString("es-CO")}</span>
                    </TableCell>
                    <TableCell className="text-right">
                      {g.promedio_historico !== null && g.promedio_historico !== undefined ? (
                        <span className={`kpi-num text-sm ${g.promedio_historico < 3 ? "text-[#E3000F]" : g.promedio_historico >= 4 ? "text-emerald-700" : ""}`}>
                          {g.promedio_historico.toFixed(2)}
                        </span>
                      ) : <span className="text-muted-foreground text-xs">—</span>}
                    </TableCell>
                    <TableCell className="text-right whitespace-nowrap">
                      <Button size="sm" variant="ghost" className="h-7 px-2" onClick={(e) => { e.stopPropagation(); openDetail(g.codigo_grupo); }} data-testid={`grupo-detail-${g.codigo_grupo}`} title="Ver detalle">
                        <Eye className="w-3.5 h-3.5 text-[#0033A0]" />
                      </Button>
                      {canDownload && (
                        <Button size="sm" variant="ghost" className="h-7 px-2" onClick={(e) => { e.stopPropagation(); descargarGrupo(g.codigo_grupo); }} data-testid={`grupo-download-${g.codigo_grupo}`} title="Descargar Excel del grupo (Grupo · Estudiantes · Notas)">
                          <Download className="w-3.5 h-3.5 text-[#0033A0]" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {items.length === 0 && (
                  <TableRow><TableCell colSpan={11} className="text-center text-xs text-muted-foreground py-6">
                    {hasGlobalFilter
                      ? "El filtro global no coincide con ningún grupo. Prueba limpiando el filtro."
                      : "Sin grupos con esos filtros"}
                  </TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Detalle modal */}
      <Dialog open={!!detail} onOpenChange={(v) => !v && setDetail(null)}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="grupo-detail-dialog">
          <DialogHeader>
            <div className="flex items-start justify-between gap-4 pr-6">
              <DialogTitle className="font-display tracking-tight flex-1">
                {detail?.grupo ? `${detail.grupo.asignatura_nombre} · ${detail.grupo.codigo_grupo}` : "Cargando…"}
              </DialogTitle>
              {detail?.grupo && canDownload && (
                <div className="flex gap-2 flex-shrink-0">
                  <Button size="sm" onClick={() => descargarGrupo(detail.grupo.codigo_grupo, "xlsx")} className="rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white text-xs h-8" data-testid="detail-download-xlsx">
                    <Download className="w-3.5 h-3.5 mr-1" /> Excel detallado
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => descargarGrupo(detail.grupo.codigo_grupo, "csv")} className="rounded-sm text-xs h-8" data-testid="detail-download-csv">
                    <FileText className="w-3.5 h-3.5 mr-1" /> CSV
                  </Button>
                </div>
              )}
            </div>
          </DialogHeader>
          {!detail || detail.loading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <Field label="Código grupo" value={detail.grupo.codigo_grupo} mono />
                <Field label="Tipo grupo" value={detail.grupo.periodicidad} />
                <Field label="Periodo" value={detail.grupo.periodo} />
                <Field label="Bloque" value={detail.grupo.bloque} />
                <Field label="Docente" value={detail.grupo.docente_nombre} />
                <Field label="Email docente" value={detail.grupo.docente_email} />
                <Field label="Cédula docente" value={detail.grupo.docente_cedula} mono />
                <Field label="Día / Hora" value={`${detail.grupo.dia || "—"} · ${detail.grupo.hora || "—"}`} />
                <Field label="Programa" value={detail.grupo.programa} full />
                <Field label="Facultad" value={detail.grupo.facultad} full />
                <Field label="Código asignatura" value={detail.grupo.asignatura_codigo} mono />
                <Field label="Estudiantes matriculados" value={detail.total_estudiantes} highlight />
              </div>

              {detail.notas_por_periodo?.length > 0 && (
                <div className="border-t border-border pt-4">
                  <p className="label-eyebrow mb-2">Promedios históricos del docente en esta asignatura</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {detail.notas_por_periodo.map((p) => (
                      <div key={p.periodo} className="border border-border rounded p-3">
                        <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{p.periodo}</div>
                        <div className={`kpi-num text-2xl mt-1 ${p.promedio < 3 ? "text-[#E3000F]" : "text-emerald-700"}`}>{p.promedio}</div>
                        <div className="text-[10px] text-muted-foreground">{p.total} notas · {p.tasa}% aprobación</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="border-t border-border pt-4">
                <div className="flex items-center justify-between mb-2">
                  <p className="label-eyebrow">Estudiantes matriculados ({detail.estudiantes?.length || 0})</p>
                  <p className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Info className="w-3 h-3" />
                    Pase el cursor sobre cada flag para ver el detalle
                  </p>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Cédula</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Nombre</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom.</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Estado</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Flags de vulnerabilidad</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(detail.estudiantes || []).map((s) => (
                        <TableRow key={s.cedula} className="hover:bg-muted/40">
                          <TableCell className="text-[11px] mono">{s.cedula}</TableCell>
                          <TableCell className="text-xs">{s.nombre} {s.apellidos}</TableCell>
                          <TableCell className="text-[10px] text-muted-foreground">{s.programa?.slice(0, 30)}</TableCell>
                          <TableCell className="text-right">
                            <span className={`kpi-num text-sm ${s.promedio < 3 ? "text-[#E3000F]" : s.promedio >= 4.5 ? "text-emerald-700" : ""}`}>
                              {(s.promedio || 0).toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">{s.estado_matricula}</Badge>
                          </TableCell>
                          <TableCell>
                            <VulnFlags s={s} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function VulnFlags({ s }) {
  const flags = [];

  if (s.grupo_vulnerable) {
    flags.push({
      label: s.tipo_grupo_vulnerable || "Vulnerable",
      short: (s.tipo_grupo_vulnerable || "Vuln").slice(0, 18),
      color: "bg-amber-500/15 text-amber-800 border-amber-500/30",
      tooltip: `Grupo vulnerable: ${s.tipo_grupo_vulnerable || "No especificado"}`,
    });
  }
  if (s.victima_conflicto) {
    flags.push({
      label: "Víctima",
      short: "Víctima",
      color: "bg-[#E3000F]/10 text-[#E3000F] border-[#E3000F]/30",
      tooltip: "Víctima del conflicto armado",
    });
  }
  if (s.discapacidad_flag) {
    const tipo = (s.discapacidad_tipo && s.discapacidad_tipo !== "Ninguno") ? s.discapacidad_tipo : "Discapacidad";
    flags.push({
      label: tipo,
      short: tipo.length > 18 ? tipo.slice(0, 16) + "…" : tipo,
      color: "bg-purple-500/15 text-purple-800 border-purple-500/30",
      tooltip: `Discapacidad: ${tipo}`,
    });
  }
  if (s.sisben_tiene && s.sisben_nivel) {
    // SISBEN nivel A/B highlight
    const isCritical = /^[AB]/i.test(s.sisben_nivel || "");
    flags.push({
      label: `SISBEN ${s.sisben_nivel}`,
      short: `SISB ${s.sisben_nivel}`,
      color: isCritical ? "bg-blue-500/15 text-blue-800 border-blue-500/30" : "bg-blue-500/10 text-blue-700 border-blue-500/20",
      tooltip: `SISBEN nivel ${s.sisben_nivel}${s.grupo_sisben ? ` (${s.grupo_sisben})` : ""}`,
    });
  }
  if (s.tipo_ubicacion === "Rural" || s.tipo_ubicacion === "Semirural") {
    flags.push({
      label: s.tipo_ubicacion,
      short: s.tipo_ubicacion,
      color: "bg-emerald-500/15 text-emerald-800 border-emerald-500/30",
      tooltip: `Ubicación ${s.tipo_ubicacion.toLowerCase()}`,
    });
  }
  if (s.etnia && s.etnia !== "Ninguno" && s.etnia !== "No Aplica") {
    flags.push({
      label: s.etnia,
      short: s.etnia.length > 14 ? s.etnia.slice(0, 12) + "…" : s.etnia,
      color: "bg-orange-500/15 text-orange-800 border-orange-500/30",
      tooltip: `Etnia: ${s.etnia}${s.grupo_etnia && s.grupo_etnia !== "Ningún Grupo Étnico" ? ` (${s.grupo_etnia})` : ""}`,
    });
  }

  if (flags.length === 0) {
    return <span className="text-[10px] text-muted-foreground italic">Sin flags</span>;
  }

  return (
    <div className="flex gap-1 flex-wrap max-w-[280px]">
      {flags.map((f, i) => (
        <Badge
          key={i}
          variant="outline"
          className={`text-[9px] rounded-sm h-4 px-1.5 border ${f.color} cursor-help`}
          title={f.tooltip}
        >
          {f.short}
        </Badge>
      ))}
    </div>
  );
}

function Field({ label, value, mono, highlight, full }) {
  return (
    <div className={full ? "col-span-2" : ""}>
      <div className="label-eyebrow">{label}</div>
      <div className={`mt-0.5 ${mono ? "font-mono text-xs" : "text-sm"} ${highlight ? "kpi-num text-2xl text-[#0033A0]" : ""}`}>
        {value || <span className="text-muted-foreground italic">—</span>}
      </div>
    </div>
  );
}
