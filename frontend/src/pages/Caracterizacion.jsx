import { useEffect, useState } from "react";
import api from "@/lib/api";
import { useFilters, buildQuery } from "./AppLayout";
import { ExportButtons } from "./Executive";
import {
  BarChart, Bar, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Users, Wallet, MapPin, Sprout, Heart, Home, Briefcase, Sparkles
} from "lucide-react";

const PALETTE = ["#0033A0", "#0052FF", "#FFCD00", "#E3000F", "#059669", "#8B5CF6", "#F97316", "#0EA5E9"];

function KPI({ label, value, sub, icon: Icon, accent }) {
  return (
    <div className="dense-card p-5" data-testid={`carac-kpi-${label.toLowerCase().replace(/\s+/g, "-")}`}>
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

function HBar({ data, color = "#0033A0", height = 220 }) {
  if (!data || data.length === 0) {
    return <div className="text-xs text-muted-foreground italic py-6">Sin datos</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 12 }}>
        <CartesianGrid horizontal={false} stroke="hsl(var(--border))" />
        <XAxis type="number" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} />
        <YAxis type="category" dataKey="label" width={130} tick={{ fontSize: 10, fill: "hsl(var(--foreground))" }} tickFormatter={(v) => v?.length > 22 ? v.slice(0, 20) + "…" : v} />
        <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 4, fontSize: 12 }} />
        <Bar dataKey="n" fill={color} radius={[0, 2, 2, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

function Donut({ data, height = 220 }) {
  if (!data || data.length === 0) {
    return <div className="text-xs text-muted-foreground italic py-6">Sin datos</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie data={data} dataKey="n" nameKey="label" outerRadius={72} innerRadius={42} paddingAngle={2}>
          {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
        </Pie>
        <Tooltip />
        <Legend verticalAlign="bottom" iconType="square" wrapperStyle={{ fontSize: 10 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

function Block({ title, eyebrow, children, span = "" }) {
  return (
    <div className={`dense-card p-5 ${span}`}>
      <div className="mb-3">
        <p className="label-eyebrow">{eyebrow}</p>
        <h3 className="font-display font-bold text-base tracking-tight">{title}</h3>
      </div>
      {children}
    </div>
  );
}

const fmtMoney = (n) => {
  if (!n || n <= 0) return "$0";
  // Colombian Pesos formatting: no decimals, thousands separator with '.'
  if (n >= 1_000_000) {
    // e.g. 1400000 -> "$1,4 M COP"
    const millones = n / 1_000_000;
    const rounded = millones >= 10 ? millones.toFixed(0) : millones.toFixed(1).replace(".", ",");
    return `$${rounded} M COP`;
  }
  if (n >= 1000) {
    return `$${Math.round(n / 1000)} K COP`;
  }
  return `$${Math.round(n).toLocaleString("es-CO")} COP`;
};

export default function Caracterizacion() {
  const { filters } = useFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.get(`/caracterizacion/overview?${buildQuery(filters)}`)
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  }, [filters]);

  const b = data?.blocks || {};
  const k = data?.kpis || {};
  const total = data?.total || 0;
  const fmt = (n) => (n || 0).toLocaleString("es-CO");

  return (
    <div className="space-y-6" data-testid="caracterizacion-dashboard">
      <header className="flex flex-col md:flex-row md:items-end md:justify-between gap-3">
        <div>
          <p className="label-eyebrow text-[#0033A0]">Caracterización sociodemográfica</p>
          <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Perfil del estudiante</h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
            Vista multidimensional de la base estudiantil. Use los filtros globales para segmentar por facultad, programa, periodo y otras dimensiones.
          </p>
        </div>
        <ExportButtons scope="caracterizacion" filters={filters} />
      </header>

      {/* KPI summary */}
      {loading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-28" />)}
        </div>
      ) : total === 0 ? (
        <div className="dense-card p-8 text-center">
          <p className="text-sm text-muted-foreground">No hay estudiantes con los filtros seleccionados.</p>
        </div>
      ) : (
        <>
          {/* Aviso de matrículas cuando hay filtro por docente o grupo */}
          {data.matriculas_total != null && data.matriculas_total !== total && (
            <div className="dense-card p-3 border-l-4 border-l-[#0033A0] bg-[#0033A0]/5 flex items-start gap-3" data-testid="matriculas-vs-unicos">
              <div className="h-8 w-8 grid place-items-center rounded bg-[#0033A0]/10 text-[#0033A0] text-xs font-bold">
                {data.cursos_count}
              </div>
              <div className="text-xs">
                <p className="font-semibold text-[#0033A0]">
                  {data.matriculas_total} matrículas en {data.cursos_count} curso{data.cursos_count !== 1 ? "s" : ""} · {total} estudiantes únicos
                </p>
                <p className="text-muted-foreground mt-0.5">
                  La diferencia ({data.matriculas_total - total}) corresponde a estudiantes que están matriculados en más de un curso del mismo docente. En caracterización cada persona cuenta una sola vez.
                </p>
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <KPI
              label={data.matriculas_total != null && data.matriculas_total !== total ? "Estudiantes únicos" : "Total filtrado"}
              value={fmt(total)}
              sub={data.matriculas_total != null && data.matriculas_total !== total ? `${data.matriculas_total} matrículas` : "estudiantes"}
              icon={Users}
              accent="bg-[#0033A0]/10 text-[#0033A0]"
            />
            <KPI label="Edad promedio" value={`${k.promedio_edad} años`} sub="grupo seleccionado" icon={Sparkles} accent="bg-purple-500/10 text-purple-700" />
            <KPI label="Ingreso familiar" value={fmtMoney(k.promedio_ingresos)} sub="promedio mensual" icon={Wallet} accent="bg-emerald-500/10 text-emerald-700" />
            <KPI label="Promedio académico" value={(k.promedio_academico ?? 0).toFixed(2)} sub="Escala 0–5" icon={Sparkles} accent="bg-[#FFCD00]/15 text-[#7A6300]" />
            <KPI label="% víctimas" value={`${k.victimas_pct}%`} sub="del conflicto armado" icon={Heart} accent="bg-[#E3000F]/10 text-[#E3000F]" />
            <KPI label="% vulnerables" value={`${k.vulnerables_pct}%`} sub="autoidentificación" icon={Heart} accent="bg-amber-500/10 text-amber-700" />
            <KPI label="% SISBEN" value={`${k.sisben_pct}%`} sub="beneficiarios" icon={Briefcase} accent="bg-blue-500/10 text-blue-700" />
            <KPI label="% rural" value={`${k.rural_pct}%`} sub="ubicación rural/semirural" icon={Sprout} accent="bg-green-600/10 text-green-700" />
          </div>

          <Tabs defaultValue="personal">
            <TabsList className="rounded-sm flex-wrap h-auto">
              <TabsTrigger value="personal" data-testid="carac-tab-personal">Personal</TabsTrigger>
              <TabsTrigger value="socioeconomico" data-testid="carac-tab-socioeconomico">Socioeconómico</TabsTrigger>
              <TabsTrigger value="territorial" data-testid="carac-tab-territorial">Territorial</TabsTrigger>
              <TabsTrigger value="etnico" data-testid="carac-tab-etnico">Étnico y Diferencial</TabsTrigger>
              <TabsTrigger value="vulnerabilidad" data-testid="carac-tab-vulnerabilidad">Vulnerabilidad</TabsTrigger>
              <TabsTrigger value="familiar" data-testid="carac-tab-familiar">Familiar</TabsTrigger>
              <TabsTrigger value="vocacional" data-testid="carac-tab-vocacional">Vocacional</TabsTrigger>
            </TabsList>

            {/* PERSONAL */}
            <TabsContent value="personal" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Block eyebrow="Demografía" title="Género"><Donut data={b.personal?.genero} /></Block>
                <Block eyebrow="Edad" title="Rango etario"><HBar data={b.personal?.rango_edad} color="#0052FF" /></Block>
                <Block eyebrow="Civil" title="Estado civil"><Donut data={b.personal?.estado_civil} /></Block>
                <Block eyebrow="Documento" title="Tipo documento"><HBar data={b.personal?.tipo_documento} color="#8B5CF6" /></Block>
              </div>
            </TabsContent>

            {/* SOCIOECONÓMICO */}
            <TabsContent value="socioeconomico" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <Block eyebrow="Vivienda" title="Estrato"><HBar data={b.socioeconomico?.estrato} color="#FFCD00" /></Block>
                <Block eyebrow="Ingresos" title="Rango ingresos familiares (SMMLV)"><HBar data={b.socioeconomico?.rango_ingresos} color="#059669" /></Block>
                <Block eyebrow="SISBEN" title="Grupo SISBEN (A–D)"><HBar data={b.socioeconomico?.grupo_sisben} color="#0033A0" /></Block>
                <Block eyebrow="SISBEN detalle" title="Nivel SISBEN (A1–D21)" span="lg:col-span-3"><HBar data={b.socioeconomico?.sisben_nivel} color="#E3000F" height={320} /></Block>
                <Block eyebrow="Tenencia" title="Vivienda propia"><Donut data={b.socioeconomico?.vivienda_propia} /></Block>
                <Block eyebrow="Financiera" title="Tiene deuda vivienda"><Donut data={b.socioeconomico?.deuda_vivienda} /></Block>
                <Block eyebrow="Hogar" title="Personas en el hogar"><HBar data={b.socioeconomico?.num_personas_flia?.slice(0, 10)} color="#8B5CF6" /></Block>
              </div>
            </TabsContent>

            {/* TERRITORIAL */}
            <TabsContent value="territorial" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <Block eyebrow="Ubicación" title="Tipo ubicación"><HBar data={b.territorial?.tipo_ubicacion} color="#059669" /></Block>
                <Block eyebrow="Geografía" title="Top 25 departamentos" span="lg:col-span-2"><HBar data={b.territorial?.departamento} color="#0033A0" height={500} /></Block>
                <Block eyebrow="Frontera" title="Zona frontera"><HBar data={b.territorial?.zona_frontera} color="#E3000F" /></Block>
              </div>
            </TabsContent>

            {/* ÉTNICO */}
            <TabsContent value="etnico" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <Block eyebrow="Autoidentificación" title="Etnia"><HBar data={b.etnico_diferencial?.etnia} color="#FFCD00" /></Block>
                <Block eyebrow="Grupo étnico específico" title="Grupo étnico"><HBar data={b.etnico_diferencial?.grupo_etnia} color="#F97316" /></Block>
                <Block eyebrow="Resguardo" title="Vinculación a resguardo"><Donut data={b.etnico_diferencial?.resguardo_indigena} /></Block>
                <Block eyebrow="Inclusión" title="Tiene discapacidad"><Donut data={b.etnico_diferencial?.discapacidad_flag} /></Block>
                <Block eyebrow="Detalle" title="Tipo de discapacidad"><HBar data={b.etnico_diferencial?.discapacidad_tipo} color="#8B5CF6" /></Block>
                <Block eyebrow="Talentos" title="Capacidad excepcional"><HBar data={b.etnico_diferencial?.capacidad_excepcional} color="#059669" /></Block>
              </div>
            </TabsContent>

            {/* VULNERABILIDAD */}
            <TabsContent value="vulnerabilidad" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <Block eyebrow="Vulnerabilidad general" title="Grupo vulnerable"><Donut data={b.vulnerabilidad?.grupo_vulnerable} /></Block>
                <Block eyebrow="Tipología" title="Tipo de vulnerabilidad" span="lg:col-span-2"><HBar data={b.vulnerabilidad?.tipo_grupo_vulnerable} color="#E3000F" height={260} /></Block>
                <Block eyebrow="Conflicto" title="Víctima conflicto armado"><Donut data={b.vulnerabilidad?.victima_conflicto} /></Block>
                <Block eyebrow="Veterano" title="Población veterana"><HBar data={b.vulnerabilidad?.veterano} color="#0033A0" /></Block>
              </div>
            </TabsContent>

            {/* FAMILIAR */}
            <TabsContent value="familiar" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-4">
                <Block eyebrow="Educación" title="Nivel educativo madre"><HBar data={b.familiar?.nivel_educ_madre} color="#FFCD00" height={280} /></Block>
                <Block eyebrow="Educación" title="Nivel educativo padre"><HBar data={b.familiar?.nivel_educ_padre} color="#0052FF" height={280} /></Block>
                <Block eyebrow="Hermanos" title="Hermanos en educación superior"><HBar data={b.familiar?.hnos_educ_superior?.slice(0, 8)} color="#059669" /></Block>
                <Block eyebrow="Contacto" title="Parentesco emergencia"><HBar data={b.familiar?.parentesco_emergencia} color="#8B5CF6" /></Block>
              </div>
            </TabsContent>

            {/* VOCACIONAL */}
            <TabsContent value="vocacional" className="mt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <Block eyebrow="Motivación" title="Razón elección de carrera"><HBar data={b.vocacional?.razon_carrera} color="#0033A0" /></Block>
                <Block eyebrow="Institución" title="Por qué eligió IU Digital"><HBar data={b.vocacional?.razon_institucion} color="#FFCD00" /></Block>
                <Block eyebrow="Reconocimientos" title="Tiene distinciones"><Donut data={b.vocacional?.tiene_distinciones} /></Block>
                <Block eyebrow="Tiempo libre" title="Hobbies (categorizado)"><HBar data={b.vocacional?.hobbies} color="#F97316" /></Block>
                <Block eyebrow="Extracurricular" title="Actividades (categorizado)"><HBar data={b.vocacional?.actividades} color="#059669" /></Block>
                <Block eyebrow="Nota" title="Sobre categorización">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Los campos de texto libre (hobbies, actividades, motivaciones) son procesados automáticamente con análisis de palabras clave para clasificarlos en categorías agregables. Estudiantes pueden aparecer en múltiples categorías.
                  </p>
                </Block>
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
