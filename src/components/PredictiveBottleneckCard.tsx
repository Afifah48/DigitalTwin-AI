import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  Clock,
  HelpCircle,
  GitBranch,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap
} from 'lucide-react';

export const PredictiveBottleneckCard: React.FC = () => {
  const {
    countdownSec,
    openWhyModal,
    openWhatIfModal,
    interventionApplied,
    applyIntervention
  } = useFactorySimulation();

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  if (interventionApplied) {
    return (
      <div className="w-full bg-emerald-950/40 p-5 lg:p-6 rounded-2xl border border-emerald-500/40 shadow-2xl relative overflow-hidden">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center">
              <CheckCircle2 className="w-7 h-7 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-900/60 text-emerald-300 font-bold">
                  PREEMPTIVE INTERVENTION ACTIVE
                </span>
                <span className="text-xs font-mono text-slate-400">Policy: Scenario B</span>
              </div>
              <h3 className="font-heading font-bold text-xl text-white mt-0.5">
                S3 CHASSIS BOTTLENECK AVERTED
              </h3>
              <p className="text-xs font-mono text-slate-300">
                Cycle time stabilized to 52.0s • Upstream S2 buffer unlocked • Line throughput increased to <strong>43 UPH (+9)</strong>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs">
            <div className="bg-slate-900/80 p-2.5 rounded-lg border border-emerald-500/30">
              <span className="text-slate-400 text-[10px] block">AVERTED DOWNTIME COST</span>
              <span className="text-emerald-400 font-bold text-base">$142,000</span>
            </div>
            <button
              onClick={() => openWhatIfModal()}
              className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-heading font-semibold transition-colors"
            >
              COMPARE OTHER SCENARIOS
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-[#130d17] p-5 lg:p-6 rounded-2xl border border-red-500/40 shadow-2xl relative overflow-hidden">
      
      {/* Ambient Red/Amber Alert Backlight */}
      <div className="absolute -top-12 -right-12 w-64 h-64 bg-red-600/15 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-12 -left-12 w-64 h-64 bg-amber-600/10 rounded-full blur-3xl pointer-events-none" />

      {/* Main Prediction Top Header */}
      <div className="relative z-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 pb-4 border-b border-red-500/20">
        
        {/* Title & Probability */}
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-red-950/80 border border-red-500/60 flex items-center justify-center shadow-lg shadow-red-500/20">
            <AlertTriangle className="w-6 h-6 text-red-400 animate-bounce" />
          </div>

          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-red-900/80 text-red-200 font-bold tracking-wider">
                AI PREDICTIVE BOTTLENECK ALERT
              </span>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-amber-300 font-bold">
                PROBABILITY: 87%
              </span>
            </div>

            <h3 className="font-heading font-bold text-xl text-white tracking-wide mt-1">
              S3 — CHASSIS MARRIAGE
            </h3>
          </div>
        </div>

        {/* Live Countdown & Critical Principle */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 font-mono">
          
          {/* Big Countdown Box */}
          <div className="bg-slate-950/90 px-4 py-2 rounded-xl border border-amber-500/40 shadow-inner flex items-center gap-3">
            <div>
              <span className="text-[10px] text-slate-400 uppercase tracking-widest block">TIME-TO-LOCKUP</span>
              <span className="text-2xl font-black text-amber-400 tracking-wider">
                {formatCountdown(countdownSec)}
              </span>
            </div>
            <Clock className="w-5 h-5 text-amber-400 animate-spin" style={{ animationDuration: '8s' }} />
          </div>

          {/* Quick Action CTAs */}
          <div className="flex items-center gap-2">
            <button
              onClick={openWhyModal}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-heading font-bold shadow-md shadow-amber-500/20 transition-all cursor-pointer"
            >
              <HelpCircle className="w-4 h-4" />
              <span>EXPLAIN WHY</span>
            </button>

            <button
              onClick={() => openWhatIfModal()}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-heading font-bold shadow-md shadow-emerald-600/20 transition-all cursor-pointer"
            >
              <GitBranch className="w-4 h-4" />
              <span>SIMULATE WHAT-IF</span>
            </button>
          </div>
        </div>

      </div>

      {/* Upstream & Downstream Propagation Dynamics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 my-4">
        
        {/* Upstream S2 Blocking */}
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-amber-500/30 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-amber-300 font-bold mb-1">
              <span className="flex items-center gap-1">
                <ArrowUpRight className="w-4 h-4" />
                UPSTREAM PROPAGATION
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-400">S2 → S3</span>
            </div>
            <h4 className="font-heading font-bold text-sm text-white">Buffer B23 Saturation & Paint Blocking</h4>
            <p className="text-[11px] font-mono text-slate-300 mt-1">
              As S3 slows down, Buffer B23 reaches 5/5 max capacity. Paint shop S2 will be forced into hard interlock stoppage in 8.5 min.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] font-mono flex justify-between text-slate-400">
            <span>Buffer Occupancy:</span>
            <span className="text-amber-400 font-bold">5 / 5 (100% Locked)</span>
          </div>
        </div>

        {/* Primary Bottleneck Root S3 */}
        <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-500/50 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-red-300 font-bold mb-1">
              <span className="flex items-center gap-1">
                <Zap className="w-4 h-4" />
                PRIMARY CONSTRAINT
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-red-900 text-red-200">S3 CHASSIS</span>
            </div>
            <h4 className="font-heading font-bold text-sm text-white">Atlas Copco Spindle #4 Torque Anomaly</h4>
            <p className="text-[11px] font-mono text-slate-300 mt-1">
              Motor current variance +3.85 A² during multi-spindle decking. Cycle time drifting from 54s to 79.6s (+47%).
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-red-500/30 text-[10px] font-mono flex justify-between text-slate-400">
            <span>Takt Deviation δ(t):</span>
            <span className="text-red-400 font-bold">+25.6s Degradation</span>
          </div>
        </div>

        {/* Downstream S4 Starvation */}
        <div className="p-3.5 rounded-xl bg-slate-950/80 border border-indigo-500/30 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-xs font-mono text-indigo-300 font-bold mb-1">
              <span className="flex items-center gap-1">
                <ArrowDownRight className="w-4 h-4" />
                DOWNSTREAM PROPAGATION
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-400">S3 → S4</span>
            </div>
            <h4 className="font-heading font-bold text-sm text-white">Line Starvation at Powertrain & Interior</h4>
            <p className="text-[11px] font-mono text-slate-300 mt-1">
              Starvation wavefront starves S4 and S5. Station utilization drops to 68%, dragging total plant throughput from 42 to 31 UPH.
            </p>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] font-mono flex justify-between text-slate-400">
            <span>Line Throughput Loss:</span>
            <span className="text-indigo-400 font-bold">-11 Vehicles/Hour</span>
          </div>
        </div>

      </div>

      {/* The Central Manifesto Banner */}
      <div className="p-3 bg-slate-950/90 rounded-xl border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="text-slate-300">
            <strong>CORE PRINCIPLE:</strong> “WE DON'T PREDICT THE BOTTLENECK. WE PREDICT HOW THE LINE WILL EVOLVE.”
          </span>
        </div>

        <span className="text-[11px] text-cyan-400 font-semibold italic shrink-0">
          Act before the problem arrives →
        </span>
      </div>

    </div>
  );
};
