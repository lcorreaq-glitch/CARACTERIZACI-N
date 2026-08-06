import { useEffect, useState } from "react";
import api, { API } from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend, LabelList
} from "recharts";
import { Users, GraduationCap, Building2, MapPin, AlertTriangle, Heart, Accessibility, TrendingUp, Trees, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const PALETTE = ["#0033A0", "#0052FF", "#FFCD00", "#E3000F", "#059669", "#8B5CF6"];

export function ExportButtons({ scope, filters }) {
  const downloadExport = (endpoint, fmt) => {
    const token = localStorage.getItem("iud_token");
    const q = new URLSearchParams(filters);
    q.append("fmt", fmt);
    fetch(`${API}/${endpoint}?${q.toString()}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob()).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${scope}_${new Date().toISOString().slice(0, 10)}.${fmt}`;
        a.click();
        URL.revokeObjectURL(url);
      });
  };
  return (
    <div className="flex gap-2">
      <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport(`exports/dashboard/${scope}`, "xlsx")} data-testid={`export-${scope}-xlsx`}>
        <Download className="w-3.5 h-3.5 mr-2" /> Excel
      </Button>
      <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport(`exports/dashboard/${scope}`, "csv")} data-testid={`export-${scope}-csv`}>
        <Download className="w-3.5 h-3.5 mr-2" /> CSV
      </Button>
      <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport("exports/students", "xlsx")} data-testid={`export-${scope}-students`}>
        <Download className="w-3.5 h-3.5 mr-2" /> Base estudiantes
      </Button>
    </div>
  );
}

function KPI({ label, value, sub, icon: Icon, accent }) {
  return (
    <div className="dense-card p-5 transition-soft hover:border-foreground/30" data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
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

function ChartCard({ title, eyebrow, children, span = "" }) {
  return (
    <div className={`dense-card p-5 ${span}`}>
      <div className="mb-4">
        <p className="label-eyebrow">{eyebrow}</p>
        <h3 className="font-display font-bold text-lg tracking-tight">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function Executive() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/dashboards/executive?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const k = data?.kpis || {};
  const fmt = (n) => (n || 0).toLocaleString("es-CO");

  return (
    <div className="space-y-6" data-testid="executive-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Dashboard ejecutivo</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Panorama institucional</h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
            Indicadores consolidados de la base estudiantil. Aplique filtros globales para segmentar la información.
          </p>
        </div>
        <ExportButtons scope="ejecutivo" filters={filters} />
      </header>

      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : (
        <>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPI label="Total estudiantes" value={fmt(k.total)} sub={`${fmt(k.matriculados)} matriculados`} icon={Users} accent="bg-[#0033A0]/10 text-[#0033A0]" />
          <KPI label="Promedio general" value={(k.promedio ?? 0).toFixed(2)} sub="Última nota disponible" icon={GraduationCap} accent="bg-[#FFCD00]/15 text-[#7A6300]" />
          <KPI label="Programas" value={fmt(k.programas)} sub={`${k.facultades} facultades`} icon={Building2} accent="bg-emerald-500/10 text-emerald-700" />
          <KPI label="Avance curricular" value={`${(k.avance_pct ?? 0).toFixed(0)}%`} sub="% aprobadas del estudiante" icon={TrendingUp} accent="bg-blue-500/10 text-blue-700" />
          <KPI label="Vivienda rural" value={fmt(k.rurales)} sub={`${((k.rurales / (k.total || 1)) * 100).toFixed(1)}% (Rural + Semirural)`} icon={Trees} accent="bg-green-700/10 text-green-800" />
          <KPI label="Víctimas conflicto" value={fmt(k.victimas)} sub={`${((k.victimas / (k.total || 1)) * 100).toFixed(1)}% del total`} icon={Heart} accent="bg-[#E3000F]/10 text-[#E3000F]" />
          <KPI label="Grupo vulnerable" value={fmt(k.vulnerables)} sub="Auto identificación" icon={AlertTriangle} accent="bg-amber-500/10 text-amber-700" />
          <KPI label="Discapacidad" value={fmt(k.discapacidad)} sub="Reportada por el estudiante" icon={Accessibility} accent="bg-purple-500/10 text-purple-700" />
        </div>

        {/* Promedios por periodo histórico */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="dense-card p-5" data-testid="periodo-2025-2">
            <p className="label-eyebrow text-[#0033A0]">Histórico académico</p>
            <div className="flex items-end justify-between gap-4 mt-1">
              <div>
                <h3 className="font-display font-bold text-lg tracking-tight">Periodo 2025-2</h3>
                <p className="text-xs text-muted-foreground">{fmt(k.notas_2025_2)} notas registradas</p>
              </div>
              <div className="text-right">
                <div className={`kpi-num text-4xl ${(k.promedio_2025_2 || 0) < 3 ? "text-[#E3000F]" : "text-emerald-700"}`}>
                  {(k.promedio_2025_2 ?? 0).toFixed(2)}
                </div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{(k.aprob_pct_2025_2 ?? 0).toFixed(0)}% aprobación</div>
              </div>
            </div>
          </div>
          <div className="dense-card p-5" data-testid="periodo-2026-1">
            <p className="label-eyebrow text-[#0033A0]">Periodo más reciente</p>
            <div className="flex items-end justify-between gap-4 mt-1">
              <div>
                <h3 className="font-display font-bold text-lg tracking-tight">Periodo 2026-1</h3>
                <p className="text-xs text-muted-foreground">{fmt(k.notas_2026_1)} notas registradas</p>
              </div>
              <div className="text-right">
                <div className={`kpi-num text-4xl ${(k.promedio_2026_1 || 0) < 3 ? "text-[#E3000F]" : "text-emerald-700"}`}>
                  {(k.promedio_2026_1 ?? 0).toFixed(2)}
                </div>
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{(k.aprob_pct_2026_1 ?? 0).toFixed(0)}% aprobación</div>
              </div>
            </div>
            {(k.promedio_2026_1 !== undefined && k.promedio_2025_2 !== undefined && k.promedio_2025_2 > 0) && (
              <div className="mt-3 text-[11px] text-muted-foreground">
                Variación: <span className={`font-semibold ${(k.promedio_2026_1 - k.promedio_2025_2) < 0 ? "text-[#E3000F]" : "text-emerald-700"}`}>
                  {(k.promedio_2026_1 - k.promedio_2025_2) > 0 ? "+" : ""}{(k.promedio_2026_1 - k.promedio_2025_2).toFixed(2)}
                </span> frente al periodo anterior
              </div>
            )}
          </div>
        </div>
        </>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <ChartCard title="Estudiantes por programa" eyebrow="Distribución" span="lg:col-span-7">
          <ResponsiveContainer width="100%" height={Math.max(360, (data?.by_program?.length || 0) * 24)}>
            <BarChart data={data?.by_program || []} layout="vertical" margin={{ left: 8, right: 40, top: 4, bottom: 4 }}>
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis type="category" dataKey="programa" tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} width={260} tickFormatter={(v) => v?.length > 40 ? v.slice(0, 38) + "…" : v} interval={0} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#0033A0" radius={[0, 2, 2, 0]}>
                <LabelList dataKey="n" position="right" style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Género" eyebrow="Caracterización" span="lg:col-span-5">
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie data={data?.by_genero || []} dataKey="n" nameKey="genero" outerRadius={90} innerRadius={50} paddingAngle={2}>
                {(data?.by_genero || []).map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              </Pie>
              <Tooltip />
              <Legend verticalAlign="bottom" iconType="square" wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Distribución por estrato" eyebrow="Socioeconómico" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.by_estrato || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="estrato" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#FFCD00" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Tipo de ubicación" eyebrow="Territorial (Tipo de vivienda)" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.by_ubicacion || []} layout="vertical">
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis type="category" dataKey="tipo" tick={{ fontSize: 11, fill: "hsl(var(--foreground))" }} width={90} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#059669" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Grupos etarios" eyebrow="Demografía (categoría)" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.by_edad || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="rango" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#0033A0" radius={[3, 3, 0, 0]}>
                <LabelList dataKey="n" position="top" style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Rangos de edad" eyebrow="Demografía (numérico)" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.by_rango_edad || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="rango" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#FFCD00" radius={[3, 3, 0, 0]}>
                <LabelList dataKey="n" position="top" style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Tipo de vulnerabilidad" eyebrow="Enfoque diferencial" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.by_vulnerabilidad || []} layout="vertical">
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis type="category" dataKey="tipo" tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} width={130} tickFormatter={(v) => v?.length > 22 ? v.slice(0, 20) + "…" : v} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#E3000F" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Georeferenciación · departamento de residencia" eyebrow="Territorial" span="lg:col-span-6">
          <ResponsiveContainer width="100%" height={Math.max(340, (data?.by_departamento?.length || 0) * 26)}>
            <BarChart data={data?.by_departamento || []} layout="vertical" margin={{ left: 8, right: 40 }}>
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis type="category" dataKey="departamento" tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} width={150} interval={0} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#8B5CF6" radius={[0, 2, 2, 0]}>
                <LabelList dataKey="n" position="right" style={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
