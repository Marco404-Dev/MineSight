"use client";

import { Activity, LoaderCircle } from "lucide-react";
import { useState, type FormEvent } from "react";
import { CompareChart, ProfileRadar } from "@/components/charts";
import { DataTable } from "@/components/data-table";
import { PageHeading, Status, WithModel } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { COLORS, message, number, request, type ModelInfo, type Prediction } from "@/lib/api";

const GROUPS = [
  { name: "Alimentación", indices: [0, 1] },
  { name: "Dosificación", indices: [2, 3] },
  { name: "Pulpa", indices: [4, 5, 6] },
];

export default function PredictionPage() {
  return <>
    <PageHeading label="Segmentación individual" title="Predicción manual" detail="Identifica el perfil histórico más cercano a una operación de flotación." />
    <WithModel>{model => <PredictionForm model={model} />}</WithModel>
  </>;
}

function PredictionForm({ model }: { model: ModelInfo }) {
  const [values, setValues] = useState(() => model.means.map(String));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Prediction | null>(null);
  const [feature, setFeature] = useState(0);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError("");
    setResult(null);
    const parsed = values.map(value => Number(value.replace(",", ".")));
    if (values.some(value => !value.trim()) || parsed.some(value => !Number.isFinite(value))) {
      setError("Completa los siete campos con valores numéricos finitos.");
      return;
    }
    setBusy(true);
    try {
      setResult(await request<Prediction>("/api/predict", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(model.input_keys.map((key, index) => [key, parsed[index]]))),
      }));
    } catch (error) { setError(message(error)); }
    finally { setBusy(false); }
  }

  return <div className="space-y-4">
    <Card>
      <CardTitle>Condición operativa</CardTitle>
      <p className="mt-1 text-sm text-muted-foreground">Los campos contienen las medias históricas. Para evaluar una operación, usa las siete mediciones de una misma hora y sus unidades originales.</p>
      <form onSubmit={submit} className="mt-5 space-y-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {GROUPS.map(group => <fieldset key={group.name} disabled={busy} className="rounded-xl border border-border px-3.5 pb-4">
            <legend className="px-1 text-sm font-semibold text-[#ffd2ae]">{group.name}</legend>
            {group.indices.map(index => <label key={index} className="mt-3 block text-sm">{model.features[index]}
              <input className="field mt-1 tabular-nums" type="text" inputMode="decimal" required autoComplete="off"
                value={values[index]} onChange={event => {
                  const value = event.target.value;
                  setValues(previous => previous.map((item, i) => i === index ? value : item));
                  setResult(null);
                }} />
              <span className="mt-1 block text-xs text-muted-foreground">Media histórica · {number(model.means[index])}</span>
            </label>)}
          </fieldset>)}
        </div>
        <Button type="submit" disabled={busy}>{busy ? <LoaderCircle className="animate-spin" /> : <Activity />}
          {busy ? "Calculando cluster…" : "Asignar cluster"}
        </Button>
      </form>
    </Card>
    {error && <Status kind="error">{error}</Status>}
    {result && <PredictionResult model={model} result={result} feature={feature} onFeature={setFeature} />}
  </div>;
}

function PredictionResult({ model, result, feature, onFeature }: {
  model: ModelInfo; result: Prediction; feature: number; onFeature: (value: number) => void;
}) {
  const color = COLORS[result.cluster];
  const distances = [...result.distances].sort((a, b) => a.distance - b.distance);
  const maxDistance = distances.at(-1)?.distance || 1;
  return <>
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <Card className="border-l-4" style={{ borderLeftColor: color }}>
        <p className="text-xs font-bold uppercase tracking-widest" style={{ color }}>Cluster asignado</p>
        <h2 className="mt-1 text-4xl font-bold" style={{ color }}>Cluster {result.cluster}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{number(result.historical_hours)} horas históricas en el grupo. El modelo comparó las siete variables estandarizadas.</p>
        <h3 className="mt-5 border-t border-border pt-4 text-base font-semibold">Por qué se asignó este cluster</h3>
        <p className="mt-1 text-sm text-muted-foreground">Menor distancia indica mayor similitud.</p>
        <ol aria-label="Distancias a los centroides" className="mt-3 space-y-2">
          {distances.map(item => <li key={item.cluster} className="grid grid-cols-[5.3rem_minmax(0,1fr)_3.5rem] items-center gap-2 text-xs sm:text-sm">
            <span className={item.cluster === result.cluster ? "font-bold" : "text-muted-foreground"}>Cluster {item.cluster}</span>
            <span aria-hidden className="h-2 overflow-hidden rounded bg-[#24374d]"><span className="block h-full rounded" style={{
              width: (item.distance * 100 / maxDistance) + "%", backgroundColor: COLORS[item.cluster],
            }} /></span>
            <span className="text-right font-mono tabular-nums">{number(item.distance)}</span>
          </li>)}
        </ol>
      </Card>
      <Card>
        <CardTitle>Operación frente al centroide</CardTitle>
        <p className="mt-1 text-sm text-muted-foreground">0σ es la media histórica de cada variable.</p>
        <ProfileRadar vectors={[
          { label: "Cluster " + result.cluster, color, values: result.center_z },
          { label: "Operación ingresada", color: "#F8FAFC", values: result.z },
        ]} />
      </Card>
    </div>
    <Card className="space-y-4">
      <CardTitle>Perfil del cluster {result.cluster}</CardTitle>
      <ul className="space-y-1 text-sm text-muted-foreground">
        {result.descriptors.map(item => <li key={item.feature}><strong className="text-foreground">{item.feature}</strong> · {number(Math.abs(item.z))}σ {item.z < 0 ? "por debajo" : "por encima"} de la media histórica.</li>)}
      </ul>
      <DataTable label="Comparación en unidades originales" data={{
        columns: ["Variable", "Entrada", "Centroide", "Media histórica"],
        rows: model.features.map((name, index) => [name, result.values[index], result.center[index], model.means[index]]),
      }} />
      <label className="block max-w-sm text-sm">Variable para comparar los siete centroides
        <select className="field mt-1" value={feature} onChange={event => onFeature(Number(event.target.value))}>
          {model.features.map((name, i) => <option key={name} value={i}>{name}</option>)}
        </select>
      </label>
      <p className="text-sm text-muted-foreground">La línea punteada marca el valor ingresado para esta variable.</p>
      <CompareChart selected={result.values[feature]} data={model.clusters.map(item => ({ cluster: item.cluster, value: item.center[feature] }))} />
    </Card>
  </>;
}
