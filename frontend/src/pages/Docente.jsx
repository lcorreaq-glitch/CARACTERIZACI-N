import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend
} from "recharts";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LTooltip } from "react-leaflet";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { AlertTriangle, BookOpen, Users, TrendingUp, Heart, Accessibility, GraduationCap, MapPin } from "lucide-react";

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
  const [loading, setLoading] = useState(true);
  const [filtroMateria, setFiltroMateria] = useState("all");
  const [onlyRiesgo, setOnlyRiesgo] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.get("/dashboards/docente/me").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const q = new URLSearchParams();
    if (filtroMateria !== "all") q.append("materia_id", filtroMateria);
    if (onlyRiesgo) q.append("riesgo", "true");
    api.get(`/dashboards/docente/students?${q.toString()}`).then((r) => setStudents(r.data.students || []));
  }, [filtroMateria, onlyRiesgo]);

  const fmt = (n) => (n || 0).toLocaleString("es-CO");
  const k = data?.kpis || {};
  const materias = data?.materias || [];

  const distribucion = (data?.distribucion_notas || []).map((b) => {
    const labels = { 0: "0–1", 1: "1–2", 2: "2–3", 3: "3–3.5", 3.5: "3.5–4", 4: "4–4.5", 4.5: "4.5–5" };
    return { rango: labels[b._id] || b._id, n: b.n };
  });

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
        {materias.length > 0 && (
          <Select value={filtroMateria} onValueChange={setFiltroMateria}>
            <SelectTrigger className="h-9 w-72 rounded-sm" data-testid="docente-materia-select">
              <SelectValue placeholder="Todas las materias" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todas mis materias</SelectItem>
              {materias.map((m) => (
                <SelectItem key={m.id} value={m.materia_id}>
                  {m.materia_nombre} · {m.periodo}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </header>

      {/* Materias asignadas */}
      <div className="dense-card p-5">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-[#0033A0]" />
          <p className="label-eyebrow">Materias asignadas</p>
        </div>
        {loading ? (
          <Skeleton className="h-12 w-full" />
        ) : materias.length === 0 ? (
          <div className="text-sm text-muted-foreground italic py-4">
            Aún no tienes materias asignadas. Solicita al administrador la asignación en el módulo de Administración → Docente-Materia.
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {materias.map((m) => (
              <div key={m.id} className="border border-border rounded px-3 py-2 transition-soft hover:border-[#0033A0]/40" data-testid={`docente-materia-card-${m.materia_id}`}>
                <div className="text-sm font-medium">{m.materia_nombre}</div>
                <div className="text-[10px] text-muted-foreground tracking-widest uppercase mt-0.5">
                  {m.programa_nombre || "Sin programa"} · {m.periodo}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {materias.length > 0 && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI label="Mis estudiantes" value={fmt(k.total_estudiantes)} sub={`${fmt(k.matriculados)} matriculados`} icon={Users} accent="bg-[#0033A0]/10 text-[#0033A0]" />
            <KPI label="Promedio" value={(k.promedio ?? 0).toFixed(2)} sub="Escala 0–5" icon={GraduationCap} accent="bg-[#FFCD00]/15 text-[#7A6300]" />
            <KPI label="En riesgo" value={fmt(k.en_riesgo)} sub="Promedio < 3.0" icon={AlertTriangle} accent="bg-[#E3000F]/10 text-[#E3000F]" />
            <KPI label="Excelencia" value={fmt(k.excelencia)} sub="Promedio ≥ 4.5" icon={TrendingUp} accent="bg-emerald-500/10 text-emerald-700" />
            <KPI label="Avance curricular" value={`${(k.avance_pct ?? 0).toFixed(0)}%`} sub="Promedio del grupo" icon={TrendingUp} accent="bg-blue-500/10 text-blue-700" />
            <KPI label="Vulnerables" value={fmt(k.vulnerables)} sub="Auto identificación" icon={AlertTriangle} accent="bg-amber-500/10 text-amber-700" />
            <KPI label="Víctimas conflicto" value={fmt(k.victimas)} sub="Requieren acompañamiento" icon={Heart} accent="bg-[#E3000F]/10 text-[#E3000F]" />
            <KPI label="Discapacidad" value={fmt(k.discapacidad)} sub="Apoyo educativo" icon={Accessibility} accent="bg-purple-500/10 text-purple-700" />
          </div>

          <Tabs defaultValue="academico">
            <TabsList className="rounded-sm">
              <TabsTrigger value="academico" data-testid="docente-tab-academico">Académico</TabsTrigger>
              <TabsTrigger value="caracterizacion" data-testid="docente-tab-caracterizacion">Caracterización</TabsTrigger>
              <TabsTrigger value="territorial" data-testid="docente-tab-territorial">Territorial</TabsTrigger>
              <TabsTrigger value="estudiantes" data-testid="docente-tab-estudiantes">Estudiantes</TabsTrigger>
            </TabsList>

            <TabsContent value="academico" className="mt-4">
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
                <div className="dense-card p-5 lg:col-span-7">
                  <p className="label-eyebrow">Notas</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Distribución de promedios</h3>
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={distribucion}>
                      <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                      <XAxis dataKey="rango" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                      <Bar dataKey="n" radius={[3, 3, 0, 0]}>
                        {distribucion.map((d, i) => (
                          <Cell key={i} fill={d.rango?.startsWith("0") || d.rango?.startsWith("1") || d.rango?.startsWith("2") ? "#E3000F" : d.rango?.startsWith("3") ? "#FFCD00" : "#059669"} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="dense-card p-5 lg:col-span-5">
                  <p className="label-eyebrow">Por programa</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Estudiantes y promedio</h3>
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={data?.by_programa || []} layout="vertical" margin={{ left: 8 }}>
                      <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis type="category" dataKey="programa" width={130} tick={{ fontSize: 9, fill: "hsl(var(--foreground))" }} tickFormatter={(v) => v?.length > 22 ? v.slice(0, 20) + "…" : v} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                      <Bar dataKey="n" fill="#0033A0" radius={[0, 2, 2, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
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
                      <Pie data={data?.caracterizacion?.genero || []} dataKey="n" nameKey="genero" outerRadius={80} innerRadius={40} paddingAngle={2}>
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
                      <XAxis dataKey="estrato" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                      <Bar dataKey="n" fill="#FFCD00" radius={[3, 3, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="dense-card p-5">
                  <p className="label-eyebrow">Territorial</p>
                  <h3 className="font-display font-bold text-lg tracking-tight mb-3">Ubicación</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={data?.caracterizacion?.ubicacion || []} layout="vertical">
                      <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                      <YAxis type="category" dataKey="tipo" width={90} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="n" fill="#059669" radius={[0, 2, 2, 0]} />
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
                        </TableRow>
                      ))}
                      {students.length === 0 && (
                        <TableRow><TableCell colSpan={7} className="text-center text-xs text-muted-foreground py-6">Sin estudiantes para mostrar</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
