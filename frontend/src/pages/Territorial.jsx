import { useEffect, useState, useMemo } from "react";
import api, { API } from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LTooltip } from "react-leaflet";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Download } from "lucide-react";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function Territorial() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("nacional"); // nacional | internacional | todo

  useEffect(() => {
    setLoading(true);
    api.get(`/dashboards/territorial?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const allMunis = data?.municipios || [];
  const resumen = data?.resumen || {};
  const isColombia = (m) => (m.pais || "").toLowerCase().includes("colombia");
  const munis = useMemo(() => {
    const withCoords = allMunis.filter((m) => m.lat && m.lon);
    if (view === "nacional") return withCoords.filter(isColombia);
    if (view === "internacional") return withCoords.filter((m) => !isColombia(m));
    return withCoords;
  }, [allMunis, view]);

  // Totales de estudiantes por vista (nacional/intl/todo)
  const estudiantesVista = useMemo(() => {
    const src = view === "nacional"
      ? allMunis.filter(isColombia)
      : view === "internacional"
        ? allMunis.filter((m) => !isColombia(m))
        : allMunis;
    return src.reduce((a, m) => a + (m.n || 0), 0);
  }, [allMunis, view]);

  const maxN = useMemo(() => Math.max(1, ...munis.map((m) => m.n)), [munis]);
  const topMun = munis.slice(0, 15);
  const colorFor = (n) => {
    const r = n / maxN;
    if (r > 0.7) return "#E3000F";
    if (r > 0.4) return "#FFCD00";
    if (r > 0.15) return "#0052FF";
    return "#0033A0";
  };

  const mapCenter = view === "internacional" ? [10, -60] : view === "nacional" ? [6.5, -75.0] : [8.0, -75.0];
  const mapZoom = view === "internacional" ? 3 : view === "nacional" ? 5 : 4;

  const downloadExport = (fmt) => {
    const token = localStorage.getItem("iud_token");
    const q = new URLSearchParams(filters);
    q.append("fmt", fmt);
    fetch(`${API}/exports/dashboard/territorial?${q.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `territorial_${new Date().toISOString().slice(0, 10)}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    });
  };

  return (
    <div className="space-y-6" data-testid="territorial-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Dashboard territorial</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Cobertura geográfica</h1>
          <p className="text-sm text-muted-foreground mt-2">
            Distribución por país, departamento y municipio. El mapa muestra <b>{estudiantesVista.toLocaleString("es-CO")}</b> estudiantes con geolocalización DIVIPOLA en la vista <b>{view}</b>.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport("xlsx")} data-testid="territorial-export-xlsx">
            <Download className="w-3.5 h-3.5 mr-2" /> Excel
          </Button>
          <Button variant="outline" size="sm" className="rounded-sm" onClick={() => downloadExport("csv")} data-testid="territorial-export-csv">
            <Download className="w-3.5 h-3.5 mr-2" /> CSV
          </Button>
        </div>
      </header>

      <Tabs value={view} onValueChange={setView}>
        <TabsList className="rounded-sm">
          <TabsTrigger value="nacional" data-testid="terr-view-nacional">🇨🇴 Nacional ({allMunis.filter(isColombia).reduce((a, m) => a + m.n, 0).toLocaleString("es-CO")} est. · {allMunis.filter(isColombia).length} municipios)</TabsTrigger>
          <TabsTrigger value="internacional" data-testid="terr-view-internacional">🌎 Internacional ({allMunis.filter((m) => !isColombia(m)).reduce((a, m) => a + m.n, 0).toLocaleString("es-CO")} est.)</TabsTrigger>
          <TabsTrigger value="todo" data-testid="terr-view-todo">Todo ({resumen.total?.toLocaleString("es-CO") || 0})</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Panel de resumen · cobertura territorial */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <div className="dense-card p-3">
          <p className="label-eyebrow">Total estudiantes</p>
          <p className="kpi-num text-2xl mt-1">{resumen.total?.toLocaleString("es-CO") || "—"}</p>
        </div>
        <div className="dense-card p-3">
          <p className="label-eyebrow">Con georreferencia</p>
          <p className="kpi-num text-2xl mt-1 text-emerald-700">{resumen.con_georef?.toLocaleString("es-CO") || "—"}</p>
          <p className="text-[10px] text-muted-foreground">Mostrables en mapa</p>
        </div>
        <div className="dense-card p-3">
          <p className="label-eyebrow">Sin georreferencia</p>
          <p className="kpi-num text-2xl mt-1 text-amber-700">{resumen.sin_georef?.toLocaleString("es-CO") || "—"}</p>
          <p className="text-[10px] text-muted-foreground">Municipio no en DIVIPOLA</p>
        </div>
        <div className="dense-card p-3">
          <p className="label-eyebrow">Municipios únicos</p>
          <p className="kpi-num text-2xl mt-1">{resumen.n_municipios?.toLocaleString("es-CO") || "—"}</p>
        </div>
        <div className="dense-card p-3">
          <p className="label-eyebrow">Departamentos</p>
          <p className="kpi-num text-2xl mt-1">{resumen.n_departamentos || "—"}</p>
        </div>
        <div className="dense-card p-3">
          <p className="label-eyebrow">Países</p>
          <p className="kpi-num text-2xl mt-1">{resumen.n_paises || "—"}</p>
        </div>
        <div className="dense-card p-3 bg-amber-50/60 border-amber-200">
          <p className="label-eyebrow text-amber-800">Sin dato</p>
          <p className="text-xs mt-1">Ciudad: <b>{resumen.sin_ciudad || 0}</b></p>
          <p className="text-xs">Depto: <b>{resumen.sin_departamento || 0}</b></p>
          <p className="text-xs">País: <b>{resumen.sin_pais || 0}</b></p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-0 overflow-hidden lg:col-span-8" data-testid="territorial-map">
          <div className="p-4 border-b border-border">
            <p className="label-eyebrow">Mapa de calor</p>
            <h3 className="font-display font-bold text-lg tracking-tight">Concentración por municipio · {view === "nacional" ? "Colombia" : view === "internacional" ? "Internacional" : "Mundo"}</h3>
          </div>
          <div className="h-[540px] relative">
            {loading && <div className="absolute inset-0 grid place-items-center z-[1000] bg-card/50"><Skeleton className="h-full w-full" /></div>}
            <ErrorBoundary resetKey={view}>
            <MapContainer key={view} center={mapCenter} zoom={mapZoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom worldCopyJump>
              <TileLayer
                attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
              />
              {munis.map((m, i) => (
                <CircleMarker
                  key={`${view}-${m.codigo}-${i}`}
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
            </ErrorBoundary>
          </div>
        </div>

        <div className="dense-card p-5 lg:col-span-4">
          <p className="label-eyebrow">Top municipios · {view}</p>
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

        <div className="dense-card p-5 lg:col-span-8">
          <p className="label-eyebrow">Departamentos · Colombia</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Estudiantes por departamento</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data?.por_departamento || []}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="departamento" tick={{ fontSize: 9, fill: "hsl(var(--muted-foreground))" }} interval={0} angle={-30} textAnchor="end" height={80} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
              <Bar dataKey="n" fill="#FFCD00" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dense-card p-5 lg:col-span-4">
          <p className="label-eyebrow">País de residencia</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">Distribución por país</h3>
          <div className="space-y-2">
            {(data?.por_pais || []).map((p) => {
              const pct = resumen.total ? (p.n / resumen.total * 100) : 0;
              return (
                <div key={p.pais} className="flex items-center justify-between text-xs py-1 border-b border-border/40 last:border-0">
                  <div>
                    <div className="font-medium">{p.pais}</div>
                    <div className="text-[10px] text-muted-foreground">{pct.toFixed(1)}%</div>
                  </div>
                  <div className="kpi-num text-lg">{p.n.toLocaleString("es-CO")}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
