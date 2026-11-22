"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, FileUp, LayoutDashboard, Mountain, Network } from "lucide-react";
import { motion, MotionConfig } from "motion/react";
import { createContext, useContext, useEffect, useState } from "react";
import { type ModelInfo, message, request } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const NAV = [
  { href: "/", label: "Panel ejecutivo", icon: LayoutDashboard },
  { href: "/analisis", label: "Análisis CSV", icon: FileUp },
  { href: "/prediccion", label: "Predicción manual", icon: Activity },
  { href: "/modelo", label: "Información del modelo", icon: Network },
];

const Workspace = createContext<{
  model: ModelInfo | null; error: string; retry: () => void;
  sessionCount: number; addOperations: (count: number) => void;
}>({ model: null, error: "", retry: () => {}, sessionCount: 0, addOperations: () => {} });

export function useWorkspace() {
  return useContext(Workspace);
}

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const [sessionCount, setSessionCount] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    request<ModelInfo>("/api/model-info", { signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setModel(data); })
      .catch(error => { if (!controller.signal.aborted) setError(message(error)); });
    return () => controller.abort();
  }, [retryCount]);

  return <MotionConfig reducedMotion="user">
    <Workspace.Provider value={{
      model, error, sessionCount, addOperations: count => setSessionCount(previous => previous + count),
      retry: () => { setError(""); setRetryCount(previous => previous + 1); },
    }}>
      <div className="min-h-screen">
        <header className="sticky top-0 z-20 border-b border-border bg-[#0a1421]/95 backdrop-blur-xl"><div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-8 gap-y-2 px-4 pt-3 sm:px-7 lg:flex-nowrap lg:px-9 lg:pt-0">
          <Link href="/" className="flex items-center gap-3 shrink-0 rounded-lg text-xl font-bold tracking-tight">
            <span className="grid size-10 place-items-center rounded-xl border border-[#f5a45d50] bg-[#f5a45d14] text-primary"><Mountain size={21} /></span>
            MineSight
          </Link>
          <nav aria-label="Navegación principal" className="grid w-full grid-cols-2 gap-x-2 sm:flex sm:w-auto">
            {NAV.map(({ href, label, icon: Icon }) => <Link key={href} href={href}
              aria-current={pathname === href ? "page" : undefined}
              className={cn("flex min-h-11 items-center gap-2 border-b-2 border-transparent px-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground sm:px-3 sm:text-sm lg:min-h-16",
                pathname === href && "border-b-[#f5a45d] text-[#ffd1a7]")}>
              <Icon size={17} className="shrink-0" />{label}
            </Link>)}
          </nav>
          <span className="ml-auto hidden font-mono text-xs text-muted-foreground xl:inline">UPCH · Challenge 4</span>
        </div></header>
        <main className="min-w-0 bg-[radial-gradient(ellipse_at_top_right,#112338,transparent_45%)]">
          <motion.div key={pathname} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
            transition={{ duration: .24 }} className="mx-auto max-w-[1500px] px-4 py-6 sm:px-7 lg:px-9 lg:py-9">
            {children}
          </motion.div>
        </main>
      </div>
    </Workspace.Provider>
  </MotionConfig>;
}

export function PageHeading({ label, title, detail }: { label: string; title: string; detail: string }) {
  return <header className="mb-7">
    <p className="text-xs font-bold tracking-[.16em] text-primary uppercase">{label}</p>
    <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">{title}</h1>
    <p className="mt-2 max-w-3xl text-sm leading-relaxed text-muted-foreground sm:text-base">{detail}</p>
  </header>;
}

export function Status({ children, kind = "info" }: { children: React.ReactNode; kind?: "info" | "error" | "success" }) {
  return <div role={kind === "error" ? "alert" : "status"} className={cn("rounded-lg border px-3.5 py-3 text-sm",
    kind === "error" ? "border-rose-500/40 bg-rose-500/10 text-rose-200" :
    kind === "success" ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200" :
    "border-sky-500/30 bg-sky-500/10 text-sky-100")}>{children}</div>;
}

export function WithModel({ children }: { children: (data: ModelInfo) => React.ReactNode }) {
  const { model, error, retry } = useWorkspace();
  if (error) return <Status kind="error">{error} <Button onClick={retry} variant="outline" className="ml-2">Reintentar</Button></Status>;
  if (!model) return <div role="status" aria-label="Cargando datos del modelo" className="grid gap-4 sm:grid-cols-2">
    <div className="h-32 animate-pulse rounded-2xl bg-card" /><div className="h-32 animate-pulse rounded-2xl bg-card" />
  </div>;
  return children(model);
}
