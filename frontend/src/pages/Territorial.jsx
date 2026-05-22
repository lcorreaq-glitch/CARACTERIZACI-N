import { useEffect, useState, useMemo } from "react";
import api from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LTooltip } from "react-leaflet";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";

export default function Territorial() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/dashboards/territorial?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const munis = data?.municipios || [];
  const maxN = useMemo(() => Math.max(1, ...munis.map((m) => m.n)), [munis]);
  const topMun = munis.slice(0, 15);

  const colorFor = (n) => {
    const r = n / maxN;
    if (r > 0.7) return "#E3000F";
    if (r > 0.4) return "#FFCD00";
    if (r > 0.15) return "#0052FF";
    return "#0033A0";
  };

  return (
    <div className="space-y-6" data-testid="territorial-dashboard">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Dashboard territorial</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Cobertura geográfica</h1>
        <p className="text-sm text-muted-foreground mt-2">Distribución por municipio sobre el mapa de Colombia. Tamaño y color indican concentración estudiantil.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-0 overflow-hidden lg:col-span-8" data-testid="territorial-map">
          <div className="p-4 border-b border-border">
            <p className="label-eyebrow">Mapa de calor</p>
            <h3 className="font-display font-bold text-lg tracking-tight">Concentración por municipio</h3>
          </div>
          <div className="h-[540px] relative">
            <MapContainer center={[6.6, -75.6]} zoom={7} style={{ height: "100%", width: "100%" }} scrollWheelZoom>
                <TileLayer
                  attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />
                {munis.map((m, i) => (
                  <CircleMarker
                    key={`${m.codigo}-${i}`}
                    center={[m.lat, m.lon]}
                    radius={Math.max(4, Math.min(24, Math.sqrt(m.n) * 1.3))}
                    pathOptions={{ color: colorFor(m.n), fillColor: colorFor(m.n), fillOpacity: 0.55, weight: 1 }}
                  >
                    <LTooltip>
                      <div className="text-xs">
                        <div className="font-bold">{m.nombre}</div>
                        <div className="text-muted-foreground">{m.departamento}</div>
                        <div className="mt-1">Estudiantes: <b>{m.n.toLocaleString("es-CO")}</b></div>
                        <div>Promedio: <b>{m.prom?.toFixed(2)}</b></div>
                        <div>Vulnerables: <b>{m.vulnerables}</b></div>
                        <div>Rural: <b>{m.rural}</b></div>
                      </div>
                    </LTooltip>
                  </CircleMarker>
                ))}
              </MapContainer>
            {loading && (
              <div className="absolute inset-0 bg-card/40 backdrop-blur-sm grid place-items-center pointer-events-none">
                <span className="text-xs text-muted-foreground mono">Cargando datos…</span>
              </div>
            )}
          </div>
        </div>

        <div className="dense-card p-5 lg:col-span-4">
          <p className="label-eyebrow">Top municipios</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">15 con más estudiantes</h3>
          <ResponsiveContainer width="100%" height={460}>
            <BarChart data={topMun} layout="vertical" margin={{ left: 8 }}>
              <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <YAxis type="category" dataKey="nombre" width={110} tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#0033A0" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dense-card p-5 lg:col-span-12">
          <p className="label-eyebrow">Departamentos</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Estudiantes por departamento</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.por_departamento || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="departamento" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} interval={0} angle={-30} textAnchor="end" height={80} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#FFCD00" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
