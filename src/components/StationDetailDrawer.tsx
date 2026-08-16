import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  Cpu,
  X,
  Activity,
  Zap,
  Gauge,
  Thermometer,
  Layers,
  Wrench,
  AlertTriangle,
  CheckCircle2
} from 'lucide-react';

export const StationDetailDrawer: React.FC = () => {
  const { selectedStation, setSelectedStation, openWhyModal, interventionApplied } = useFactorySimulation();

  if (!selectedStation) return null;

  const { telemetry } = selectedStation;
  const isDegraded = !interventionApplied && selectedStation.deviationScore > 0.4;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#0b0f19] border-l border-cyan-500/30 shadow-2xl overflow-y-auto p-5 font-mono text-xs animate-slideLeft flex flex-col justify-between">
      
      <div>
        {/* Header */}
        <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-cyan-400 font-bold text-base">{selectedStation.id}</span>
                <span className="text-white font-bold text-sm">{selectedStation.name}</span>
              </div>
              <p className="text-slate-400 text-[10px]">{selectedStation.subTitle}</p>
            </div>
          </div>

          <button
            onClick={() => setSelectedStation(null)}
            className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Overview & Tooling */}
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 mb-4 space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Active Tooling:</span>
            <span className="text-slate-200 font-semibold truncate max-w-[200px]">{selectedStation.activeTooling}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Sensor Density:</span>
            <span className="text-cyan-300 font-bold">{selectedStation.sensorCount} Real-time Telemetry Feeds</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Machine State:</span>
            <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
              isDegraded ? 'bg-red-950 text-red-300' : 'bg-emerald-950 text-emerald-300'
            }`}>
              {telemetry.machineState}
            </span>
          </div>
        </div>

        {/* Live Telemetry Sensor Matrix */}
        <div className="space-y-2 mb-4">
          <h4 className="text-slate-400 uppercase text-[10px] tracking-wider font-bold">
            LIVE INDUSTRIAL SENSOR STREAMS (100Hz)
          </h4>

          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">CYCLE TIME</span>
              <div className="flex items-baseline gap-1 mt-0.5">
                <span className={`text-base font-bold ${telemetry.cycleTime > 65 ? 'text-red-400' : 'text-white'}`}>
                  {telemetry.cycleTime.toFixed(1)}s
                </span>
                <span className="text-slate-500 text-[9px]">/ {telemetry.baselineCycleTime}s</span>
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">UTILIZATION</span>
              <span className="text-base font-bold text-white mt-0.5 block">{telemetry.utilization}%</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">MOTOR CURRENT</span>
              <span className={`text-base font-bold mt-0.5 block ${telemetry.currentVariance > 1.5 ? 'text-amber-400' : 'text-white'}`}>
                {telemetry.motorCurrent.toFixed(1)} A
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">VIBRATION RMS</span>
              <span className="text-base font-bold text-white mt-0.5 block">{telemetry.vibration.toFixed(1)} mm/s</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">OPERATING TEMP</span>
              <span className="text-base font-bold text-white mt-0.5 block">{telemetry.temperature.toFixed(1)} °C</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <span className="text-slate-400 text-[9px] block">TWIN CONFIDENCE</span>
              <span className="text-base font-bold text-emerald-400 mt-0.5 block">{telemetry.confidence}%</span>
            </div>
          </div>
        </div>

        {/* S3 Anomaly Callout if applicable */}
        {selectedStation.id === 'S3' && isDegraded && (
          <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-500/40 space-y-2">
            <div className="flex items-center gap-2 text-amber-300 font-bold">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <span>Degradation δ(t) Anomaly Active</span>
            </div>
            <p className="text-[11px] text-slate-300">
              Spindle #4 motor torque variance +3.85 A² causing cycle-time creep from 54s to 79.6s.
            </p>
            <button
              onClick={openWhyModal}
              className="w-full py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold font-heading text-xs transition-colors cursor-pointer"
            >
              LAUNCH EXPLAINABILITY (WHY S3?)
            </button>
          </div>
        )}

      </div>

      <div className="pt-4 border-t border-slate-800 text-[10px] text-slate-500">
        Digital Twin Computational Synchronized Stream • Latency 1.2ms
      </div>

    </div>
  );
};
