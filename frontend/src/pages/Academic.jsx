import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  ComposedChart, Line, LineChart, Cell
} from "recharts";
import { TrendingDown, TrendingUp, BookOpen } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

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

  const distribucion = (data?.distribucion_notas || []).map((b) => {
    const lo = b._id === "Otros" ? null : b._id;
    const labels = { 0: "0.0–1.0", 1: "1.0–2.0", 2: "2.0–3.0", 3: "3.0–3.5", 3.5: "3.5–4.0", 4: "4.0–4.5", 4.5: "4.5–5.0" };
    return { rango: labels[lo] || lo, n: b.n };
  });

  return (
    <div className="space-y-6" data-testid="academic-dashboard">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Dashboard académico</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Rendimiento y avance</h1>
        <p className="text-sm text-muted-foreground mt-2">Análisis de promedio, distribución de notas, materias críticas y avance curricular.</p>
      </header>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="dense-card p-5">
          <p className="label-eyebrow">En riesgo (&lt;3.0)</p>
          <div className="kpi-num text-3xl md:text-4xl text-[#E3000F] mt-2">{(data?.en_riesgo || 0).toLocaleString("es-CO")}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center"><TrendingDown className="w-3 h-3 mr-1" /> requiere intervención</div>
        </div>
        <div className="dense-card p-5">
          <p className="label-eyebrow">Excelencia (&gt;=4.5)</p>
          <div className="kpi-num text-3xl md:text-4xl text-emerald-600 mt-2">{(data?.excelencia || 0).toLocaleString("es-CO")}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center"><TrendingUp className="w-3 h-3 mr-1" /> talento destacado</div>
        </div>
        <div className="dense-card p-5">
          <p className="label-eyebrow">Programas analizados</p>
          <div className="kpi-num text-3xl md:text-4xl mt-2">{(data?.by_program_avg || []).length}</div>
          <div className="text-xs text-muted-foreground mt-1 flex items-center"><BookOpen className="w-3 h-3 mr-1" /> con datos suficientes</div>
        </div>
        <div className="dense-card p-5">
          <p className="label-eyebrow">Facultades</p>
          <div className="kpi-num text-3xl md:text-4xl mt-2">{(data?.by_facultad || []).length}</div>
          <div className="text-xs text-muted-foreground mt-1">Agrupación institucional</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <ChartCard title="Promedio por programa" eyebrow="Rendimiento" span="lg:col-span-7">
          {loading ? <Skeleton className="h-80" /> :
            <ResponsiveContainer width="100%" height={420}>
              <BarChart data={data?.by_program_avg || []} layout="vertical" margin={{ left: 8, right: 24 }}>
                <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                <XAxis type="number" domain={[0, 5]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis type="category" dataKey="programa" width={180} tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} tickFormatter={(v) => v?.length > 30 ? v.slice(0, 28) + "…" : v} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
                <Bar dataKey="prom" radius={[0, 2, 2, 0]}>
                  {(data?.by_program_avg || []).map((d, i) => (
                    <Cell key={i} fill={d.prom < 3 ? "#E3000F" : d.prom < 3.5 ? "#FFCD00" : d.prom < 4 ? "#0052FF" : "#059669"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          }
        </ChartCard>

        <ChartCard title="Distribución de notas" eyebrow="Calificaciones" span="lg:col-span-5">
          <ResponsiveContainer width="100%" height={420}>
            <BarChart data={distribucion}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="rango" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#0033A0" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Promedio por facultad" eyebrow="Facultades" span="lg:col-span-7">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={data?.by_facultad || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="facultad" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} interval={0} angle={-12} textAnchor="end" height={70} />
              <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar yAxisId="left" dataKey="n" fill="#0033A0" radius={[3, 3, 0, 0]} name="Estudiantes" />
              <Line yAxisId="right" dataKey="prom" stroke="#E3000F" strokeWidth={2} dot={{ r: 4, fill: "#E3000F" }} name="Promedio" />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Avance curricular por programa" eyebrow="Permanencia" span="lg:col-span-5">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data?.avance || []} layout="vertical">
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} unit="%" />
              <YAxis type="category" dataKey="programa" width={150} tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} tickFormatter={(v) => v?.length > 24 ? v.slice(0, 22) + "…" : v} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="avance" fill="#FFCD00" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
