"use client";

import { Download, FileCheck2, LoaderCircle, UploadCloud } from "lucide-react";
import { useRef, useState } from "react";
import { CompareChart, DistributionChart, PCA } from "@/components/charts";
import { DataTable } from "@/components/data-table";
import { PageHeading, Status, useWorkspace } from "@/components/shell";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { type Batch, type Preview, MAX_UPLOAD, message, multipart, number } from "@/lib/api";

const EXPORTS = {
  operations: ["Operaciones", "minesight_operaciones.csv"],
  summary: ["Resumen", "minesight_resumen.csv"],
  report: ["Reporte", "minesight_reporte.md"],
} as const;

export default function AnalysisPage() {
  const { model, addOperations } = useWorkspace();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [separator, setSeparator] = useState(",");
  const [decimal, setDecimal] = useState(".");
  const [timeColumn, setTimeColumn] = useState("");
  const [includePca, setIncludePca] = useState(true);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [batch, setBatch] = useState<Batch | null>(null);
  const [queue, setQueue] = useState("");
  const [progress, setProgress] = useState<number | null>(0);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [feature, setFeature] = useState(0);

  function reset() {
    setPreview(null);
    setBatch(null);
    setTimeColumn("");
    setError("");
  }

  function choose(next?: File) {
    if (!next || queue) return;
    reset();
    setFile(null);
    if (!next.name.toLowerCase().endsWith(".csv")) { setError("Selecciona un archivo CSV."); return; }
    if (next.size > MAX_UPLOAD) { setError("El archivo supera el límite de 20 MiB."); return; }
    setFile(next);
  }

  async function run(action: "preview" | "analyze" | keyof typeof EXPORTS) {
    if (!file || queue) return;
    setError("");
    setQueue(action === "preview" ? "Validando archivo" : action === "analyze" ? "Segmentando operaciones" : "Preparando descarga");
    setProgress(0);
    const form = new FormData();
    form.set("file", file);
    form.set("separator", separator);
    form.set("decimal", decimal);
    form.set("time_column", timeColumn);
    form.set("include_pca", String(includePca));
    try {
      if (action === "preview") setPreview(await multipart<Preview>("/api/preview-csv", form, setProgress));
      else if (action === "analyze") {
        const result = await multipart<Batch>("/api/analyze-csv", form, setProgress);
        setBatch(result);
        addOperations(result.operation_count);
      } else {
        const blob = await multipart<Blob>("/api/export-csv/" + action, form, setProgress);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = EXPORTS[action][1];
        anchor.click();
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (error) { setError(message(error)); }
    finally { setQueue(""); setProgress(0); }
  }

  return <>
    <PageHeading label="Segmentación por lote" title="Análisis de operaciones" detail="Valida un CSV, asigna clusters y explora los perfiles de tus operaciones." />
    <div className="space-y-4">
      <Card>
        <CardTitle>Importar mediciones</CardTitle>
        <p className="mt-1 text-sm text-muted-foreground">CSV UTF-8 de hasta 20 MiB. Usa promedios horarios para comparar con el entrenamiento.</p>
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        <div className="space-y-3">
        <input ref={fileInput} id="operations-file" className="sr-only" tabIndex={-1} type="file" accept=".csv,text/csv" aria-label="Archivo CSV"
          onChange={event => { choose(event.target.files?.[0]); event.target.value = ""; }} />
        <button type="button" disabled={!!queue} onClick={() => fileInput.current?.click()}
          onDragOver={event => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]); }}
          className={"grid min-h-40 w-full min-w-0 place-content-center place-items-center gap-2 rounded-xl border border-dashed p-6 text-center outline-none focus-visible:ring-2 focus-visible:ring-sky-400 " + (dragging ? "border-sky-400 bg-sky-500/15" : "border-[#426480] bg-[#122438] hover:bg-[#1a344c]")}>
          {file ? <FileCheck2 className="text-sky-300" /> : <UploadCloud className="text-sky-300" />}
          <span className="max-w-full break-all font-medium">{file?.name ?? "Arrastra un CSV o selecciónalo"}</span>
        </button>
          <Button variant="outline" disabled={!file || !!queue} onClick={() => run("preview")}>Validar y previsualizar</Button>
        </div>
        <div className="rounded-xl border border-border bg-[#0e1928] p-4">
        <h3 className="text-sm font-semibold">Formato del archivo</h3>
        <fieldset disabled={!!queue} className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="text-sm">Separador de campos<select className="field mt-1" value={separator} onChange={event => { reset(); setSeparator(event.target.value); }}>
            <option value=",">Coma (,)</option><option value=";">Punto y coma (;)</option><option value={"\t"}>Tabulación</option>
          </select></label>
          <label className="text-sm">Separador decimal<select className="field mt-1" value={decimal} onChange={event => { reset(); setDecimal(event.target.value); }}>
            <option value=".">Punto (.)</option><option value=",">Coma (,)</option>
          </select></label>
        </fieldset>
        {model && <details className="mt-4 text-sm text-muted-foreground"><summary className="cursor-pointer">Ver columnas requeridas</summary>
          <p className="mt-2 break-words">{model.features.join(", ")}</p>
        </details>}
        </div>
        </div>
      </Card>

      {preview && <Card className="space-y-4">
        <CardTitle>Vista previa de datos</CardTitle>
        <Status kind="success">{number(preview.source_count)} filas validadas.</Status>
        <DataTable data={preview.preview} label="Mediciones del CSV" />
        <fieldset disabled={!!queue} className="grid gap-3">
          <label className="max-w-md text-sm">Granularidad de análisis
            <select className="field mt-1" value={timeColumn} onChange={event => { setTimeColumn(event.target.value); setBatch(null); }}>
              <option value="">Una operación por fila</option>
              {preview.temporal_candidates.map(column => <option key={column} value={column}>Promedios por hora · {column}</option>)}
            </select>
          </label>
          <p className="text-sm text-muted-foreground">La agregación requiere una columna ISO 8601. Los desplazamientos horarios se convierten a UTC.</p>
          <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={includePca}
            onChange={event => { setIncludePca(event.target.checked); setBatch(null); }} /> Calcular proyección PCA</label>
        </fieldset>
        <Button disabled={!!queue} onClick={() => run("analyze")}>Segmentar operaciones</Button>
      </Card>}

      {queue && <div role="status" className="rounded-xl border border-border bg-card p-4">
        <div className="flex items-center gap-2 text-sm"><LoaderCircle size={16} className="animate-spin text-sky-300" />
          {progress === null ? queue + " en FastAPI…" : "Enviando archivo · " + progress + " %"}
        </div>
        <progress value={progress ?? undefined} max={100} aria-label={progress === null ? queue : "Progreso de envío"} className="mt-2 block w-full accent-sky-400" />
      </div>}
      {error && <Status kind="error">{error}</Status>}

      {batch && <>
        <Status kind="success">Lote segmentado · {number(batch.operation_count)} operaciones · {batch.mode}.</Status>
        <div className="grid gap-4 xl:grid-cols-2">
          <Card><CardTitle>Distribución del lote</CardTitle><DistributionChart data={batch.distribution} /></Card>
          {model && <Card><CardTitle>Perfil por variable</CardTitle>
            <label className="mt-3 block text-sm">Variable<select className="field mt-1" value={feature} onChange={event => setFeature(Number(event.target.value))}>
              {model.features.map((name, i) => <option key={name} value={i}>{name}</option>)}
            </select></label>
            <p className="mt-2 text-xs text-muted-foreground">Barras rayadas: promedios del lote. Barras sólidas: centroides históricos.</p>
            <CompareChart data={model.clusters.map(item => ({
              cluster: item.cluster, value: item.center[feature], observed: batch.profiles.find(profile => profile.cluster === item.cluster)?.values[feature],
            }))} />
          </Card>}
        </div>
        {batch.pca && <Card>
          <CardTitle>Proyección PCA del lote</CardTitle>
          <p className="mt-1 text-sm text-muted-foreground">{(batch.pca.variance * 100).toFixed(2)} % de varianza explicada en dos componentes. Se grafican hasta 2 000 operaciones.</p>
          <PCA points={batch.pca.points} />
        </Card>}
        {batch.pca_error && <Status>{batch.pca_error}</Status>}
        <Card className="space-y-4"><CardTitle>Operaciones segmentadas</CardTitle>
          <DataTable data={batch.preview} label="Operaciones segmentadas" />
          <div className="flex flex-wrap gap-2">
            {(Object.keys(EXPORTS) as (keyof typeof EXPORTS)[]).map(key => <Button key={key} variant="outline" disabled={!!queue} onClick={() => run(key)}><Download />{EXPORTS[key][0]}</Button>)}
          </div>
        </Card>
      </>}
    </div>
  </>;
}
