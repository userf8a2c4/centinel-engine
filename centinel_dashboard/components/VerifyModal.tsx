"use client";

import { X, CheckCircle2, XCircle } from "lucide-react";
import { useState } from "react";

interface VerifyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function VerifyModal({ isOpen, onClose }: VerifyModalProps) {
  const [hashValue, setHashValue] = useState("");
  const [result, setResult] = useState<"idle" | "valid" | "invalid">("idle");

  if (!isOpen) return null;

  const handleVerify = () => {
    setResult(hashValue.toLowerCase().includes("9f3a") ? "valid" : "invalid");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4">
      <div className="glass gradient-border w-full max-w-xl rounded-3xl p-6">
        <div className="flex items-center justify-between">
          <p className="text-lg font-semibold text-white">Verificación ciudadana</p>
          <button onClick={onClose} type="button">
            <X className="h-5 w-5 text-slate-400" />
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          Pega un hash raíz para validar su registro en Arbitrum L2.
        </p>
        <input
          className="mt-4 w-full rounded-2xl border border-slate-700/70 bg-slate-900/60 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:outline-none"
          placeholder="0x..."
          value={hashValue}
          onChange={(event) => setHashValue(event.target.value)}
        />
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            className="rounded-2xl bg-centinel-blue/20 px-4 py-2 text-sm text-centinel-blue"
            onClick={handleVerify}
            type="button"
          >
            Verificar ahora
          </button>
          <button
            className="rounded-2xl border border-slate-700/70 bg-slate-900/60 px-4 py-2 text-sm text-slate-200"
            type="button"
          >
            Ver en explorer
          </button>
        </div>
        {result !== "idle" ? (
          <div className="mt-6 rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 text-sm">
            <div className="flex items-center gap-2">
              {result === "valid" ? (
                <CheckCircle2 className="h-5 w-5 text-centinel-green" />
              ) : (
                <XCircle className="h-5 w-5 text-rose-400" />
              )}
              <p className="font-semibold text-white">
                {result === "valid" ? "Verificado ✓" : "No coincide ✗"}
              </p>
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {result === "valid"
                ? "Hash confirmado en Arbitrum L2 con prueba pública disponible."
                : "El hash no coincide con el registro actual. Revisa el origen o prueba otra entrada."}
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
