"use client";

import { useReducedMotion } from "motion/react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis,
  Radar, RadarChart, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from "recharts";
import { AXES, COLORS, type Batch, type Distribution } from "@/lib/api";

const AXIS = "#a9bbcf";
const GRID = "#263950";
const clusterLabel = (value: string | number) => "Cluster " + value;

export function DistributionChart({ data }: { data: Distribution[] }) {
  const reduced = useReducedMotion();
  return <div className="h-[275px] w-full min-w-0">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart data={data} margin={{ left: -12, right: 10, top: 10 }}>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="cluster" tick={{ fill: AXIS }} />
        <YAxis tick={{ fill: AXIS }} allowDecimals={false} />
        <Tooltip labelFormatter={value => clusterLabel(String(value ?? ""))} cursor={{ fill: "#ffffff0c" }} formatter={(value, _, item) => [
          String(value) + " · " + Number(item.payload.share).toFixed(1) + " %", "Operaciones",
        ]} />
        <Bar dataKey="count" radius={[6, 6, 0, 0]} isAnimationActive={!reduced} animationDuration={450}>
          {data.map(item => <Cell key={item.cluster} fill={COLORS[item.cluster]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  </div>;
}

export function CompareChart({ data, selected }: { data: { cluster: number; value: number; observed?: number }[]; selected?: number }) {
  const reduced = useReducedMotion();
  const observed = data.some(item => item.observed !== undefined);
  return <div className="h-[285px] w-full min-w-0">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <BarChart data={data} margin={{ top: 14, right: 10 }}>
        <defs>
          {COLORS.map((color, i) => <pattern key={color} id={"pattern-" + i} patternUnits="userSpaceOnUse" width={6} height={6}>
            <rect width={6} height={6} fill={color} /><path d="M0 6L6 0" stroke="#0b1523" strokeWidth={2} />
          </pattern>)}
        </defs>
        <CartesianGrid vertical={false} stroke={GRID} />
        <XAxis dataKey="cluster" tick={{ fill: AXIS }} /><YAxis tick={{ fill: AXIS }} />
        <Tooltip labelFormatter={value => clusterLabel(String(value ?? ""))} cursor={{ fill: "#ffffff0c" }} />
        <Bar dataKey="value" name="Centroide histórico" radius={[5, 5, 0, 0]} isAnimationActive={!reduced}>
          {data.map(item => <Cell key={item.cluster} fill={COLORS[item.cluster]} />)}
        </Bar>
        {observed && <Bar dataKey="observed" name="Promedio del lote" radius={[4, 4, 0, 0]} isAnimationActive={!reduced}>
          {data.map(item => <Cell key={item.cluster} fill={"url(#pattern-" + item.cluster + ")"} />)}
        </Bar>}
        {selected !== undefined && <ReferenceLine y={selected} stroke="#f8fafc" strokeDasharray="5 5" ifOverflow="extendDomain" />}
      </BarChart>
    </ResponsiveContainer>
  </div>;
}

export function ProfileRadar({ vectors }: { vectors: { label: string; color: string; values: number[] }[] }) {
  const reduced = useReducedMotion();
  const extent = Math.max(1, ...vectors.flatMap(vector => vector.values.map(Math.abs)));
  const radius = Math.ceil(extent);
  const data = AXES.map((feature, i) => ({
    feature, ...Object.fromEntries(vectors.map(vector => [vector.label, vector.values[i]])),
  }));
  return <div className="h-[300px] w-full min-w-0">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <RadarChart data={data} outerRadius="69%">
        <PolarGrid stroke={GRID} />
        <PolarAngleAxis dataKey="feature" tick={{ fill: AXIS, fontSize: 11 }} />
        <PolarRadiusAxis domain={[-radius, radius]} tick={{ fill: AXIS, fontSize: 10 }} />
        <Tooltip formatter={value => typeof value === "number" ? value.toFixed(2) + " σ" : String(value)} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        {vectors.map(vector => <Radar key={vector.label} dataKey={vector.label} stroke={vector.color}
          fill={vector.color} fillOpacity={.09} strokeWidth={2} isAnimationActive={!reduced} />)}
      </RadarChart>
    </ResponsiveContainer>
  </div>;
}

export function PCA({ points }: { points: NonNullable<Batch["pca"]>["points"] }) {
  return <div className="h-[350px] w-full min-w-0">
    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
      <ScatterChart margin={{ right: 14, bottom: 10 }}>
        <CartesianGrid stroke={GRID} />
        <XAxis dataKey="x" name="CP1" type="number" tick={{ fill: AXIS }} domain={["auto", "auto"]} />
        <YAxis dataKey="y" name="CP2" type="number" tick={{ fill: AXIS }} domain={["auto", "auto"]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={value => typeof value === "number" ? value.toFixed(3) : String(value)} />
        <Legend />
        {COLORS.map((color, cluster) => {
          const data = points.filter(point => point.cluster === cluster);
          return data.length > 0 && <Scatter name={clusterLabel(cluster)} key={cluster} data={data} fill={color} fillOpacity={.8} isAnimationActive={false} />;
        })}
      </ScatterChart>
    </ResponsiveContainer>
  </div>;
}
