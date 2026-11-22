import type { Metadata } from "next";
import { Shell } from "@/components/shell";
import "./globals.css";

export const metadata: Metadata = {
  title: "MineSight · Inteligencia operativa",
  description: "Analítica operativa de flotación de mineral de hierro.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body><Shell>{children}</Shell></body></html>;
}
