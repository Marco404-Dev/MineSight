export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
export const COLORS = ["#F5A45D", "#38BDF8", "#ADA4FF", "#F4CE69", "#F293BA", "#67D8A1", "#D6A7ED"];
export const AXES = ["Hierro", "Sílice", "Almidón", "Amina", "Caudal pulpa", "pH", "Densidad"];
export const MAX_UPLOAD = 20 * 1024 * 1024;

export type Distribution = { cluster: number; count: number; share: number };
export type Cluster = Distribution & { center: number[]; z: number[] };
export type ModelInfo = {
  algorithm: string; features: string[]; input_keys: string[]; original_records: number; training_hours: number;
  means: number[]; clusters: Cluster[];
  metrics: { silhouette: number; davies_bouldin: number; calinski_harabasz: number; ari: number; pca_variance: number };
  benchmark: { alternative: string; winner: string; metrics: string[] };
};
export type Prediction = {
  cluster: number; values: number[]; z: number[]; center: number[]; center_z: number[];
  historical_hours: number; distances: { cluster: number; distance: number }[];
  descriptors: { feature: string; z: number }[];
};
export type TableData = { columns: string[]; rows: (string | number | boolean | null)[][] };
export type Preview = { source_count: number; temporal_candidates: string[]; preview: TableData };
export type Batch = {
  source_count: number; operation_count: number; mode: string; distribution: Distribution[];
  profiles: { cluster: number; values: number[] }[];
  preview: TableData; pca: { points: { x: number; y: number; cluster: number }[]; variance: number } | null;
  pca_error: string | null;
};

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(API_URL + path, { ...init, cache: "no-store" });
  } catch {
    throw new Error("No se pudo conectar con FastAPI. Comprueba que el servidor esté iniciado.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : "El servidor no pudo completar la solicitud.");
  }
  return response.json();
}

export function multipart<T>(path: string, form: FormData, progress: (value: number | null) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", API_URL + path);
    xhr.responseType = path.startsWith("/api/export") ? "blob" : "json";
    xhr.upload.onprogress = event => {
      if (event.lengthComputable) progress(Math.round(event.loaded * 100 / event.total));
    };
    xhr.upload.onload = () => progress(null);
    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as T);
        return;
      }
      const body = xhr.response instanceof Blob ? await xhr.response.text().then(text => {
        try { return JSON.parse(text); } catch { return null; }
      }) : xhr.response;
      reject(new Error(typeof body?.detail === "string" ? body.detail : "No se pudo procesar el archivo."));
    };
    xhr.onerror = () => reject(new Error("No se pudo conectar con FastAPI."));
    xhr.send(form);
  });
}

export function message(error: unknown) {
  return error instanceof Error ? error.message : "Ocurrió un error inesperado.";
}

const numberFormatter = new Intl.NumberFormat("es-PE", { maximumFractionDigits: 4 });
export const number = (value: number) => numberFormatter.format(value);
