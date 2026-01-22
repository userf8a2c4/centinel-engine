"use client";

import {
  Area,
  AreaChart,
  Pie,
  PieChart,
  Cell,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip
} from "recharts";

const timelineData = [
  { day: "Lun", snapshots: 128, cambios: 12 },
  { day: "Mar", snapshots: 132, cambios: 18 },
  { day: "Mié", snapshots: 140, cambios: 9 },
  { day: "Jue", snapshots: 152, cambios: 14 },
  { day: "Vie", snapshots: 168, cambios: 22 },
  { day: "Sáb", snapshots: 174, cambios: 11 },
  { day: "Dom", snapshots: 160, cambios: 7 }
];

const anomalies = [
  { name: "Cambios no esperados", value: 38 },
  { name: "Patrones repetidos", value: 21 },
  { name: "Alteraciones críticas", value: 12 },
  { name: "Meta-datos", value: 29 }
];

const anomalyColors = ["#00D4FF", "#8B5CF6", "#F87171", "#10B981"];

const heatmap = [
  { time: "00:00", score: 20 },
  { time: "04:00", score: 32 },
  { time: "08:00", score: 48 },
  { time: "12:00", score: 71 },
  { time: "16:00", score: 58 },
  { time: "20:00", score: 36 }
];

export function ChartsSection() {
  return (
    <section className="grid gap-6 lg:grid-cols-3">
      <div className="glass gradient-border rounded-3xl p-5 lg:col-span-2">
        <div className="mb-4">
          <p className="text-sm font-semibold">Evolución de snapshots y cambios detectados</p>
          <p className="text-xs text-slate-400">Últimos 7 días</p>
        </div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timelineData}>
              <XAxis dataKey="day" stroke="#94A3B8" tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid #334155" }} />
              <Area type="monotone" dataKey="snapshots" stroke="#00D4FF" fill="#00D4FF" fillOpacity={0.2} />
              <Area type="monotone" dataKey="cambios" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass gradient-border rounded-3xl p-5">
        <p className="text-sm font-semibold">Distribución de anomalías</p>
        <p className="text-xs text-slate-400">Últimas 24h</p>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={anomalies} dataKey="value" innerRadius={40} outerRadius={80} paddingAngle={5}>
                {anomalies.map((entry, index) => (
                  <Cell key={entry.name} fill={anomalyColors[index % anomalyColors.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#0F172A", border: "1px solid #334155" }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="glass gradient-border rounded-3xl p-5 lg:col-span-3">
        <p className="text-sm font-semibold">Heatmap de actividad por hora</p>
        <p className="text-xs text-slate-400">Detecta patrones sospechosos</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
          {heatmap.map((slot) => (
            <div key={slot.time} className="rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4">
              <p className="text-xs text-slate-400">{slot.time}</p>
              <p className="mt-2 text-lg font-semibold" style={{ color: slot.score > 60 ? "#F87171" : "#00D4FF" }}>
                {slot.score}%
              </p>
              <p className="text-[11px] text-slate-500">Intensidad</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
