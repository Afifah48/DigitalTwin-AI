import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import { MONTE_CARLO_PASSES } from '../data/factoryData';
import {
  ShieldAlert,
  X,
  Layers,
  Sparkles,
  Activity,
  Cpu,
  BarChart2,
  CheckCircle2
} from 'lucide-react';

export const UncertaintyViewModal: React.FC = () => {
  const { isUncertaintyModalOpen, closeUncertaintyModal, stations, uncertaintyData } = useFactorySimulation();

  if (!isUncertaintyModalOpen) return null;

  const passes = uncertaintyData?.passes || MONTE_CARLO_PASSES;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#0c101a] border border-purple-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col font-mono">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between gap-4 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/20 border border-purple-500/50 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs px-2 py-0.5 rounded bg-purple-950 border border-purple-500/30 text-purple-300 font-bold">
                  EPISTEMIC & ALEATORIC UNCERTAINTY
                </span>
                <span className="text-xs text-slate-400">Monte Carlo Dropout (50 Forward Passes)</span>
              </div>
              <h2 className="font-heading font-bold text-xl text-white tracking-wide mt-0.5">
                PREDICTION IS NEVER PRESENTED WITHOUT CONFIDENCE
              </h2>
            </div>
          </div>

          <button
            onClick={closeUncertaintyModal}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 overflow-y-auto space-y-5 flex-1 text-xs">
          
          {/* MC Dropout 50 Trajectories Visualizer */}
          <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800">
            <div className="flex items-center justify-between mb-3">
              <span className="text-purple-300 font-bold">50 MC Stochastic Forward Passes Fan (T+0 to T+20 min)</span>
              <span className="text-slate-400 text-[11px]">90% Prediction Envelope</span>
            </div>

            {/* Simulated Canvas Fan Chart */}
            <div className="relative h-44 w-full bg-slate-900/60 rounded-lg border border-slate-800/80 p-2 overflow-hidden flex items-end">
              <svg viewBox="0 0 500 120" className="w-full h-full">
                {/* 50 faint trajectory lines */}
                {passes.map((p) => {
                  const pointsStr = p.trajectory.map((pt, idx) => {
                    const x = idx * 125;
                    const y = 120 - ((pt.value - 60) / 120) * 110;
                    return `${x},${y}`;
                  }).join(' ');

                  return (
                    <polyline
                      key={p.passId}
                      points={pointsStr}
                      fill="none"
                      stroke="#c084fc"
                      strokeWidth="1"
                      strokeOpacity="0.22"
                    />
                  );
                })}

                {/* Mean Forecast Line */}
                <polyline
                  points="0,102 125,85 250,60 375,38 500,10"
                  fill="none"
                  stroke="#38bdf8"
                  strokeWidth="2.5"
                />

                {/* 90% Upper and Lower Bound Lines */}
                <polyline
                  points="0,96 125,75 250,48 375,22 500,2"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
                <polyline
                  points="0,108 125,95 250,72 375,54 500,20"
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  strokeDasharray="4 4"
                />
              </svg>

              {/* Chart Legend */}
              <div className="absolute top-2 right-2 flex items-center gap-3 bg-slate-950/80 px-2 py-1 rounded text-[10px]">
                <span className="text-cyan-400 font-bold">— Mean Forecast</span>
                <span className="text-red-400 font-bold">--- 90% Prediction Interval</span>
              </div>
            </div>
          </div>

          {/* Station Sensor Instrumentation Confidence Matrix */}
          <div>
            <h4 className="text-sm font-heading font-bold text-white mb-2">
              STATION SENSOR INSTRUMENTATION & CONFIDENCE BREAKDOWN
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
              {stations.map((st) => (
                <div key={st.id} className="p-3 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-cyan-400">{st.id}: {st.name}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                      st.telemetry.confidence > 90 ? 'bg-emerald-950 text-emerald-300' :
                      st.telemetry.confidence > 75 ? 'bg-indigo-950 text-indigo-300' : 'bg-amber-950 text-amber-300'
                    }`}>
                      {st.telemetry.confidence}% CONFIDENCE
                    </span>
                  </div>

                  <p className="text-[10px] text-slate-400 mb-2">
                    {st.sensorCount} Real-time Telemetry Sensors • {st.telemetry.instrumentationLevel} Coverage
                  </p>

                  <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        st.telemetry.confidence > 90 ? 'bg-emerald-400' :
                        st.telemetry.confidence > 75 ? 'bg-indigo-400' : 'bg-amber-400'
                      }`}
                      style={{ width: `${st.telemetry.confidence}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Footer */}
        <div className="p-4 bg-slate-950 border-t border-slate-800 flex justify-between items-center text-xs text-slate-400">
          <span>Uncertainty is explicitly factored into risk thresholds and intervention rankings.</span>
          <button
            onClick={closeUncertaintyModal}
            className="px-4 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-200 hover:text-white"
          >
            CLOSE
          </button>
        </div>

      </div>
    </div>
  );
};
