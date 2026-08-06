import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend, LineChart, Line
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LTooltip } from "react-leaflet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertTriangle, BookOpen, Users, TrendingUp, Heart, Accessibility, GraduationCap, MapPin, ArrowUpRight, ArrowDownRight, Minus, History } from "lucide-react";

const PALETTE = ["#0033A0", "#0052FF", "#FFCD00", "#E3000F", "#059669", "#8B5CF6"];

function KPI({ label, value, sub, icon: Icon, accent }) {
  return (
    <div className="dense-card p-5" data-testid={`docente-kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <div className="flex items-start justify-between mb-3">
        <span className="label-eyebrow">{label}</span>
        <div className={`h-7 w-7 grid place-items-center rounded ${accent}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
      </div>
      <div className="kpi-num text-3xl md:text-4xl">{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground mt-1.5 tracking-wide">{sub}</div>}
    </div>
  );
}

export default function Docente() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [students, setStudents] = useState([]);
  const [enRiesgo, setEnRiesgo] = useState([]);
  const [comparativa, setComparativa] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtroGrupo, setFiltroGrupo] = useState("all");
  const [onlyRiesgo, setOnlyRiesgo] = useState(false);
  const [historico, setHistorico] = useState(null);
  const [openHistorico, setOpenHistorico] = useState(false);

  useEffect(() => {
    setLoading(true);
    const q = filtroGrupo !== "all" ? `?codigo_grupo=${filtroGrupo}` : "";
    api.get(`/dashboards/docente/me${q}`).then((r) => setData(r.data)).finally(() => setLoading(false));
    api.get(`/dashboards/docente/en-riesgo${q}`).then((r) => setEnRiesgo(r.data.items || []));
  }, [filtroGrupo]);

  useEffect(() => {
    api.get("/dashboards/docente/grupos-comparativa").then((r) => setComparativa(r.data.grupos || []));
  }, []);

  useEffect(() => {
    const q = new URLSearchParams();
    if (filtroGrupo !== "all") q.append("codigo_grupo", filtroGrupo);
    if (onlyRiesgo) q.append("riesgo", "true");
    api.get(`/dashboards/docente/students?${q.toString()}`).then((r) => setStudents(r.data.students || []));
  }, [filtroGrupo, onlyRiesgo]);

  const openHist = async (cedula) => {
    setOpenHistorico(true); setHistorico(null);
    const r = await api.get(`/dashboards/docente/estudiante/${cedula}/historico`);
    setHistorico(r.data);
  };

  const fmt = (n) => (n || 0).toLocaleString("es-CO");
  const k = data?.kpis || {};
  const grupos = data?.grupos || [];

  const munis = data?.municipios || [];
  const maxN = Math.max(1, ...munis.map((m) => m.n));
  const colorFor = (n) => {
    const r = n / maxN;
    if (r > 0.7) return "#E3000F";
    if (r > 0.4) return "#FFCD00";
    if (r > 0.15) return "#0052FF";
    return "#0033A0";
  };

  return (
    <div className="space-y-6" data-testid="docente-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Mi panel docente</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">
            Hola, {(user?.full_name || "Docente").replace(/^(Prof\.|Profe\.|Dr\.|Dra\.)\s*/i, "").split(" ")[0]}
          </h1>
          <p className="text-sm text-muted-foreground mt-2">
            Vista restringida a tus materias asignadas y los estudiantes de tus programas.
          </p>
        </div>
        {grupos.length > 0 && (
          <Select value={filtroGrupo} onValueChange={setFiltroGrupo}>
            <SelectTrigger className="h-9 w-72 rounded-sm" data-testid="docente-grupo-select">
              <SelectValue placeholder="Todos los grupos" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos mis grupos ({grupos.length})</SelectItem>
              {grupos.map((g) => (
                <SelectItem key={g.codigo_grupo} value={g.codigo_grupo}>
                  {g.codigo_grupo} · {g.asignatura_nombre?.slice(0, 40)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </header>

      {/* Grupos asignados */}
      <div className="dense-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-[#0033A0]" />
          <p className="label-eyebrow">Grupos asignados ({grupos.length})</p>
        </div>
        {loading ? (
          <Skeleton className="h-12 w-full" />
        ) : grupos.length === 0 ? (
          <div className="text-sm text-muted-foreground italic py-4">
            Aún no tienes grupos asignados en este periodo. Contacta al administrador.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
            {grupos.slice(0, 30).map((g) => (
              <button
                key={g.codigo_grupo}
                onClick={() => setFiltroGrupo(g.codigo_grupo === filtroGrupo ? "all" : g.codigo_grupo)}
                className={`text-left border rounded px-3 py-2 transition-soft hover:border-[#0033A0]/40 ${filtroGrupo === g.codigo_grupo ? "border-[#0033A0] bg-[#0033A0]/5" : "border-border"}`}
                data-testid={`docente-grupo-card-${g.codigo_grupo}`}
              >
                <div className="text-xs font-medium truncate">{g.asignatura_nombre}</div>
                <div className="text-[10px] text-muted-foreground mono mt-0.5">{g.codigo_grupo}</div>
                <div className="text-[10px] text-muted-foreground mt-0.5">{g.programa?.slice(0, 30)} · {g.periodo}</div>
              </button>
            ))}
          </div>
        )}
      </div>

      {grupos.length > 0 && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI label="Mis estudiantes" value={fmt(k.total_estudiantes)} sub="matriculados en mis grupos" icon={Users} accent="bg-[#0033A0]/10 text-[#0033A0]" />
            <KPI label="Promedio" value={(k.promedio ?? 0).toFixed(2)} sub="Escala 0–5" icon={GraduationCap} accent="bg-[#FFCD00]/15 text-[#7A6300]" />
            <KPI label="En riesgo" value={fmt(k.en_riesgo)} sub="Promedio < 3.0" icon={AlertTriangle} accent="bg-[#E3000F]/10 text-[#E3000F]" />
            <KPI label="Excelencia" value={fmt(k.excelencia)} sub="Promedio ≥ 4.5" icon={TrendingUp} accent="bg-emerald-500/10 text-emerald-700" />
            <KPI label="Avance curricular" value={`${(k.avance_pct ?? 0).toFixed(0)}%`} sub="Promedio del grupo" icon={TrendingUp} accent="bg-blue-500/10 text-blue-700" />
            <KPI label="Vulnerables" value={fmt(k.vulnerables)} sub="Auto identificación" icon={AlertTriangle} accent="bg-amber-500/10 text-amber-700" />
            <KPI label="Víctimas conflicto" value={fmt(k.victimas)} sub="Requieren acompañamiento" icon={Heart} accent="bg-[#E3000F]/10 text-[#E3000F]" />
            <KPI label="Discapacidad" value={fmt(k.discapacidad)} sub="Apoyo educativo" icon={Accessibility} accent="bg-purple-500/10 text-purple-700" />
          </div>

          <Tabs defaultValue="riesgo">
            <TabsList className="rounded-sm">
              <TabsTrigger value="riesgo" data-testid="docente-tab-riesgo">
                <AlertTriangle className="w-3.5 h-3.5 mr-1.5" /> En riesgo ({enRiesgo.length})
              </TabsTrigger>
              <TabsTrigger value="comparativa" data-testid="docente-tab-comparativa">
                <TrendingUp className="w-3.5 h-3.5 mr-1.5" /> Comparativa periodos
              </TabsTrigger>
              <TabsTrigger value="caracterizacion" data-testid="docente-tab-caracterizacion">Caracterización</TabsTrigger>
              <TabsTrigger value="territorial" data-testid="docente-tab-territorial">Territorial</TabsTrigger>
              <TabsTrigger value="estudiantes" data-testid="docente-tab-estudiantes">Estudiantes</TabsTrigger>
            </TabsList>

            <TabsContent value="riesgo" className="mt-4">
              <div className="dense-card p-5">
                <div className="flex items-end justify-between mb-4">
                  <div>
                    <p className="label-eyebrow text-[#E3000F]">Alertas académicas</p>
                    <h3 className="font-display font-bold text-lg tracking-tight">Estudiantes que requieren atención ({enRiesgo.length})</h3>
                    <p className="text-xs text-muted-foreground mt-1">Ordenados por score de riesgo (nota + factores de vulnerabilidad). Bajo promedio, víctima, SISBEN A/B, discapacidad suman puntos.</p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Score</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Estudiante</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Contacto</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom. grupo</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom. gral</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Motivos</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {enRiesgo.map((s) => (
                        <TableRow key={s.cedula} className="hover:bg-muted/40">
                          <TableCell>
                            <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold ${s.score_riesgo > 40 ? "bg-[#E3000F]/10 text-[#E3000F]" : s.score_riesgo > 20 ? "bg-amber-500/15 text-amber-700" : "bg-muted"}`}>
                              {s.score_riesgo}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div className="text-xs font-medium">{s.nombre} {s.apellidos}</div>
                            <div className="text-[10px] text-muted-foreground mono">{s.cedula}</div>
                          </TableCell>
                          <TableCell className="text-[10px] leading-tight">
                            <div>{s.correo_institucional || s.correo || "—"}</div>
                            {s.telefono && <div className="text-muted-foreground mono">{s.telefono}</div>}
                          </TableCell>
                          <TableCell className="text-[10px] text-muted-foreground">{s.programa?.length > 30 ? s.programa.slice(0, 28) + "…" : s.programa}</TableCell>
                          <TableCell className="text-right">
                            <span className={`kpi-num text-sm ${s.prom_grupo > 0 && s.prom_grupo < 3 ? "text-[#E3000F]" : ""}`}>
                              {s.prom_grupo > 0 ? s.prom_grupo.toFixed(2) : "—"}
                            </span>
                          </TableCell>
                          <TableCell className="text-right">
                            <span className={`kpi-num text-sm ${s.promedio > 0 && s.promedio < 3 ? "text-[#E3000F]" : ""}`}>
                              {s.promedio > 0 ? s.promedio.toFixed(2) : "—"}
                            </span>
                          </TableCell>
                          <TableCell>
                            <div className="flex flex-wrap gap-1">
                              {(s.motivos || []).slice(0, 3).map((m, i) => (
                                <Badge key={i} variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm h-4 px-1">{m}</Badge>
                              ))}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px]" onClick={() => openHist(s.cedula)} data-testid={`view-historico-${s.cedula}`}>
                              <History className="w-3 h-3 mr-1" /> Histórico
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {enRiesgo.length === 0 && (
                        <TableRow><TableCell colSpan={8} className="text-center text-xs text-muted-foreground py-6">🎉 Ningún estudiante en riesgo con los criterios actuales</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="comparativa" className="mt-4">
              <div className="dense-card p-5">
                <div className="flex items-end justify-between mb-4">
                  <div>
                    <p className="label-eyebrow">Progresión</p>
                    <h3 className="font-display font-bold text-lg tracking-tight">Comparativa por grupo · últimos 2 periodos</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      Promedios y tasas de aprobación en 2025-2 vs 2026-1. Ordenados por promedio actual (peores arriba).
                    </p>
                  </div>
                  <Badge variant="outline" className="text-[10px] uppercase tracking-widest rounded-sm">
                    {comparativa.filter((g) => g.promedio_actual !== null).length} grupos con datos
                  </Badge>
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Grupo</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Asignatura</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Docente</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom. actual</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Prom. anterior</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Variación</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">% aprob.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {comparativa.filter((g) => g.promedio_actual !== null).slice(0, 100).map((g) => {
                        const TrendIcon = g.tendencia === "sube" ? ArrowUpRight : g.tendencia === "baja" ? ArrowDownRight : Minus;
                        const trendColor = g.tendencia === "sube" ? "text-emerald-600" : g.tendencia === "baja" ? "text-[#E3000F]" : "text-muted-foreground";
                        const actualLow = g.promedio_actual < 3;
                        return (
                          <TableRow key={g.codigo_grupo} className="hover:bg-muted/40">
                            <TableCell className="text-[10px] mono">{g.codigo_grupo}</TableCell>
                            <TableCell className="text-xs font-medium">{g.asignatura_nombre?.slice(0, 45)}</TableCell>
                            <TableCell className="text-[10px] text-muted-foreground">{g.docente_nombre?.slice(0, 30)}</TableCell>
                            <TableCell className={`text-right kpi-num text-sm ${actualLow ? "text-[#E3000F]" : ""}`}>
                              {g.promedio_actual !== null ? g.promedio_actual.toFixed(2) : "—"}
                            </TableCell>
                            <TableCell className="text-right kpi-num text-sm text-muted-foreground">
                              {g.promedio_anterior !== null ? g.promedio_anterior.toFixed(2) : "—"}
                            </TableCell>
                            <TableCell className={`text-right ${trendColor}`}>
                              <div className="inline-flex items-center gap-1">
                                <TrendIcon className="w-3 h-3" />
                                <span className="kpi-num text-xs">{g.variacion !== null ? (g.variacion > 0 ? "+" : "") + g.variacion : "—"}</span>
                              </div>
                            </TableCell>
                            <TableCell className="text-right text-xs">
                              {g.periodos?.[0]?.tasa_aprobacion !== undefined ? `${g.periodos[0].tasa_aprobacion}%` : "—"}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                      {comparativa.filter((g) => g.promedio_actual !== null).length === 0 && (
                        <TableRow><TableCell colSpan={7} className="text-center text-xs text-muted-foreground py-6">Sin histórico académico disponible</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="caracterizacion" className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="dense-card p-5">
                  <p className="label-eyebrow">Demografía</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Género</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie data={data?.caracterizacion?.genero || []} dataKey="n" nameKey="label" outerRadius={80} innerRadius={40} paddingAngle={2}>
                        {(data?.caracterizacion?.genero || []).map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      </Pie>
                      <Tooltip />
                      <Legend verticalAlign="bottom" iconType="square" wrapperStyle={{ fontSize: 11 }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="dense-card p-5">
                  <p className="label-eyebrow">Socioeconómico</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Estrato</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={data?.caracterizacion?.estrato || []}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey="label" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                      <Bar dataKey="n" fill="#FFCD00" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="dense-card p-5">
                  <p className="label-eyebrow">SISBEN</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Grupo SISBEN</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={data?.caracterizacion?.grupo_sisben || []} layout="vertical">
                      <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis type="category" dataKey="label" width={90} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="n" fill="#0033A0" radius={[0, 2, 2, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="territorial" className="mt-4">
              <div className="dense-card p-0 overflow-hidden">
                <div className="p-4 border-b border-border flex items-center gap-2">
                  <MapPin className="w-4 h-4 text-[#0033A0]" />
                  <div>
                    <p className="label-eyebrow">Mapa</p>
                    <h3 className="font-display font-bold text-lg tracking-tight">Mis estudiantes por municipio</h3>
                  </div>
                </div>
                <div className="h-[520px] relative">
                  <MapContainer center={[6.5, -75.0]} zoom={5} style={{ height: "100%", width: "100%" }} scrollWheelZoom worldCopyJump>
                    <TileLayer
                      attribution='&copy; CARTO'
                      url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    />
                    {munis.map((m, i) => (
                      <CircleMarker
                        key={`${m.codigo}-${i}`}
                        center={[m.lat, m.lon]}
                        radius={Math.max(4, Math.min(22, Math.sqrt(m.n) * 1.6))}
                        pathOptions={{ color: colorFor(m.n), fillColor: colorFor(m.n), fillOpacity: 0.55, weight: 1 }}
                      >
                        <LTooltip>
                          <div className="text-xs">
                            <div className="font-bold">{m.nombre}</div>
                            <div className="text-muted-foreground">{m.departamento}</div>
                            <div className="mt-1">Estudiantes: <b>{m.n.toLocaleString("es-CO")}</b></div>
                            <div>Promedio: <b>{m.prom?.toFixed(2)}</b></div>
                          </div>
                        </LTooltip>
                      </CircleMarker>
                    ))}
                  </MapContainer>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="estudiantes" className="mt-4">
              <div className="dense-card p-5">
                <div className="flex items-end justify-between mb-4 flex-wrap gap-3">
                  <div>
                    <p className="label-eyebrow">Listado</p>
                    <h3 className="font-display font-bold text-lg tracking-tight">Mis estudiantes ({students.length})</h3>
                    <p className="text-xs text-muted-foreground mt-1">Top 200 ordenados por menor promedio. Información sensible no se muestra.</p>
                  </div>
                  <button
                    onClick={() => setOnlyRiesgo((v) => !v)}
                    className={`text-xs px-3 py-1.5 rounded-sm border transition-soft ${onlyRiesgo ? "bg-[#E3000F]/10 border-[#E3000F]/30 text-[#E3000F]" : "border-border hover:bg-muted"}`}
                    data-testid="docente-toggle-riesgo"
                  >
                    {onlyRiesgo ? "✓ Solo en riesgo" : "Mostrar solo en riesgo"}
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Cédula</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Nombre</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Programa</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Nivel</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Promedio</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Ciudad</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Flags</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider"></TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {students.map((s) => (
                        <TableRow key={s.cedula} className="hover:bg-muted/40">
                          <TableCell className="text-xs mono">{s.cedula}</TableCell>
                          <TableCell className="text-xs font-medium">{s.nombre} {s.apellidos}</TableCell>
                          <TableCell className="text-[10px] text-muted-foreground">{s.programa?.length > 30 ? s.programa.slice(0, 28) + "…" : s.programa}</TableCell>
                          <TableCell className="text-xs">{s.nivel}</TableCell>
                          <TableCell className="text-right">
                            <span className={`kpi-num text-sm ${s.promedio < 3 ? "text-[#E3000F]" : s.promedio >= 4.5 ? "text-emerald-600" : ""}`}>
                              {s.promedio?.toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell className="text-xs">{s.ciudad_nombre}</TableCell>
                          <TableCell>
                            <div className="flex gap-1 flex-wrap">
                              {s.grupo_vulnerable && <Badge variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm h-4 px-1 border-amber-500/40 text-amber-700">Vuln</Badge>}
                              {s.victima_conflicto && <Badge variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm h-4 px-1 border-[#E3000F]/40 text-[#E3000F]">Víctima</Badge>}
                              {s.discapacidad_flag && <Badge variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm h-4 px-1 border-purple-500/40 text-purple-700">Disc</Badge>}
                              {s.tipo_ubicacion === "Rural" && <Badge variant="outline" className="text-[8px] uppercase tracking-wider rounded-sm h-4 px-1 border-emerald-500/40 text-emerald-700">Rural</Badge>}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Button size="sm" variant="ghost" className="h-7 px-2 text-[10px]" onClick={() => openHist(s.cedula)}>
                              <History className="w-3 h-3 mr-1" /> Histórico
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {students.length === 0 && (
                        <TableRow><TableCell colSpan={8} className="text-center text-xs text-muted-foreground py-6">Sin estudiantes para mostrar</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}

      {/* Modal Histórico Estudiante */}
      <Dialog open={openHistorico} onOpenChange={setOpenHistorico}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto" data-testid="historico-dialog">
          <DialogHeader>
            <DialogTitle className="font-display tracking-tight">
              Histórico académico
            </DialogTitle>
          </DialogHeader>
          {!historico ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <div className="space-y-4">
              <div className="dense-card p-4">
                <div className="text-xs label-eyebrow">Estudiante</div>
                <div className="font-display text-xl font-bold">{historico.estudiante.nombre} {historico.estudiante.apellidos}</div>
                <div className="text-[10px] text-muted-foreground mono">CC {historico.estudiante.cedula} · {historico.estudiante.correo_institucional || historico.estudiante.correo}</div>
                <div className="grid grid-cols-4 gap-4 mt-4">
                  <div>
                    <span className="label-eyebrow block">Programa</span>
                    <b className="text-xs">{historico.estudiante.programa}</b>
                  </div>
                  <div>
                    <span className="label-eyebrow block">Nivel</span>
                    <b className="kpi-num">{historico.estudiante.nivel}</b>
                  </div>
                  <div>
                    <span className="label-eyebrow block">Promedio actual</span>
                    <b className={`kpi-num ${historico.estudiante.promedio < 3 ? "text-[#E3000F]" : "text-emerald-700"}`}>{historico.estudiante.promedio?.toFixed(2)}</b>
                  </div>
                  <div>
                    <span className="label-eyebrow block">Total notas</span>
                    <b className="kpi-num">{historico.total_notas}</b>
                  </div>
                </div>
                <div className="flex gap-2 mt-3 flex-wrap">
                  {historico.estudiante.grupo_vulnerable && <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm border-amber-500/40 text-amber-700">Vulnerable</Badge>}
                  {historico.estudiante.victima_conflicto && <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm border-[#E3000F]/40 text-[#E3000F]">Víctima conflicto</Badge>}
                  {historico.estudiante.discapacidad_flag && <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm border-purple-500/40 text-purple-700">Discapacidad</Badge>}
                  <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">SISBEN {historico.estudiante.sisben_nivel}</Badge>
                  <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">{historico.estudiante.estrato}</Badge>
                </div>
              </div>

              {/* Evolución promedio */}
              {historico.periodos.length > 1 && (
                <div className="dense-card p-4">
                  <p className="label-eyebrow">Evolución</p>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart data={[...historico.periodos].reverse()}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey="periodo" tick={{ fontSize: 11 }} />
                      <YAxis domain={[0, 5]} tick={{ fontSize: 11 }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                      <Line type="monotone" dataKey="promedio" stroke="#0033A0" strokeWidth={2} dot={{ fill: "#0033A0", r: 5 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

              {/* Notas por periodo */}
              {historico.periodos.map((p) => (
                <div key={p.periodo} className="dense-card p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="label-eyebrow">Periodo {p.periodo}</p>
                      <h4 className="font-display font-bold text-base">
                        Promedio {p.promedio.toFixed(2)}
                        <span className="ml-2 text-xs text-muted-foreground">· {p.aprobadas}/{p.total} aprobadas · {p.reprobadas} reprobadas</span>
                      </h4>
                    </div>
                    <Badge className={`rounded-sm ${p.promedio < 3 ? "bg-[#E3000F]/10 text-[#E3000F]" : p.promedio >= 4.5 ? "bg-emerald-500/15 text-emerald-700" : "bg-[#FFCD00]/20 text-[#7A6300]"}`}>
                      {p.promedio < 3 ? "Riesgo" : p.promedio >= 4.5 ? "Excelencia" : "Regular"}
                    </Badge>
                  </div>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead className="text-[10px] uppercase tracking-wider">Materia</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Docente</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider text-right">Nota</TableHead>
                        <TableHead className="text-[10px] uppercase tracking-wider">Estado</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {p.notas.map((n, i) => (
                        <TableRow key={i} className="hover:bg-muted/40">
                          <TableCell className="text-xs font-medium">{n.asignatura_nombre}</TableCell>
                          <TableCell className="text-[10px] text-muted-foreground">{n.docente_nombre}</TableCell>
                          <TableCell className="text-right">
                            <span className={`kpi-num text-sm ${n.nota < 3 && n.nota > 0 ? "text-[#E3000F]" : n.nota >= 4 ? "text-emerald-700" : ""}`}>
                              {n.nota?.toFixed(2)}
                            </span>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className="text-[9px] uppercase tracking-wider rounded-sm">{n.estado}</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))}
              {historico.periodos.length === 0 && (
                <div className="text-center text-xs text-muted-foreground py-8">Sin histórico académico registrado</div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
