import { useState, useEffect, createContext, useContext } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import {
  LayoutDashboard, GraduationCap, Map, History, Upload, Settings, Brain,
  LogOut, Sun, Moon, Filter, ChevronDown, X, Users, BookOpen
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Sheet, SheetContent, SheetTrigger, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";

// -------------- Filters context (global) --------------
const FilterContext = createContext({ filters: {}, setFilter: () => {}, clear: () => {}, opts: {} });
export const useFilters = () => useContext(FilterContext);

const NAV = [
  { to: "/", label: "Ejecutivo", icon: LayoutDashboard, hideForDocente: true },
  { to: "/mi-panel", label: "Mi panel", icon: GraduationCap, onlyDocente: true },
  { to: "/caracterizacion", label: "Caracterización", icon: Users },
  { to: "/academico", label: "Académico", icon: GraduationCap },
  { to: "/territorial", label: "Territorial", icon: Map, hideForDocente: true },
  { to: "/historico", label: "Histórico", icon: History, hideForDocente: true },
  { to: "/insights", label: "Insights IA", icon: Brain, hideForDocente: true },
  { to: "/cargas", label: "Cargas Excel", icon: Upload, admin: true },
  { to: "/grupos", label: "Grupos", icon: BookOpen, admin: true },
  { to: "/admin", label: "Administración", icon: Settings, admin: true },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [theme, setTheme] = useState(() => localStorage.getItem("iud_theme") || "light");
  const [filters, setFilters] = useState({});
  const [opts, setOpts] = useState({});

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("iud_theme", theme);
  }, [theme]);

  useEffect(() => {
    api.get("/dashboards/filters").then((r) => setOpts(r.data)).catch(() => {});
  }, []);

  // user.must_change_password redirect handled by Protected wrapper in App.js

  const setFilter = (k, v) => setFilters((prev) => {
    const next = { ...prev };
    if (v === undefined || v === null || v === "" || v === "all") delete next[k];
    else next[k] = v;
    // Cascade clear: when facultad changes/clears, drop programa & materia.
    // When programa changes/clears, drop materia.
    if (k === "facultad") {
      if (prev.programa && (!v || !((opts.facultad_programa || {})[v] || []).includes(prev.programa))) {
        delete next.programa;
        delete next.materia;
      }
    }
    if (k === "programa") {
      if (prev.materia && prev.programa !== v) delete next.materia;
    }
    return next;
  });
  const clear = () => setFilters({});

  const activeCount = Object.keys(filters).length;
  const isAdmin = user?.role === "superadmin" || user?.role === "admin";
  const isDocente = user?.role === "docente";

  const visibleNav = NAV.filter((n) => {
    if (n.admin && !isAdmin) return false;
    if (n.onlyDocente && !isDocente && user?.role !== "superadmin") return false;
    if (n.hideForDocente && isDocente) return false;
    return true;
  });

  return (
    <FilterContext.Provider value={{ filters, setFilter, clear, opts }}>
      <div className="min-h-screen bg-background text-foreground flex">
        {/* Sidebar */}
        <aside className="hidden lg:flex w-60 flex-col border-r border-border bg-card sticky top-0 h-screen" data-testid="app-sidebar">
          <div className="px-5 py-5 border-b border-border flex items-center gap-3">
            <div className="h-9 w-9 grid place-items-center bg-[#0033A0] text-white rounded">
              <GraduationCap className="w-5 h-5" />
            </div>
            <div>
              <div className="font-display font-black text-sm leading-none">IU Digital</div>
              <div className="label-eyebrow leading-none mt-1">Analítica</div>
            </div>
          </div>
          <nav className="flex-1 py-3 overflow-y-auto">
            {visibleNav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={`nav-${n.label.toLowerCase().replace(/\s+/g, "-")}`}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-5 py-2.5 text-sm transition-soft hover:bg-muted ${isActive ? "nav-active" : "text-foreground/80"}`
                }
              >
                <n.icon className="w-4 h-4" />
                <span>{n.label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="px-5 py-3 border-t border-border">
            <div className="flex items-center gap-2 mb-3">
              <div className="h-8 w-8 grid place-items-center bg-muted rounded text-xs font-bold">
                {(user?.full_name || "U").split(" ").map(p => p[0]).slice(0, 2).join("")}
              </div>
              <div className="min-w-0">
                <div className="text-xs font-medium truncate">{user?.full_name}</div>
                <div className="text-[10px] text-muted-foreground uppercase tracking-widest">{user?.role}</div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} className="h-8 w-8 p-0" data-testid="theme-toggle-btn">
                {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </Button>
              <Button variant="ghost" size="sm" onClick={logout} className="h-8 w-8 p-0" data-testid="logout-btn">
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </aside>

        {/* Main */}
        <div className="flex-1 min-w-0">
          {/* Top bar with filters */}
          <header className="sticky top-0 z-30 bg-card/85 backdrop-blur-xl border-b border-border">
            <div className="flex items-center justify-between px-5 py-3 gap-3">
              <div className="flex items-center gap-3 flex-wrap">
                <Sheet>
                  <SheetTrigger asChild>
                    <Button variant="outline" size="sm" className="rounded-sm" data-testid="open-filters-btn">
                      <Filter className="w-3.5 h-3.5 mr-2" />
                      Filtros
                      {activeCount > 0 && <Badge className="ml-2 h-5 bg-[#0033A0]">{activeCount}</Badge>}
                    </Button>
                  </SheetTrigger>
                  <SheetContent side="left" className="w-[320px]">
                    <FiltersPanel />
                  </SheetContent>
                </Sheet>
                {activeCount > 0 && (
                  <>
                    <Button variant="destructive" size="sm" onClick={clear} className="text-xs rounded-sm h-8" data-testid="clear-filters-btn">
                      <X className="w-3 h-3 mr-1" /> Limpiar filtros ({activeCount})
                    </Button>
                    <span className="text-[10px] text-muted-foreground tracking-widest uppercase hidden md:inline">
                      Los filtros aplican a TODOS los dashboards
                    </span>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                <PeriodSelector />
              </div>
            </div>
            {activeCount > 0 && (
              <div className="px-5 pb-3 flex flex-wrap gap-1.5">
                {Object.entries(filters).map(([k, v]) => (
                  <Badge key={k} variant="outline" className="rounded-sm gap-1 text-[10px] uppercase tracking-wider">
                    {k}: {String(v)}
                    <button onClick={() => setFilter(k, null)} className="hover:text-destructive ml-1" data-testid={`remove-filter-${k}`}>
                      <X className="w-3 h-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </header>
          <main className="p-5 md:p-7" data-testid="main-content">
            <Outlet />
          </main>
        </div>
      </div>
    </FilterContext.Provider>
  );
}

function PeriodSelector() {
  const { filters, setFilter, opts } = useFilters();
  return (
    <Select value={filters.periodo || "all"} onValueChange={(v) => setFilter("periodo", v)}>
      <SelectTrigger className="h-8 w-[140px] rounded-sm text-xs" data-testid="period-select">
        <SelectValue placeholder="Periodo" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">Todos los periodos</SelectItem>
        {(opts.periodos || []).map((p) => (
          <SelectItem key={p} value={p}>{p}</SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function FiltersPanel() {
  const { filters, setFilter, opts, clear } = useFilters();
  // Cascade: if facultad is selected, restrict programas list to that facultad's programs
  const programasFiltrados = filters.facultad && opts.facultad_programa?.[filters.facultad]
    ? opts.facultad_programa[filters.facultad]
    : (opts.programas || []);
  const groups = [
    { key: "facultad", label: "Facultad", list: opts.facultades || [] },
    { key: "programa", label: `Programa${filters.facultad ? ` (${programasFiltrados.length})` : ""}`, list: programasFiltrados },
    { key: "estado_matricula", label: "Estado Matrícula", list: opts.estados_matricula || [] },
    { key: "genero", label: "Género", list: opts.generos || [] },
    { key: "estrato", label: "Estrato", list: opts.estratos || [] },
    { key: "etnia", label: "Grupo étnico", list: opts.etnias || [] },
    { key: "tipo_ubicacion", label: "Ubicación", list: opts.ubicaciones || [] },
  ];
  // Docente + Materia + Grupo (estructura distinta: list de objetos {id, nombre})
  const objectGroups = [
    { key: "docente_id", label: `Docente${(opts.docentes || []).length ? ` (${opts.docentes.length})` : ""}`, list: opts.docentes || [] },
    { key: "materia_id", label: `Materia${(opts.materias || []).length ? ` (${opts.materias.length})` : ""}`, list: opts.materias || [] },
    { key: "codigo_grupo", label: `Grupo${(opts.grupos || []).length ? ` (${opts.grupos.length})` : ""}`, list: opts.grupos || [] },
  ];
  const booleans = [
    { key: "sisben", label: "Beneficiario SISBEN" },
    { key: "discapacidad", label: "Con discapacidad" },
    { key: "victima", label: "Víctima conflicto" },
    { key: "grupo_vulnerable", label: "Grupo vulnerable" },
  ];
  return (
    <div className="h-full flex flex-col">
      <SheetHeader>
        <SheetTitle className="font-display tracking-tight">Filtros globales</SheetTitle>
      </SheetHeader>
      <div className="flex-1 overflow-y-auto mt-4 -mx-6 px-6">
        <Accordion type="multiple" className="w-full">
          {groups.map((g) => (
            <AccordionItem key={g.key} value={g.key}>
              <AccordionTrigger className="text-xs uppercase tracking-widest font-semibold py-3" data-testid={`filter-${g.key}-trigger`}>
                {g.label} {filters[g.key] && <Badge variant="secondary" className="ml-2 h-4 text-[9px]">1</Badge>}
              </AccordionTrigger>
              <AccordionContent>
                <div className="flex flex-col gap-1.5 py-1 max-h-72 overflow-y-auto pr-2">
                  {g.list.length === 0 && <span className="text-xs text-muted-foreground">Sin datos</span>}
                  {g.list.map((v) => (
                    <button
                      key={v}
                      onClick={() => setFilter(g.key, filters[g.key] === v ? null : v)}
                      data-testid={`filter-${g.key}-${v.toString().slice(0, 12)}`}
                      className={`text-left text-xs px-2 py-1.5 rounded transition-soft hover:bg-muted ${filters[g.key] === v ? "bg-[#0033A0]/10 text-[#0033A0] font-medium" : ""}`}
                    >
                      {v}
                    </button>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
          {objectGroups.map((g) => (
            <AccordionItem key={g.key} value={g.key}>
              <AccordionTrigger className="text-xs uppercase tracking-widest font-semibold py-3" data-testid={`filter-${g.key}-trigger`}>
                {g.label} {filters[g.key] && <Badge variant="secondary" className="ml-2 h-4 text-[9px]">1</Badge>}
              </AccordionTrigger>
              <AccordionContent>
                <div className="flex flex-col gap-1.5 py-1 max-h-72 overflow-y-auto pr-2">
                  {g.list.length === 0 && <span className="text-xs text-muted-foreground italic">Aún no hay registros. Cargue datos en "Cargas Excel".</span>}
                  {g.list.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setFilter(g.key, filters[g.key] === v.id ? null : v.id)}
                      data-testid={`filter-${g.key}-${(v.codigo || v.id).toString().slice(0, 14)}`}
                      className={`text-left text-xs px-2 py-1.5 rounded transition-soft hover:bg-muted ${filters[g.key] === v.id ? "bg-[#0033A0]/10 text-[#0033A0] font-medium" : ""}`}
                    >
                      {v.codigo ? <span className="mono text-[10px] mr-2 text-muted-foreground">{v.codigo}</span> : null}
                      {v.nombre}
                    </button>
                  ))}
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
          <AccordionItem value="booleans">
            <AccordionTrigger className="text-xs uppercase tracking-widest font-semibold py-3">
              Vulnerabilidad y enfoques
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-1">
                {booleans.map((b) => (
                  <button
                    key={b.key}
                    onClick={() => setFilter(b.key, filters[b.key] === true ? null : true)}
                    data-testid={`filter-bool-${b.key}`}
                    className={`w-full text-left text-xs px-2 py-1.5 rounded transition-soft hover:bg-muted ${filters[b.key] === true ? "bg-[#E3000F]/10 text-[#E3000F] font-medium" : ""}`}
                  >
                    {b.label} {filters[b.key] === true && "✓"}
                  </button>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
      <Button onClick={clear} variant="outline" className="rounded-sm mt-3" data-testid="filters-clear-btn">
        Limpiar filtros
      </Button>
    </div>
  );
}

export function buildQuery(filters) {
  const params = new URLSearchParams();
  Object.entries(filters || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    params.append(k, String(v));
  });
  return params.toString();
}
