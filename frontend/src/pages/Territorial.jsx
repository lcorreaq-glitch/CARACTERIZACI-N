import { useEffect, useState, useMemo, useRef } from "react";
import api, { API } from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import { MapContainer, TileLayer, CircleMarker, Tooltip as LTooltip, useMap } from "react-leaflet";
import { BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Download, Search, MapPin, X, Info } from "lucide-react";
import ErrorBoundary from "@/components/ErrorBoundary";

// Componente auxiliar para hacer fly-to al buscar un municipio
function MapFly({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target?.lat && target?.lon) {
      map.flyTo([target.lat, target.lon], 10, { duration: 1.2 });
    }
  }, [target, map]);
  return null;
}

export default function Territorial() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("nacional");
  // Nuevos filtros locales del mapa
  const [pais, setPais] = useState("all");
  const [departamento, setDepartamento] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedMuni, setSelectedMuni] = useState(null);

  useEffect(() => {
    setLoading(true);
    api.get(`/dashboards/territorial?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const allMunis = data?.municipios || [];
  const resumen = data?.resumen || {};
  const isColombia = (m) => (m.pais || "").toLowerCase().includes("colombia");

  // Opciones para los selectores locales
  const paisesUnicos = useMemo(() => {
    const s = new Set();
    allMunis.forEach((m) => m.pais && s.add(m.pais));
    return Array.from(s).sort();
  }, [allMunis]);

  const departamentosUnicos = useMemo(() => {
    const s = new Set();
    allMunis.forEach((m) => {
      if (m.departamento && (pais === "all" || m.pais === pais)) s.add(m.departamento);
    });
    return Array.from(s).sort();
  }, [allMunis, pais]);

  // Municipios filtrados aplicando vista + filtros locales + búsqueda
  const munis = useMemo(() => {
    let filtered = allMunis.filter((m) => m.lat && m.lon);
    if (view === "nacional") filtered = filtered.filter(isColombia);
    else if (view === "internacional") filtered = filtered.filter((m) => !isColombia(m));
    if (pais !== "all") filtered = filtered.filter((m) => m.pais === pais);
    if (departamento !== "all") filtered = filtered.filter((m) => m.departamento === departamento);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      filtered = filtered.filter((m) =>
        (m.nombre || "").toLowerCase().includes(q) ||
        (m.departamento || "").toLowerCase().includes(q) ||
        (m.pais || "").toLowerCase().includes(q)
      );
    }
    return filtered;
  }, [allMunis, view, pais, departamento, search]);

  const estudiantesVista = useMemo(
    () => munis.reduce((a, m) => a + (m.n || 0), 0),
    [munis]
  );
  const promedioPonderadoVista = useMemo(() => {
    let sumN = 0, sumProm = 0;
    munis.forEach((m) => {
      if (m.prom > 0 && m.n) { sumN += m.n; sumProm += m.prom * m.n; }
    });
    return sumN ? (sumProm / sumN) : 0;
  }, [munis]);

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

  const clearFilters = () => { setPais("all"); setDepartamento("all"); setSearch(""); setSelectedMuni(null); };
  const hasLocalFilter = pais !== "all" || departamento !== "all" || search.trim() !== "";

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

  // Sugerencias de búsqueda (matches parciales)
  const suggestions = useMemo(() => {
    if (!search.trim() || search.trim().length < 2) return [];
    const q = search.trim().toLowerCase();
    return allMunis
      .filter((m) => m.lat && m.lon && (m.nombre || "").toLowerCase().includes(q))
      .slice(0, 8);
  }, [allMunis, search]);

  return (
    <div className="space-y-6" data-testid="territorial-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Dashboard territorial</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Cobertura geográfica</h1>
          <p className="text-sm text-muted-foreground mt-2">
            El mapa muestra <b>{estudiantesVista.toLocaleString("es-CO")}</b> estudiantes con geolocalización DIVIPOLA en <b>{munis.length}</b> municipios visibles.
            {promedioPonderadoVista > 0 && <> · Promedio ponderado <b>{promedioPonderadoVista.toFixed(2)}</b>.</>}
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

      <Tabs value={view} onValueChange={(v) => { setView(v); setPais("all"); setDepartamento("all"); }}>
        <TabsList className="rounded-sm">
          <TabsTrigger value="nacional" data-testid="terr-view-nacional">Nacional</TabsTrigger>
          <TabsTrigger value="internacional" data-testid="terr-view-internacional">Internacional</TabsTrigger>
          <TabsTrigger value="todo" data-testid="terr-view-todo">Todo</TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Panel de resumen */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <KPI label="Total estudiantes" v={resumen.total} />
        <KPI label="Con georreferencia" v={resumen.con_georef} accent="text-emerald-700" />
        <KPI label="Sin georreferencia" v={resumen.sin_georef} accent="text-amber-700" sub="Municipio no en DIVIPOLA" />
        <KPI label="Municipios únicos" v={resumen.n_municipios} />
        <KPI label="Departamentos" v={resumen.n_departamentos} />
        <KPI label="Países" v={resumen.n_paises} />
      </div>

      {/* Filtros locales del mapa */}
      <div className="dense-card p-4 border-l-4 border-l-[#0033A0]" data-testid="map-filters">
        <div className="flex items-center gap-2 mb-3">
          <MapPin className="w-4 h-4 text-[#0033A0]" />
          <p className="label-eyebrow text-[#0033A0]">Filtros del mapa</p>
          {hasLocalFilter && (
            <Button variant="ghost" size="sm" className="h-7 text-xs ml-auto" onClick={clearFilters} data-testid="clear-map-filters">
              <X className="w-3 h-3 mr-1" /> Limpiar filtros
            </Button>
          )}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground z-10" />
            <Input
              placeholder="Buscar municipio por nombre…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="rounded-sm pl-9"
              data-testid="map-search"
            />
            {suggestions.length > 0 && search.length >= 2 && !selectedMuni && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-sm shadow-lg z-[500] max-h-64 overflow-y-auto">
                {suggestions.map((m, i) => (
                  <button
                    key={`${m.codigo}-${i}`}
                    onClick={() => { setSelectedMuni(m); setSearch(m.nombre); }}
                    className="w-full text-left px-3 py-2 hover:bg-muted transition-soft border-b border-border/40 last:border-0"
                    data-testid={`sugg-${m.codigo}`}
                  >
                    <div className="text-xs font-medium">{m.nombre}</div>
                    <div className="text-[10px] text-muted-foreground flex justify-between">
                      <span>{m.departamento} · {m.pais}</span>
                      <span>{m.n} est · prom {m.prom?.toFixed(2)}</span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <Select value={pais} onValueChange={(v) => { setPais(v); setDepartamento("all"); }}>
            <SelectTrigger className="rounded-sm" data-testid="filter-pais"><SelectValue placeholder="País" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los países ({paisesUnicos.length})</SelectItem>
              {paisesUnicos.map((p) => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={departamento} onValueChange={setDepartamento} disabled={pais === "all" && departamentosUnicos.length > 40}>
            <SelectTrigger className="rounded-sm" data-testid="filter-departamento"><SelectValue placeholder="Departamento" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los depto. ({departamentosUnicos.length})</SelectItem>
              {departamentosUnicos.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="text-xs text-muted-foreground flex items-center px-2">
            <b>{munis.length}</b>&nbsp;municipios visibles · <b className="ml-1">{estudiantesVista.toLocaleString("es-CO")}</b>&nbsp;estudiantes
          </div>
        </div>
        {selectedMuni && (
          <div className="mt-3 flex items-center gap-3 border-t border-border pt-3">
            <Badge className="rounded-sm bg-[#0033A0]">{selectedMuni.nombre}</Badge>
            <span className="text-xs text-muted-foreground">
              {selectedMuni.departamento} · {selectedMuni.pais} · <b>{selectedMuni.n}</b> estudiantes · promedio <b>{selectedMuni.prom?.toFixed(2)}</b>
            </span>
            <Button variant="ghost" size="sm" className="h-7 text-xs ml-auto" onClick={() => setSelectedMuni(null)}>
              <X className="w-3 h-3 mr-1" /> Deseleccionar
            </Button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-0 overflow-hidden lg:col-span-8" data-testid="territorial-map">
          <div className="p-4 border-b border-border">
            <div className="flex items-center justify-between">
              <div>
                <p className="label-eyebrow">Mapa de calor</p>
                <h3 className="font-display font-bold text-lg tracking-tight">
                  Concentración por municipio · {view === "nacional" ? "Colombia" : view === "internacional" ? "Internacional" : "Mundo"}
                </h3>
              </div>
              <div className="flex items-center gap-1 text-[10px] text-muted-foreground">
                <Info className="w-3 h-3" />
                <span>El tamaño del círculo es proporcional a #estudiantes. El color indica concentración relativa.</span>
              </div>
            </div>
          </div>
          <div className="h-[540px] relative">
            {loading && <div className="absolute inset-0 grid place-items-center z-[1000] bg-card/50"><Skeleton className="h-full w-full" /></div>}
            <ErrorBoundary resetKey={view}>
              <MapContainer key={view} center={mapCenter} zoom={mapZoom} style={{ height: "100%", width: "100%" }} scrollWheelZoom worldCopyJump>
                <TileLayer
                  attribution='&copy; <a href="https://carto.com/">CARTO</a>'
                  url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                />
                {selectedMuni && <MapFly target={selectedMuni} />}
                {munis.map((m, i) => {
                  const isSelected = selectedMuni?.codigo === m.codigo;
                  return (
                    <CircleMarker
                      key={`${view}-${m.codigo}-${i}`}
                      center={[m.lat, m.lon]}
                      radius={isSelected ? 20 : Math.max(4, Math.min(24, Math.sqrt(m.n) * 1.3))}
                      pathOptions={{
                        color: isSelected ? "#E3000F" : colorFor(m.n),
                        fillColor: isSelected ? "#E3000F" : colorFor(m.n),
                        fillOpacity: isSelected ? 0.85 : 0.55,
                        weight: isSelected ? 3 : 1,
                      }}
                      eventHandlers={{ click: () => setSelectedMuni(m) }}
                    >
                      <LTooltip>
                        <div className="text-xs">
                          <div className="font-bold text-[#0033A0]">{m.nombre}</div>
                          <div className="text-muted-foreground">{m.departamento} · {m.pais}</div>
                          <hr className="my-1" />
                          <div><b>{m.n?.toLocaleString("es-CO")}</b> estudiantes</div>
                          <div>Promedio académico: <b>{m.prom > 0 ? m.prom.toFixed(2) : "sin datos"}</b></div>
                          <div className="text-[10px] text-muted-foreground italic">
                            {m.prom > 0 ? `Ponderado sobre ${m.n} estudiantes con notas` : "Sin notas cargadas"}
                          </div>
                          <hr className="my-1" />
                          <div>Vulnerables: <b>{m.vulnerables || 0}</b> ({m.n ? Math.round((m.vulnerables || 0) / m.n * 100) : 0}%)</div>
                          <div>Rural: <b>{m.rural || 0}</b> ({m.n ? Math.round((m.rural || 0) / m.n * 100) : 0}%)</div>
                        </div>
                      </LTooltip>
                    </CircleMarker>
                  );
                })}
              </MapContainer>
            </ErrorBoundary>
          </div>
        </div>

        <div className="dense-card p-5 lg:col-span-4">
          <p className="label-eyebrow">Top municipios · {hasLocalFilter ? "filtrado" : view}</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-3">
            {Math.min(15, topMun.length)} con más estudiantes
          </h3>
          {topMun.length === 0 ? (
            <div className="text-center text-xs text-muted-foreground py-12">
              Sin resultados con los filtros actuales
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={460}>
              <BarChart data={topMun} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
                <YAxis
                  type="category"
                  dataKey="nombre"
                  width={110}
                  tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }}
                  onClick={(e) => {
                    const m = topMun.find((x) => x.nombre === e.value);
                    if (m) setSelectedMuni(m);
                  }}
                />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }}
                  formatter={(v) => [`${v.toLocaleString("es-CO")} estudiantes`, ""]}
                />
                <Bar dataKey="n" fill="#0033A0" radius={[0, 2, 2, 0]} onClick={(d) => setSelectedMuni(d.payload)} cursor="pointer" />
              </BarChart>
            </ResponsiveContainer>
          )}
          <p className="text-[10px] text-muted-foreground mt-2 italic text-center">Haga clic en una barra para centrar el mapa.</p>
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
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {(data?.por_pais || []).map((p) => {
              const pct = resumen.total ? (p.n / resumen.total * 100) : 0;
              return (
                <button
                  key={p.pais}
                  onClick={() => { setPais(p.pais); setView("todo"); }}
                  className="w-full flex items-center justify-between text-xs py-1 border-b border-border/40 last:border-0 hover:bg-muted/60 px-2 -mx-2 rounded-sm text-left"
                  data-testid={`pais-${p.pais}`}
                >
                  <div>
                    <div className="font-medium">{p.pais}</div>
                    <div className="text-[10px] text-muted-foreground">{pct.toFixed(1)}%</div>
                  </div>
                  <div className="kpi-num text-lg">{p.n.toLocaleString("es-CO")}</div>
                </button>
              );
            })}
          </div>
          <p className="text-[10px] text-muted-foreground mt-2 italic">Clic en un país para filtrar el mapa.</p>
        </div>
      </div>
    </div>
  );
}

function KPI({ label, v, accent, sub }) {
  return (
    <div className="dense-card p-3">
      <p className="label-eyebrow">{label}</p>
      <p className={`kpi-num text-2xl mt-1 ${accent || ""}`}>{v?.toLocaleString("es-CO") || "—"}</p>
      {sub && <p className="text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  );
}
