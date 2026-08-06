import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Users, Eye, GraduationCap, Search } from "lucide-react";

export default function Grupos() {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [programa, setPrograma] = useState("all");
  const [periodo, setPeriodo] = useState("all");
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [opts, setOpts] = useState({ programas: [], periodos: [] });

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
    api.get(`/admin/grupos?${params.toString()}`)
      .then((r) => { setItems(r.data.items || []); setTotal(r.data.total || 0); })
      .finally(() => setLoading(false));
  }, [q, programa, periodo]);

  const openDetail = async (codigo) => {
    setDetail({ loading: true });
    const r = await api.get(`/admin/grupos/${encodeURIComponent(codigo)}`);
    setDetail(r.data);
  };

  return (
    <div className="space-y-6" data-testid="grupos-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Catálogo académico</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Grupos</h1>
        <p className="text-sm text-muted-foreground mt-2">
          {total.toLocaleString("es-CO")} grupos activos con docente, asignatura y estudiantes matriculados.
        </p>
      </header>

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
                  <TableHead className="text-[10px] uppercase tracking-wider">Código</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Asignatura</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Docente</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider">Periodo</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider text-right">Matriculados</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom. histórico</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-wider"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((g) => (
                  <TableRow key={g.codigo_grupo} className="hover:bg-muted/40 cursor-pointer" onClick={() => openDetail(g.codigo_grupo)}>
                    <TableCell className="text-[11px] mono">{g.codigo_grupo}</TableCell>
                    <TableCell className="text-xs font-medium">{g.asignatura_nombre?.slice(0, 40)}</TableCell>
                    <TableCell className="text-[11px] text-muted-foreground">{g.docente_nombre?.slice(0, 30)}</TableCell>
                    <TableCell className="text-[11px]">{g.programa?.slice(0, 35)}</TableCell>
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
                    <TableCell>
                      <Button size="sm" variant="ghost" className="h-7 px-2" onClick={(e) => { e.stopPropagation(); openDetail(g.codigo_grupo); }} data-testid={`grupo-detail-${g.codigo_grupo}`}>
                        <Eye className="w-3.5 h-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {items.length === 0 && (
                  <TableRow><TableCell colSpan={8} className="text-center text-xs text-muted-foreground py-6">Sin grupos con esos filtros</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Detalle modal */}
      <Dialog open={!!detail} onOpenChange={(v) => !v && setDetail(null)}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-y-auto" data-testid="grupo-detail-dialog">
          <DialogHeader>
            <DialogTitle className="font-display tracking-tight">
              {detail?.grupo ? `${detail.grupo.asignatura_nombre} · ${detail.grupo.codigo_grupo}` : "Cargando…"}
            </DialogTitle>
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
                <p className="label-eyebrow mb-2">Estudiantes matriculados ({detail.estudiantes?.length || 0})</p>
                <div className="max-h-96 overflow-y-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Cédula</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Nombre</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Promedio</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Estado</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Flags</TableHead>
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
                            <div className="flex gap-1 flex-wrap">
                              {s.grupo_vulnerable && <Badge className="text-[8px] uppercase rounded-sm h-4 px-1 bg-amber-500/15 text-amber-700">Vuln</Badge>}
                              {s.victima_conflicto && <Badge className="text-[8px] uppercase rounded-sm h-4 px-1 bg-[#E3000F]/10 text-[#E3000F]">Víctima</Badge>}
                              {s.tipo_ubicacion === "Rural" && <Badge className="text-[8px] uppercase rounded-sm h-4 px-1 bg-emerald-500/15 text-emerald-700">Rural</Badge>}
                            </div>
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
