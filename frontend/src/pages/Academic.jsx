import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import { ExportButtons } from "./Executive";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  ComposedChart, Line, Cell, LabelList, Legend, LineChart,
} from "recharts";
import { TrendingDown, TrendingUp, BookOpen, CheckCircle2, AlertTriangle } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

const fmt = (n) => (n || 0).toLocaleString("es-CO");

function ChartCard({ title, eyebrow, children, span = "", note }) {
  return (
    <div className={`dense-card p-5 ${span}`}>
      <div className="mb-4">
        <p className="label-eyebrow">{eyebrow}</p>
        <h3 className="font-display font-bold text-lg tracking-tight">{title}</h3>
        {note && <p className="text-[11px] text-muted-foreground mt-1">{note}</p>}
      </div>
      {children}
    </div>
  );
}

function KPI({ label, value, sub, icon: Icon, accent, testid }) {
  return (
    <div className="dense-card p-5" data-testid={testid}>
      <div className="flex items-start justify-between">
        <div>
          <p className="label-eyebrow">{label}</p>
          <div className="kpi-num text-3xl md:text-4xl mt-2">{value}</div>
          {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
        </div>
        {Icon && <div className={`p-2 rounded-sm ${accent || "bg-muted"}`}><Icon className="w-4 h-4" /></div>}
      </div>
    </div>
  );
}

const COLOR_ESTADOS = {
  "Aprobada": "#059669",
  "Reprobada": "#E3000F",
  "Cancelada": "#FFCD00",
  "Matriculada": "#0033A0",
  "Prematriculada": "#8B5CF6",
  "Habilitada-Aprobada": "#10B981",
  "Habilitada-Reprobada": "#F87171",
  "Homologada": "#94A3B8",
  "No Aplica": "#CBD5E1",
};
const ESTADOS_ORDEN = ["Aprobada", "Habilitada-Aprobada", "Reprobada", "Habilitada-Reprobada", "Cancelada", "Matriculada", "Prematriculada", "Homologada", "No Aplica"];

export default function Academic() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/dashboards/academic?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const k = data?.kpis || {};

  return (
    <div className="space-y-6" data-testid="academic-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Dashboard académico</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Rendimiento y trayectoria</h1>
          <p className="text-sm text-muted-foreground mt-2">
            Basado en <b>169.376 notas</b> de <b>2025-2</b> y <b>2026-1</b> + nivel académico <b>2026-2</b>.
          </p>
        </div>
        <ExportButtons scope="academico" filters={filters} />
      </header>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <>
          {/* KPIs principales */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI label="En riesgo (<3.0)" value={fmt(k.en_riesgo)} sub="Requiere intervención" icon={AlertTriangle} accent="bg-[#E3000F]/10 text-[#E3000F]" testid="kpi-en-riesgo" />
            <KPI label="Excelencia (≥4.5)" value={fmt(k.excelencia)} sub="Talento destacado" icon={TrendingUp} accent="bg-emerald-500/10 text-emerald-700" testid="kpi-excelencia" />
            <KPI label="Tasa aprobación global" value={`${k.tasa_aprob_global ?? 0}%`} sub={`${fmt(k.notas_evaluadas)} notas evaluadas`} icon={CheckCircle2} accent="bg-[#0033A0]/10 text-[#0033A0]" testid="kpi-tasa-aprob" />
            <KPI label="Habilitación exitosa" value={`${k.tasa_habilitacion_exito ?? 0}%`} sub={`${fmt(k.total_habilitaciones)} habilitaciones totales`} icon={BookOpen} accent="bg-[#FFCD00]/15 text-[#7A6300]" testid="kpi-hab" />
          </div>

          {/* ============ SECCIÓN 1 · Comparativo por periodo ============ */}
          <div>
            <h2 className="font-display font-bold text-xl tracking-tight mb-3">1 · Comparativo 2025-2 vs 2026-1</h2>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

              <ChartCard title="Estados de notas por periodo" eyebrow="Detalle · barras apiladas" span="lg:col-span-7"
                note="Cuántas notas se aprobaron, reprobaron, cancelaron o quedaron en habilitación en cada periodo.">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={data?.estados_por_periodo || []}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="periodo" tick={{ fontSize: 12, fill: "hsl(var(--foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    {ESTADOS_ORDEN.map((est) => (
                      <Bar key={est} dataKey={est} stackId="a" fill={COLOR_ESTADOS[est]} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Distribución de notas" eyebrow="Calificaciones · ambos periodos" span="lg:col-span-5"
                note="Cantidad de notas en cada rango de calificación.">
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={data?.distribucion_notas || []}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="rango" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="p_2025_2" name="2025-2" fill="#059669" />
                    <Bar dataKey="p_2026_1" name="2026-1" fill="#E3000F" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Promedio y % aprobación por bloque" eyebrow="Bloques × periodo" span="lg:col-span-12"
                note="Rendimiento comparativo Bloque 1 vs Bloque 2 en cada periodo.">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b text-muted-foreground text-[10px] uppercase tracking-widest">
                        <th className="text-left py-2">Periodo</th>
                        <th className="text-left py-2">Bloque</th>
                        <th className="text-right py-2">Notas</th>
                        <th className="text-right py-2">Promedio</th>
                        <th className="text-right py-2">% aprobación</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(data?.bloque_periodo || []).map((r, i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2 font-medium">{r.periodo}</td>
                          <td>{r.bloque}</td>
                          <td className="text-right mono">{fmt(r.n)}</td>
                          <td className={`text-right kpi-num text-sm ${r.prom < 3 ? "text-[#E3000F]" : r.prom >= 4 ? "text-emerald-700" : ""}`}>{r.prom?.toFixed(2)}</td>
                          <td className={`text-right ${r.aprob_pct < 60 ? "text-[#E3000F]" : r.aprob_pct >= 80 ? "text-emerald-700" : "text-amber-600"}`}>{r.aprob_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </ChartCard>
            </div>
          </div>

          {/* ============ SECCIÓN 2 · Rendimiento por materia y facultad ============ */}
          <div>
            <h2 className="font-display font-bold text-xl tracking-tight mb-3">2 · Materias críticas y rendimiento</h2>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

              <ChartCard title="Top 10 asignaturas con mayor reprobación" eyebrow="Materias críticas" span="lg:col-span-6"
                note="Solo materias con más de 30 registros. Ordenadas por % reprobación.">
                <div className="space-y-2">
                  {(data?.top_reprobadas || []).map((a, i) => (
                    <div key={i} className="flex items-center justify-between py-1 border-b border-border/40 last:border-0">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate" title={a.asignatura}>{a.asignatura}</div>
                        <div className="text-[10px] text-muted-foreground">{fmt(a.n)} notas · prom {a.prom?.toFixed(2)}</div>
                      </div>
                      <Badge variant="outline" className="text-[10px] text-[#E3000F] border-[#E3000F]/40 ml-2">
                        {a.pct_reprob}% reprob
                      </Badge>
                    </div>
                  ))}
                </div>
              </ChartCard>

              <ChartCard title="Top 10 asignaturas con mejor rendimiento" eyebrow="Excelencia académica" span="lg:col-span-6"
                note="Solo materias con más de 30 registros. Ordenadas por promedio.">
                <div className="space-y-2">
                  {(data?.top_aprobadas || []).map((a, i) => (
                    <div key={i} className="flex items-center justify-between py-1 border-b border-border/40 last:border-0">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate" title={a.asignatura}>{a.asignatura}</div>
                        <div className="text-[10px] text-muted-foreground">{fmt(a.n)} notas · {a.pct_aprob}% aprob</div>
                      </div>
                      <Badge variant="outline" className="text-[10px] text-emerald-700 border-emerald-700/40 ml-2">
                        {a.prom?.toFixed(2)}
                      </Badge>
                    </div>
                  ))}
                </div>
              </ChartCard>

              <ChartCard title="Rendimiento por área de formación" eyebrow="Facultad de la asignatura" span="lg:col-span-6"
                note="Promedio ponderado y tasa de aprobación por área institucional.">
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={data?.by_area || []} layout="vertical" margin={{ left: 8, right: 40 }}>
                    <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis type="category" dataKey="area" width={200} tick={{ fontSize: 9, fill: "hsl(var(--foreground))" }}
                      tickFormatter={(v) => v?.replace("Facultad de ", "").slice(0, 32) + (v?.length > 32 ? "…" : "")} interval={0} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Bar dataKey="n" fill="#0033A0" name="Notas" radius={[0, 2, 2, 0]}>
                      <LabelList dataKey="pct_aprob" position="right" formatter={(v) => `${v}%`} style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
                    </Bar>
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Promedio por programa" eyebrow="Rendimiento · ponderado desde notas" span="lg:col-span-6"
                note="Promedio real de todas las notas del programa (no promedio de promedios).">
                <ResponsiveContainer width="100%" height={Math.max(280, (data?.by_program_avg?.length || 0) * 22)}>
                  <BarChart data={data?.by_program_avg || []} layout="vertical" margin={{ left: 8, right: 40 }}>
                    <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                    <XAxis type="number" domain={[0, 5]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis type="category" dataKey="programa" width={180} tick={{ fontSize: 9, fill: "hsl(var(--foreground))" }}
                      tickFormatter={(v) => v?.length > 32 ? v.slice(0, 30) + "…" : v} interval={0} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Bar dataKey="prom" radius={[0, 2, 2, 0]}>
                      {(data?.by_program_avg || []).map((d, i) => (
                        <Cell key={i} fill={d.prom < 3 ? "#E3000F" : d.prom < 3.5 ? "#FFCD00" : d.prom < 4 ? "#0052FF" : "#059669"} />
                      ))}
                      <LabelList dataKey="prom" position="right" style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

            </div>
          </div>

          {/* ============ SECCIÓN 3 · Trayectoria estudiantil ============ */}
          <div>
            <h2 className="font-display font-bold text-xl tracking-tight mb-3">3 · Trayectoria estudiantil (nivel 2026-2)</h2>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

              <ChartCard title="Estudiantes por semestre" eyebrow="Nivel académico · 2026-2" span="lg:col-span-6"
                note="Distribución del cuerpo estudiantil por semestre matriculado en 2026-2.">
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={data?.by_nivel || []}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="nivel" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(v) => v === 0 ? "Pre-grado" : `Sem ${v}`} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <YAxis yAxisId="right" orientation="right" domain={[0, 5]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar yAxisId="left" dataKey="n" fill="#0033A0" name="Estudiantes" radius={[3, 3, 0, 0]}>
                      <LabelList dataKey="n" position="top" style={{ fontSize: 10 }} />
                    </Bar>
                    <Line yAxisId="right" dataKey="prom" stroke="#FFCD00" strokeWidth={2} dot={{ r: 4, fill: "#FFCD00" }} name="Promedio" />
                  </ComposedChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Créditos aprobados vs reprobados" eyebrow="Carga académica" span="lg:col-span-6"
                note="Créditos acumulados por periodo según estado de la nota.">
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data?.creditos || []}>
                    <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
                    <XAxis dataKey="periodo" tick={{ fontSize: 12, fill: "hsl(var(--foreground))" }} />
                    <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 10 }} />
                    <Bar dataKey="aprobados" fill="#059669" name="Aprobados">
                      <LabelList dataKey="aprobados" position="top" formatter={fmt} style={{ fontSize: 10 }} />
                    </Bar>
                    <Bar dataKey="reprobados" fill="#E3000F" name="Reprobados">
                      <LabelList dataKey="reprobados" position="top" formatter={fmt} style={{ fontSize: 10 }} />
                    </Bar>
                    <Bar dataKey="cancelados" fill="#FFCD00" name="Cancelados">
                      <LabelList dataKey="cancelados" position="top" formatter={fmt} style={{ fontSize: 10 }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard title="Habilitaciones por periodo" eyebrow="Segunda oportunidad" span="lg:col-span-6"
                note="Cuántas habilitaciones se otorgaron y qué porcentaje resultó aprobado.">
                <div className="grid grid-cols-2 gap-4">
                  {(data?.habilitaciones || []).map((h) => (
                    <div key={h.periodo} className="rounded-sm border border-border p-4">
                      <div className="text-xs text-muted-foreground uppercase tracking-widest">{h.periodo}</div>
                      <div className="mt-2 flex items-end justify-between">
                        <div>
                          <div className="text-[10px] text-muted-foreground">Habilitaciones</div>
                          <div className="kpi-num text-2xl">{fmt(h.total)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] text-muted-foreground">% éxito</div>
                          <div className={`kpi-num text-2xl ${h.pct_exito >= 70 ? "text-emerald-700" : "text-amber-600"}`}>{h.pct_exito}%</div>
                        </div>
                      </div>
                      <div className="mt-2 text-[10px] text-muted-foreground">{fmt(h.exito)} aprobadas · {fmt(h.total - h.exito)} reprobadas</div>
                    </div>
                  ))}
                </div>
              </ChartCard>

              <ChartCard title="Avance curricular por programa" eyebrow="Permanencia · % aprobadas" span="lg:col-span-6"
                note="Porcentaje promedio de materias aprobadas por los estudiantes de cada programa.">
                <ResponsiveContainer width="100%" height={Math.max(280, (data?.avance?.length || 0) * 22)}>
                  <BarChart data={data?.avance || []} layout="vertical" margin={{ left: 8, right: 40 }}>
                    <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} unit="%" />
                    <YAxis type="category" dataKey="programa" width={180} tick={{ fontSize: 9, fill: "hsl(var(--foreground))" }}
                      tickFormatter={(v) => v?.length > 32 ? v.slice(0, 30) + "…" : v} interval={0} />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                    <Bar dataKey="avance" fill="#FFCD00" radius={[0, 2, 2, 0]}>
                      <LabelList dataKey="avance" position="right" formatter={(v) => `${v}%`} style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

            </div>
          </div>
        </>
      )}
    </div>
  );
}
