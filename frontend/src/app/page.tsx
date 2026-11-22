"use client";

import Link from "next/link";
import { Activity, Clock3, Database, FileUp, Network, SlidersHorizontal } from "lucide-react";
import { animate, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { CompareChart, DistributionChart, ProfileRadar } from "@/components/charts";
import { WithModel, useWorkspace } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { COLORS, number } from "@/lib/api";

function Counter({ value }: { value: number }) {
  const reduced = useReducedMotion();
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    if (reduced) return;
    const control = animate(0, value, { duration: .65, ease: "easeOut", onUpdate: item => setDisplay(Math.round(item)) });
    return () => control.stop();
  }, [value, reduced]);
  return <><span aria-hidden>{number(reduced ? value : display)}</span><span className="sr-only">{number(value)}</span></>;
}

export default function Dashboard() {
  const { sessionCount } = useWorkspace();
  const [feature, setFeature] = useState(0);
  const [groups, setGroups] = useState([0, 1, 6]);
  return <div className="space-y-6">
    <header className="flex flex-wrap items-end justify-between gap-5 border-b border-border pb-5">
      <div>
        <p className="text-xs font-bold tracking-[.16em] text-primary uppercase">Flotación de mineral de hierro</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-5xl">Inteligencia operativa</h1>
        <p className="mt-2 text-sm text-muted-foreground sm:text-base">Explora los patrones de operación de la planta y compara tus mediciones.</p>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" asChild><Link href="/prediccion"><SlidersHorizontal />Probar una operación</Link></Button>
        <Button asChild><Link href="/analisis"><FileUp />Analizar CSV</Link></Button>
      </div>
    </header>
    <WithModel>{model => {
      const mostFrequent = model.clusters.reduce((best, item) => item.count > best.count ? item : best);
      return <>
        <section aria-label="Indicadores operativos" className="grid grid-cols-2 overflow-hidden rounded-xl border border-border bg-[#0e1928] lg:grid-cols-4">
          {[
            { label: "Registros originales", value: model.original_records, icon: Database },
            { label: "Horas de entrenamiento", value: model.training_hours, icon: Clock3 },
            { label: "Clusters identificados", value: model.clusters.length, icon: Network },
            { label: "Operaciones en sesión", value: sessionCount, icon: Activity },
          ].map(({ label, value, icon: Icon }, i) => <div key={label} className="border-border px-4 py-4 odd:border-r max-lg:nth-[-n+2]:border-b sm:px-6 lg:[&:not(:last-child)]:border-r">
            <div className="flex items-center gap-2 text-xs text-muted-foreground sm:text-sm"><Icon size={16} className={i === 3 ? "text-sky-300" : "text-primary"} />{label}</div>
            <div className="mt-2 font-mono text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl"><Counter value={value} /></div>
          </div>)}
        </section>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.8fr)_minmax(0,1fr)]">
          <Card className="!rounded-xl">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><CardTitle>Distribución histórica</CardTitle><p className="mt-1 text-sm text-muted-foreground">Operaciones horarias por cluster.</p></div>
              <span className="rounded-md border border-sky-400/25 bg-sky-400/10 px-2.5 py-1 font-mono text-xs text-sky-200">Entrenamiento</span>
            </div>
            <div className="mt-5"><DistributionChart data={model.clusters} /></div>
            <div className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-border pt-3 text-sm text-muted-foreground">
              <span aria-hidden className="size-2.5 rounded-full" style={{ background: COLORS[mostFrequent.cluster] }} />
              <strong className="text-foreground">Cluster {mostFrequent.cluster}</strong>
              <span>es el más frecuente · {number(mostFrequent.count)} horas ({number(mostFrequent.share)} %)</span>
            </div>
          </Card>
          <Card className="relative isolate flex min-h-72 flex-col justify-between overflow-hidden !rounded-xl bg-[#102232]">
            <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
              <div className="hero-grid absolute inset-0 opacity-40" />
              <div className="absolute inset-x-0 top-14 bottom-9 bg-[url('/flotacion.svg')] bg-contain bg-center bg-no-repeat opacity-90" />
              <div className="hero-beam absolute top-1/2 right-0 w-full" />
            </div>
            <div><CardTitle>Planta de flotación</CardTitle><p className="mt-1 text-sm text-muted-foreground">Referencia del proceso estudiado.</p></div>
            <Link href="/modelo" className="self-start rounded-md border border-border bg-[#0b1828] px-3 py-2 text-sm font-medium text-sky-200 hover:border-sky-400">Conocer el modelo</Link>
          </Card>
        </div>
        <section aria-label="Comparación de perfiles" className="grid gap-4 xl:grid-cols-2">
          <Card className="!rounded-xl">
            <CardTitle>Perfil multivariable</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Centroides estandarizados. 0σ representa la media histórica.</p>
            <div role="group" aria-label="Clusters en el radar" className="mt-4 flex flex-wrap gap-1.5">
              {model.clusters.map(({ cluster }) => <button key={cluster} type="button" aria-pressed={groups.includes(cluster)}
                aria-label={"Cluster " + cluster} onClick={() => setGroups(previous => previous.includes(cluster) ? previous.filter(item => item !== cluster) : [...previous, cluster])}
                className="rounded-md border border-border bg-[#101b2a] px-2.5 py-1.5 font-mono text-xs aria-pressed:border-current aria-pressed:bg-[#1b2b40]"
                style={{ color: COLORS[cluster] }}>{cluster}</button>)}
            </div>
            {groups.length ? <ProfileRadar vectors={model.clusters.filter(item => groups.includes(item.cluster)).map(item => ({
              label: "Cluster " + item.cluster, color: COLORS[item.cluster], values: item.z,
            }))} /> : <p className="py-8 text-sm text-muted-foreground">Selecciona un cluster para visualizar su perfil.</p>}
          </Card>
          <Card className="!rounded-xl">
            <CardTitle>Centroides por variable</CardTitle>
            <label className="mt-4 block max-w-xs text-sm">Variable para comparar
              <select className="field mt-1.5" value={feature} onChange={event => setFeature(Number(event.target.value))}>
                {model.features.map((name, index) => <option key={name} value={index}>{name}</option>)}
              </select>
            </label>
            <CompareChart data={model.clusters.map(item => ({ cluster: item.cluster, value: item.center[feature] }))} />
          </Card>
        </section>
      </>;
    }}</WithModel>
  </div>;
}
