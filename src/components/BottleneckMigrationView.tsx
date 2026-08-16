import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  ArrowRight,
  CheckCircle2,
  Cpu,
  Layers,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  Zap,
  RefreshCw
} from 'lucide-react';

export const BottleneckMigrationView: React.FC = () => {
  const { interventionApplied, applyIntervention } = useFactorySimulation();

  return (
    <div className="w-full bg-[#080B11] p-4 lg:p-6 rounded-2xl border border-indigo-500/30 shadow-2xl relative overflow-hidden">
      
      {/* Background Ambience */}
      <div className="absolute top-0 right-1/3 w-80 h-80 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <RefreshCw className="w-5 h-5 text-indigo-400" />
            <h3 className="font-heading font-bold text-lg text-white tracking-wider">
              DYNAMIC BOTTLENECK MIGRATION
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950/80 border border-indigo-500/40 text-indigo-300 font-semibold">
              CONTINUOUS CLOSED-LOOP RECOMPUTATION
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Fixing one constraint causes surge volume to propagate down the line, shifting the next bottleneck.
          </p>
        </div>

        {!interventionApplied && (
          <button
            onClick={() => applyIntervention('ADD_OPERATOR')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-mono text-xs font-bold transition-all"
          >
            <Zap className="w-3.5 h-3.5" />
            <span>APPLY SCENARIO B TO SEE MIGRATION</span>
          </button>
        )}
      </div>

      {/* Comparative Before vs After Migration Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* State A: Before Intervention */}
        <div className={`p-4 rounded-xl border font-mono transition-all ${
          !interventionApplied ? 'bg-slate-900/90 border-amber-500/60 ring-1 ring-amber-500/30' : 'bg-slate-950/60 border-slate-800 opacity-60'
        }`}>
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="text-slate-400 font-bold uppercase">1. BEFORE INTERVENTION</span>
            <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 font-bold text-[10px]">
              S3 = PRIMARY BOTTLENECK
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center">
              <span>S3 Chassis Marriage:</span>
              <span className="text-red-400 font-bold">79.6s Cycle Time (Locked)</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center">
              <span>Upstream S2 Buffer:</span>
              <span className="text-amber-400 font-bold">5 / 5 (100% Saturated)</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center">
              <span>Downstream S4 Powertrain:</span>
              <span className="text-indigo-300">STARVED (68% Utilization)</span>
            </div>
          </div>
        </div>

        {/* State B: After Intervention (Migration to S4) */}
        <div className={`p-4 rounded-xl border font-mono transition-all ${
          interventionApplied ? 'bg-slate-900/90 border-indigo-500/60 ring-1 ring-indigo-500/40' : 'bg-slate-950/60 border-slate-800'
        }`}>
          <div className="flex items-center justify-between mb-3 text-xs">
            <span className="text-emerald-400 font-bold uppercase">2. AFTER INTERVENTION (S3 CURED)</span>
            <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 font-bold text-[10px]">
              S4 = EMERGING NEXT CONSTRAINT (T+23m)
            </span>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-slate-950 border border-emerald-500/30 flex justify-between items-center">
              <span>S3 Chassis Marriage:</span>
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                52.0s (Nominal & Balanced)
              </span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center">
              <span>S3 Output Surge:</span>
              <span className="text-emerald-400 font-bold">+9 Vehicles/Hour</span>
            </div>
            <div className="p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/40 flex justify-between items-center">
              <span>S4 Powertrain Influx:</span>
              <span className="text-indigo-300 font-bold">Queue Rising (4/5 in 23m)</span>
            </div>
          </div>
        </div>

      </div>

      {/* Causal Feedback loop insight */}
      <div className="mt-4 p-3 bg-indigo-950/20 rounded-xl border border-indigo-500/20 text-xs font-mono text-slate-300">
        <strong>Digital Twin Closed Loop:</strong> The moment S3 recovers, the Digital Twin recalculates the global plant flow vector. It flags that S4 Powertrain will become the next constraint in 23 minutes, allowing operators to pre-stage battery pack AGVs before S4 queue peaks.
      </div>

    </div>
  );
};
