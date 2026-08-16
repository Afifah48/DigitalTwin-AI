import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  Car,
  X,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Activity,
  Layers,
  Wrench,
  ShieldCheck,
  Zap
} from 'lucide-react';

export const VehicleInspectorDrawer: React.FC = () => {
  const { selectedVehicle, setSelectedVehicle } = useFactorySimulation();

  if (!selectedVehicle) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#0b0f19] border-l border-cyan-500/30 shadow-2xl overflow-y-auto p-5 font-mono text-xs animate-slideLeft flex flex-col justify-between">
      
      <div>
        {/* Header */}
        <div className="flex items-start justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-cyan-500/20 border border-cyan-500/50 flex items-center justify-center">
              <Car className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-cyan-400 font-bold text-sm">{selectedVehicle.id}</span>
                <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                  selectedVehicle.qualityExposure === 'HIGH' ? 'bg-red-950 text-red-300 border border-red-500/40' :
                  selectedVehicle.qualityExposure === 'MEDIUM' ? 'bg-amber-950 text-amber-300 border border-amber-500/40' :
                  'bg-emerald-950 text-emerald-300 border border-emerald-500/40'
                }`}>
                  {selectedVehicle.qualityExposure} EXPOSURE
                </span>
              </div>
              <p className="text-slate-400 text-[10px] mt-0.5">{selectedVehicle.vin}</p>
            </div>
          </div>

          <button
            onClick={() => setSelectedVehicle(null)}
            className="p-1 rounded bg-slate-900 border border-slate-800 text-slate-400 hover:text-white"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Vehicle Specs */}
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 mb-4 space-y-2">
          <div className="flex justify-between">
            <span className="text-slate-400">Model:</span>
            <span className="text-white font-bold">{selectedVehicle.model}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Color Variant:</span>
            <span className="text-slate-200 flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: selectedVehicle.color }} />
              {selectedVehicle.colorName}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Current Station:</span>
            <span className="text-cyan-400 font-bold">{selectedVehicle.currentStationId || 'Transit'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Total Transit Time:</span>
            <span className="text-slate-200">{selectedVehicle.totalTransitTime} seconds</span>
          </div>
        </div>

        {/* Quality Risk Exposure Index */}
        <div className={`p-4 rounded-xl border mb-4 ${
          selectedVehicle.qualityExposure === 'HIGH' ? 'bg-red-950/40 border-red-500/40' :
          selectedVehicle.qualityExposure === 'MEDIUM' ? 'bg-amber-950/40 border-amber-500/40' : 'bg-slate-950 border-slate-800'
        }`}>
          <div className="flex justify-between items-center mb-2">
            <span className="text-slate-300 font-bold">PREDICTED QUALITY RISK INDEX</span>
            <span className={`text-base font-bold ${
              selectedVehicle.riskScore > 50 ? 'text-red-400' : 'text-emerald-400'
            }`}>
              {selectedVehicle.riskScore} / 100
            </span>
          </div>

          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mb-2">
            <div
              className={`h-full rounded-full ${
                selectedVehicle.riskScore > 70 ? 'bg-red-500' :
                selectedVehicle.riskScore > 30 ? 'bg-amber-400' : 'bg-emerald-400'
              }`}
              style={{ width: `${selectedVehicle.riskScore}%` }}
            />
          </div>

          <div className="flex justify-between text-[10px] text-slate-400">
            <span>Defect Probability: <strong className="text-slate-200">{selectedVehicle.predictedQualityDefectProbability}%</strong></span>
            <span>90% CI: [±4.2%]</span>
          </div>

          {selectedVehicle.keyAnomalyNote && (
            <p className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] text-amber-300">
              {selectedVehicle.keyAnomalyNote}
            </p>
          )}
        </div>

        {/* Station Transit History */}
        <div>
          <h4 className="text-slate-400 uppercase text-[10px] tracking-wider mb-2 font-bold">
            STATION TRANSIT HISTORY & SENSOR TELEMETRY
          </h4>
          <div className="space-y-2">
            {selectedVehicle.history.map((h) => (
              <div key={h.stationId} className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex justify-between items-center text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-cyan-400">{h.stationId}</span>
                  <span className="text-slate-300">{h.actualCycleTime}s (exp {h.expectedCycleTime}s)</span>
                </div>
                <div className="text-right">
                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                    h.exposureFlag === 'HIGH' ? 'bg-red-950 text-red-300' :
                    h.exposureFlag === 'MEDIUM' ? 'bg-amber-950 text-amber-300' : 'bg-slate-900 text-slate-400'
                  }`}>
                    {h.exposureFlag} EXPOSURE
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Footer Routing Action */}
      <div className="pt-4 mt-4 border-t border-slate-800">
        {selectedVehicle.qaRoutingRequired ? (
          <div className="p-3 rounded-lg bg-red-950/60 border border-red-500/40 text-red-200 flex items-center justify-between">
            <span className="font-bold text-[11px]">Automated S6 QA Re-check Flagged</span>
            <ShieldCheck className="w-4 h-4 text-red-400" />
          </div>
        ) : (
          <div className="p-3 rounded-lg bg-emerald-950/60 border border-emerald-500/40 text-emerald-200 flex items-center justify-between">
            <span className="font-bold text-[11px]">Nominal Line Transit Approved</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
        )}
      </div>

    </div>
  );
};
