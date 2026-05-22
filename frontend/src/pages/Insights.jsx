import { useState } from "react";
import api from "@/lib/api";
import { useFilters } from "./AppLayout";
import { Button } from "@/components/ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Sparkles, Brain, Loader2 } from "lucide-react";

const SCOPES = [
  { v: "ejecutivo", label: "Resumen ejecutivo" },
  { v: "academico", label: "Análisis académico" },
  { v: "territorial", label: "Análisis territorial" },
  { v: "historico", label: "Tendencias históricas" },
];

export default function Insights() {
  const { filters } = useFilters();
  const [scope, setScope] = useState("ejecutivo");
  const [question, setQuestion] = useState("");
  const [insight, setInsight] = useState(null);
  const [loading, setLoading] = useState(false);

  const run = async () => {
    setLoading(true);
    setInsight(null);
    try {
      const r = await api.post("/ai/insights", { scope, filters, question: question || null });
      setInsight(r.data);
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Error generando insight");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="insights-page">
      <header>
        <p className="label-eyebrow text-[#0033A0]">Insights IA · GPT-5.4</p>
        <h1 className="font-display font-black text-3xl md:text-4xl tracking-tighter mt-1">Análisis inteligente</h1>
        <p className="text-sm text-muted-foreground mt-2 max-w-2xl">
          Resúmenes ejecutivos, hallazgos y recomendaciones generadas con IA usando los datos filtrados.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="dense-card p-5 lg:col-span-5">
          <p className="label-eyebrow mb-2">Configuración</p>
          <h3 className="font-display font-bold text-lg tracking-tight mb-4">Generar insight</h3>

          <label className="text-xs uppercase tracking-widest font-medium mb-2 block">Ámbito</label>
          <Select value={scope} onValueChange={setScope}>
            <SelectTrigger className="rounded-sm mb-4" data-testid="insight-scope-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SCOPES.map((s) => <SelectItem key={s.v} value={s.v}>{s.label}</SelectItem>)}
            </SelectContent>
          </Select>

          <label className="text-xs uppercase tracking-widest font-medium mb-2 block">Pregunta opcional</label>
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="¿Cuáles programas tienen mayor riesgo de deserción según estos datos?"
            className="rounded-sm mb-4 min-h-[100px]"
            data-testid="insight-question-input"
          />

          <Button onClick={run} disabled={loading} className="w-full rounded-sm bg-[#0033A0] hover:bg-[#002A85] text-white" data-testid="insight-generate-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Sparkles className="w-4 h-4 mr-2" /> Generar insight</>}
          </Button>

          <p className="text-[10px] text-muted-foreground mt-4 leading-relaxed">
            La IA usa una agregación resumida de tus datos filtrados. Ninguna información personal individual se envía al modelo.
          </p>
        </div>

        <div className="dense-card p-5 lg:col-span-7 min-h-[400px]" data-testid="insight-result">
          <div className="flex items-center gap-2 mb-4">
            <Brain className="w-4 h-4 text-[#0033A0]" />
            <p className="label-eyebrow">Resultado</p>
          </div>
          {loading && <div className="space-y-3"><Skeleton className="h-4 w-3/4" /><Skeleton className="h-4 w-full" /><Skeleton className="h-4 w-5/6" /><Skeleton className="h-4 w-2/3" /></div>}
          {!loading && !insight && (
            <div className="text-sm text-muted-foreground italic">Configure el ámbito y presione "Generar insight" para obtener un análisis ejecutivo.</div>
          )}
          {insight && (
            <article className="prose prose-sm max-w-none dark:prose-invert">
              <p className="label-eyebrow !mb-2">Ámbito: {insight.scope}</p>
              <div className="whitespace-pre-wrap text-sm leading-relaxed" data-testid="insight-text">{insight.insight}</div>
            </article>
          )}
        </div>
      </div>
    </div>
  );
}
