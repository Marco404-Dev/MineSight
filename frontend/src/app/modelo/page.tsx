"use client";

import { Braces, Network, PanelsTopLeft, Scaling } from "lucide-react";
import { DataTable } from "@/components/data-table";
import { PageHeading, Status, WithModel } from "@/components/shell";
import { Card, CardTitle } from "@/components/ui/card";

const STAGES = [
  { name: "Next.js", detail: "Recibe las mediciones y presenta los resultados de la API.", icon: PanelsTopLeft },
  { name: "FastAPI", detail: "Valida la solicitud y conserva el orden de las siete variables.", icon: Braces },
  { name: "StandardScaler", detail: "Estandariza las entradas con las medias y desviaciones del entrenamiento.", icon: Scaling },
  { name: "K-Means", detail: "Asigna la operación al centroide más cercano por distancia euclidiana.", icon: Network },
];

export default function ModelPage() {
  return <>
    <PageHeading label="Clustering no supervisado" title="Método y alcance" detail="MineSight agrupa operaciones similares de flotación de hierro. Proyecto de la UPCH para el Challenge 4 de Clustering y Segmentación." />
    <div className="space-y-4">
      <Card>
        <CardTitle>De la medición al cluster</CardTitle>
        <ol className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {STAGES.map(({ name, detail, icon: Icon }) => <li key={name} className="border-l-2 border-primary/45 bg-[#0d1826] p-4">
            <div className="flex items-center gap-2 text-sm font-semibold"><Icon size={17} className="text-primary" />{name}</div>
            <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
          </li>)}
        </ol>
      </Card>
      <WithModel>{model => <>
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {[
            ["Silhouette", model.metrics.silhouette.toFixed(4)],
            ["Davies–Bouldin", model.metrics.davies_bouldin.toFixed(4)],
            ["Calinski–Harabasz", model.metrics.calinski_harabasz.toFixed(4)],
            ["PCA histórico (2 CP)", (model.metrics.pca_variance * 100).toFixed(2) + " %"],
          ].map(([label, value]) => <Card key={label}>
            <div className="text-xl font-bold text-primary tabular-nums sm:text-3xl">{value}</div>
            <p className="mt-1 text-xs text-muted-foreground sm:text-sm">{label}</p>
          </Card>)}
        </div>
        <div className="grid gap-4 xl:grid-cols-2">
          <Card className="space-y-3">
            <CardTitle>{model.benchmark.winner} frente a {model.benchmark.alternative}</CardTitle>
            <p className="text-sm text-muted-foreground">El notebook documenta el mejor algoritmo por criterio. Se dispone de la comparación relativa.</p>
            <DataTable label="Comparación de algoritmos" data={{
              columns: ["Métrica", "Mejor resultado"],
              rows: model.benchmark.metrics.map(metric => [metric, model.benchmark.winner]),
            }} />
          </Card>
          <Card>
            <CardTitle>Estabilidad ante inicializaciones</CardTitle>
            <p className="mt-2 text-sm text-muted-foreground">El ARI indica cuánto coinciden dos agrupaciones. El valor 1 representa concordancia perfecta.</p>
            <div className="mt-4 text-3xl font-bold text-sky-300 tabular-nums">{model.metrics.ari.toFixed(4)}</div>
            <meter aria-label="ARI promedio" className="mt-2 block h-3 w-full accent-sky-400" min={-1} max={1} value={model.metrics.ari} />
            <div className="mt-1 flex justify-between text-xs text-muted-foreground"><span>−1</span><span>0</span><span>1</span></div>
          </Card>
        </div>
      </>}</WithModel>
      <Card className="space-y-3">
        <CardTitle>Interpretación minera</CardTitle>
        <p className="text-sm text-muted-foreground">El entrenamiento empleó promedios horarios de Quality Prediction in a Mining Process. Los grupos fueron estables ante cambios de inicialización, con separación limitada entre centroides.</p>
        <Status>Los clusters representan similitud con perfiles históricos. Su uso es exploratorio y carece de validación como diagnóstico de fallas, indicador de riesgo, recomendación de dosificación o estimación de calidad.</Status>
      </Card>
    </div>
  </>;
}
