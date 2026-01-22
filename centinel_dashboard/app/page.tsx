"use client";

import { useState } from "react";
import {
  Activity,
  AlertOctagon,
  CheckCircle2,
  GitCommit,
  Layers,
  Users
} from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { HeroCard } from "@/components/HeroCard";
import { KpiCard } from "@/components/KpiCard";
import { ChartsSection } from "@/components/ChartsSection";
import { SnapshotTable } from "@/components/SnapshotTable";
import { RulesPanel } from "@/components/RulesPanel";
import { AiDetectionPanel } from "@/components/AiDetectionPanel";
import { VerifyModal } from "@/components/VerifyModal";

export default function Page() {
  const [isVerifyOpen, setIsVerifyOpen] = useState(false);
  const [isLightMode, setIsLightMode] = useState(false);

  return (
    <div className={isLightMode ? "bg-slate-100 text-slate-900" : "bg-centinel-bg text-slate-100"}>
      <div className="min-h-screen w-full bg-[radial-gradient(circle_at_top,_rgba(0,212,255,0.12),_transparent_55%)] px-4 py-8 text-sm lg:px-10">
        <div className="mx-auto flex max-w-[1500px] gap-6">
          <Sidebar />
          <main className="flex-1 space-y-6">
            <Header
              onVerifyClick={() => setIsVerifyOpen(true)}
              onThemeToggle={() => setIsLightMode((prev) => !prev)}
              isLightMode={isLightMode}
            />

            <HeroCard />

            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <KpiCard
                title="Snapshots 24h"
                value="174"
                delta="+12 vs. ayer"
                icon={<Layers className="h-4 w-4" />}
                accent="text-centinel-blue"
                footer="Snapshots cada 10 min"
              />
              <KpiCard
                title="Cambios detectados"
                value="68"
                delta="▼ 14%"
                icon={<GitCommit className="h-4 w-4" />}
                accent="text-centinel-green"
                footer="Tendencia estable"
              />
              <KpiCard
                title="Anomalías críticas"
                value="0"
                delta="Sin incidentes"
                icon={<AlertOctagon className="h-4 w-4" />}
                accent="text-centinel-green"
                footer="Monitoreo IA continuo"
              />
              <KpiCard
                title="Reglas activas"
                value="12"
                delta="2 nuevas"
                icon={<Activity className="h-4 w-4" />}
                accent="text-centinel-purple"
                footer="Reglas en tiempo real"
              />
              <KpiCard
                title="Verificaciones ciudadanas"
                value="2.4K"
                delta="+8%"
                icon={<Users className="h-4 w-4" />}
                accent="text-centinel-blue"
                footer="Hash raíz reproducible"
              />
            </section>

            <ChartsSection />

            <SnapshotTable />

            <div className="grid gap-6 lg:grid-cols-2">
              <RulesPanel />
              <div className="glass gradient-border flex h-full flex-col justify-between rounded-3xl p-6">
                <div className="space-y-3">
                  <p className="text-sm font-semibold">Reportes reproducibles</p>
                  <p className="text-xs text-slate-400">
                    Exporta informes verificables por cualquier ciudadano con hash y prueba en blockchain.
                  </p>
                </div>
                <div className="mt-6 grid gap-3 text-xs">
                  {[
                    "PDF firmado con branding Centinel",
                    "JSON auditado con firma L2",
                    "Historial completo de snapshots"
                  ].map((item) => (
                    <div key={item} className="flex items-center gap-2 rounded-2xl border border-slate-800/80 bg-slate-900/50 px-4 py-3">
                      <CheckCircle2 className="h-4 w-4 text-centinel-green" />
                      {item}
                    </div>
                  ))}
                  <button className="rounded-2xl bg-centinel-purple/20 px-4 py-3 text-xs text-centinel-purple">
                    Exportar reporte PDF
                  </button>
                </div>
              </div>
            </div>

            <AiDetectionPanel />
          </main>
        </div>
      </div>
      <VerifyModal isOpen={isVerifyOpen} onClose={() => setIsVerifyOpen(false)} />
    </div>
  );
}
