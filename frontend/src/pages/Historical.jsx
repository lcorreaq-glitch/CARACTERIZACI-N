import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useFilters } from "./AppLayout";
import {
  LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Legend, BarChart, Bar
} from "recharts";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";

export default function Historical() {
  const [data, setData] = useState(null);
  const [program, setProgram] = useState("all");
  const { opts } = useFilters();

  useEffect(() => {
    const q = program === "all" ? "" : `programa=${encodeURIComponent(program)}`;
    api.get(`/dashboards/historical?${q}`).then((r) => setData(r.data));
  }, [program]);

  return (
    <div className="space-y-6" data-testid="historical-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Analítica histórica</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Tendencias por periodo</h1>
          <p className="text-sm text-muted-foreground mt-2">Evolución del promedio académico, matriculados y tasas de aprobación a lo largo de los periodos.</p>
        </div>
        <Select value={program} onValueChange={setProgram}>
          <SelectTrigger className="h-9 w-72 rounded-sm" data-testid="historical-program-select">
            <SelectValue placeholder="Todos los programas" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos los programas</SelectItem>
            {(opts.programas || []).map((p) => (<SelectItem key={p} value={p}>{p}</SelectItem>))}
          </SelectContent>
        </Select>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-5 lg:col-span-7">
          <p className="label-eyebrow">Tendencia institucional</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Promedio y tasa de aprobación</h3>
          <ResponsiveContainer width="100%" height={330}>
            <LineChart data={data?.series_periodo || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis yAxisId="left" domain={[0, 5]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis yAxisId="right" orientation="right" domain={[0, 100]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line yAxisId="left" type="monotone" dataKey="promedio" stroke="#0033A0" strokeWidth={2.2} dot={{ r: 4, fill: "#0033A0" }} name="Promedio" />
              <Line yAxisId="right" type="monotone" dataKey="tasa_aprobacion" stroke="#FFCD00" strokeWidth={2.2} dot={{ r: 4, fill: "#FFCD00" }} name="Aprobación %" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="dense-card p-5 lg:col-span-5">
          <p className="label-eyebrow">Matriculados</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Volumen por periodo</h3>
          <ResponsiveContainer width="100%" height={330}>
            <BarChart data={data?.series_periodo || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="matriculados" fill="#0052FF" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dense-card p-5 lg:col-span-12">
          <p className="label-eyebrow">Comparativo por programa</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Evolución detallada {program !== "all" && `· ${program}`}</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={transformPerProgram(data?.by_program || [], program)}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="periodo" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis domain={[0, 5]} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {programLines(data?.by_program || [], program).map((p, i) => (
                <Line key={p} type="monotone" dataKey={p} stroke={["#0033A0", "#E3000F", "#FFCD00", "#059669", "#8B5CF6", "#0052FF"][i % 6]} strokeWidth={2} dot={{ r: 3 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function programLines(items, program) {
  const set = new Set(items.map((i) => i.programa));
  let list = Array.from(set);
  if (program !== "all") return [program];
  return list.slice(0, 6);
}

function transformPerProgram(items, program) {
  const periodos = Array.from(new Set(items.map((i) => i.periodo))).sort();
  const progs = programLines(items, program);
  return periodos.map((per) => {
    const row = { periodo: per };
    progs.forEach((p) => {
      const it = items.find((i) => i.periodo === per && i.programa === p);
      row[p] = it ? it.promedio : null;
    });
    return row;
  });
}
