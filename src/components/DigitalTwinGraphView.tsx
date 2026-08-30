import React, { useState } from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import { StationId } from '../types';
import {
  BrainCircuit,
  Cpu,
  GitCommit,
  Layers,
  Network,
  Sparkles,
  Zap,
  Clock,
  Car
} from 'lucide-react';

export const DigitalTwinGraphView: React.FC = () => {
  const {
    stations,
    vehicles,
    selectStationById,
    selectVehicleById,
    interventionApplied,
    trajectoryData,
    explainabilityData
  } = useFactorySimulation();

  const [activeTab, setActiveTab] = useState<'SPATIAL' | 'TEMPORAL' | 'CROSS_ATTN'>('SPATIAL');
  const [hoveredStation, setHoveredStation] = useState<StationId | null>('S3');

  const timeSteps = (trajectoryData && trajectoryData.length > 0)
    ? trajectoryData.map((pt) => {
        const isCurrent = pt.timeOffsetMin === 0;
        const isForecast = pt.timeOffsetMin > 0;
        const type = isCurrent ? 'CURRENT' : (isForecast ? 'FORECAST' : 'HISTORICAL');
        const attention = isCurrent ? 1.0 : (isForecast ? Math.max(0.6, 1.0 - pt.timeOffsetMin * 0.015) : Math.min(0.9, 0.15 + (pt.timeOffsetMin + 60) * 0.012));
        
        let note = `Observed: ${pt.observed.toFixed(1)}s (δ ${pt.deltaT >= 0 ? '+' : ''}${pt.deltaT.toFixed(1)}s)`;
        if (isCurrent) note = `Active δ(t) = +${pt.deltaT.toFixed(1)}s | Alert Issued`;
        else if (isForecast) note = `DES Projection: ${pt.observed.toFixed(1)}s [±${((pt.upperBand - pt.lowerBand)/2).toFixed(1)}s]`;
        
        return {
          label: pt.timestampLabel,
          type,
          attention: Number(attention.toFixed(2)),
          note
        };
      })
    : [
        { label: 'T-60m', type: 'HISTORICAL', attention: 0.12, note: 'Nominal DES baseline' },
        { label: 'T-50m', type: 'HISTORICAL', attention: 0.18, note: 'Normal variance' },
        { label: 'T-40m', type: 'HISTORICAL', attention: 0.28, note: 'Micro-vibration inception' },
        { label: 'T-30m', type: 'HISTORICAL', attention: 0.44, note: 'Cycle time +2.8s' },
        { label: 'T-20m', type: 'HISTORICAL', attention: 0.68, note: 'Spindle #4 torque variance ↑' },
        { label: 'T-10m', type: 'HISTORICAL', attention: 0.86, note: 'δ(t) reaches 15.4s' },
        { label: 'NOW (T-0)', type: 'CURRENT', attention: 1.0, note: '87% Bottleneck Alert Issued' },
        { label: 'T+5m', type: 'FORECAST', attention: 0.94, note: 'Queue locks to 5/5 buffer' },
        { label: 'T+10m', type: 'FORECAST', attention: 0.88, note: 'S2 Paint upstream blocked' },
        { label: 'T+14m', type: 'FORECAST', attention: 0.82, note: 'Predicted Hard Stoppage' },
        { label: 'T+20m', type: 'FORECAST', attention: 0.75, note: 'Downstream S4 full starved' }
      ];

  return (
    <div className="w-full bg-[#080B11] p-4 lg:p-6 rounded-2xl border border-purple-500/30 shadow-2xl relative overflow-hidden">
      
      {/* Background Ambience */}
      <div className="absolute top-0 right-1/4 w-80 h-80 bg-purple-600/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-80 h-80 bg-cyan-600/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-5 h-5 text-purple-400" />
            <h3 className="font-heading font-bold text-lg text-white tracking-wider">
              SPATIO-TEMPORAL AI ARCHITECTURE
            </h3>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950/80 border border-purple-500/40 text-purple-300 font-semibold">
              GATv2 + TEMPORAL TRANSFORMER
            </span>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Hierarchical Graph Attention for Factory Topologies & Non-Linear Trajectory Forecasting
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center bg-slate-900/90 p-1 rounded-lg border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveTab('SPATIAL')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
              activeTab === 'SPATIAL'
                ? 'bg-purple-900/60 text-purple-200 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>GATv2 SPATIAL ATTENTION</span>
          </button>

          <button
            onClick={() => setActiveTab('TEMPORAL')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
              activeTab === 'TEMPORAL'
                ? 'bg-purple-900/60 text-purple-200 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>TEMPORAL TRANSFORMER</span>
          </button>

          <button
            onClick={() => setActiveTab('CROSS_ATTN')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-all ${
              activeTab === 'CROSS_ATTN'
                ? 'bg-purple-900/60 text-purple-200 border border-purple-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Car className="w-3.5 h-3.5" />
            <span>VEHICLE ↔ STATION CROSS-ATTENTION</span>
          </button>
        </div>
      </div>

      {/* TAB 1: GATv2 Spatial Attention Graph */}
      {activeTab === 'SPATIAL' && (
        <div className="space-y-4">
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 flex items-center justify-between">
            <span className="text-purple-300 font-semibold">
              Spatial Attention Query: "Which neighboring stations and buffers directly influence S3 Chassis Marriage?"
            </span>
            <span className="text-slate-500">Softmax Edge Weights (α_ij)</span>
          </div>

          {/* Interactive Graph Diagram */}
          <div className="grid grid-cols-1 lg:grid-cols-6 gap-3">
            {stations.map((st) => {
              const isTargetS3 = st.id === 'S3';
              const attentionToS3 = st.attentionWeights['S3'] || 0.1;
              const isHovered = hoveredStation === st.id;

              return (
                <div
                  key={st.id}
                  onMouseEnter={() => setHoveredStation(st.id)}
                  onClick={() => selectStationById(st.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                    isTargetS3
                      ? 'bg-amber-950/40 border-amber-500/60 ring-2 ring-amber-400/40 shadow-xl shadow-amber-500/10'
                      : isHovered
                      ? 'bg-purple-950/40 border-purple-500/60'
                      : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between text-xs font-mono mb-2">
                      <span className="font-bold text-cyan-400">{st.id}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-purple-300">
                        α={st.attentionWeights[st.id]?.toFixed(2) || '0.30'}
                      </span>
                    </div>

                    <h4 className="font-heading font-bold text-sm text-white mb-1">
                      {st.name}
                    </h4>
                    <p className="text-[10px] text-slate-400 mb-3">
                      {st.sensorCount} Telemetry Feeds
                    </p>
                  </div>

                  {/* Spatial Attention Influence Bar to S3 */}
                  <div className="pt-2 border-t border-slate-800/80 font-mono text-[10px]">
                    <div className="flex justify-between text-slate-400 mb-1">
                      <span>Influence on S3:</span>
                      <span className="font-bold text-purple-300">{(attentionToS3 * 100).toFixed(0)}%</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-cyan-400 to-purple-500 rounded-full transition-all duration-500"
                        style={{ width: `${attentionToS3 * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-3 bg-purple-950/30 rounded-xl border border-purple-500/30 text-xs font-mono text-purple-200">
            <strong>GATv2 Graph Inference:</strong> Graph node embeddings aggregate physical constraints: Upstream S2 Paint buffer pressure provides 38% spatial coupling into S3, while S4 Powertrain reflects a 12% downstream starvation pull.
          </div>
        </div>
      )}

      {/* TAB 2: Temporal Transformer Timeline */}
      {activeTab === 'TEMPORAL' && (
        <div className="space-y-4">
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 flex items-center justify-between">
            <span className="text-purple-300 font-semibold">
              Temporal Self-Attention Query: "How will historical micro-vibration & torque deviations propagate forward into T+20 min?"
            </span>
            <span className="text-slate-500">Multi-Head Causal Attention</span>
          </div>

          {/* Timeline Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 lg:grid-cols-11 gap-2">
            {timeSteps.map((step, idx) => {
              const isNow = step.type === 'CURRENT';
              const isForecast = step.type === 'FORECAST';

              return (
                <div
                  key={step.label}
                  className={`p-2.5 rounded-lg border font-mono text-[10px] transition-all flex flex-col justify-between ${
                    isNow
                      ? 'bg-amber-950/80 border-amber-500 shadow-md ring-1 ring-amber-400/50'
                      : isForecast
                      ? 'bg-purple-950/40 border-purple-500/30'
                      : 'bg-slate-900/60 border-slate-800'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className={`font-bold ${isNow ? 'text-amber-300' : isForecast ? 'text-purple-300' : 'text-slate-400'}`}>
                        {step.label}
                      </span>
                    </div>
                    <span className={`text-[8px] px-1 py-0.2 rounded font-semibold uppercase ${
                      isNow ? 'bg-amber-900 text-amber-200' : isForecast ? 'bg-purple-900/80 text-purple-200' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {step.type}
                    </span>
                    <p className="text-[9px] text-slate-300 mt-2 leading-tight">
                      {step.note}
                    </p>
                  </div>

                  <div className="mt-3 pt-1 border-t border-slate-800 text-[8px] text-slate-500 flex justify-between">
                    <span>Attn:</span>
                    <span className="text-cyan-400 font-bold">{step.attention.toFixed(2)}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="p-3 bg-cyan-950/30 rounded-xl border border-cyan-500/30 text-xs font-mono text-cyan-200">
            <strong>Temporal Transformer Synthesis:</strong> The temporal horizon captures the rate of change (dδ(t)/dt). By projecting non-linear momentum at T-14m, the model anticipates catastrophic buffer saturation at T+14m before the physical line stalls.
          </div>
        </div>
      )}

      {/* TAB 3: Vehicle ↔ Station Cross-Attention */}
      {activeTab === 'CROSS_ATTN' && (
        <div className="space-y-4">
          <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800 text-xs font-mono text-slate-300">
            <span className="text-purple-300 font-semibold">
              Cross-Attention: "Linking individual vehicle build complexity (SUV vs Sedan) with station mechanical stress."
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {vehicles.slice(0, 4).map((veh) => {
              return (
                <div
                  key={veh.id}
                  onClick={() => selectVehicleById(veh.id)}
                  className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/70 hover:border-cyan-500/40 transition-all cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs font-mono mb-2">
                    <span className="font-bold text-cyan-400">{veh.id}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      veh.qualityExposure === 'HIGH' ? 'bg-red-900/80 text-red-200' :
                      veh.qualityExposure === 'MEDIUM' ? 'bg-amber-900/80 text-amber-200' : 'bg-cyan-950 text-cyan-300'
                    }`}>
                      {veh.qualityExposure} EXPOSURE
                    </span>
                  </div>

                  <h4 className="font-heading font-bold text-sm text-white">{veh.model}</h4>
                  <p className="text-[10px] font-mono text-slate-400 mb-2">{veh.vin}</p>

                  <div className="space-y-1.5 pt-2 border-t border-slate-800 font-mono text-[10px]">
                    <div className="flex justify-between text-slate-300">
                      <span>S3 Experienced Torque:</span>
                      <span className={veh.riskScore > 50 ? 'text-red-400 font-bold' : 'text-slate-400'}>
                        {veh.history.find((h) => h.stationId === 'S3')?.torqueVariance?.toFixed(2) || '0.22'} A²
                      </span>
                    </div>
                    <div className="flex justify-between text-slate-300">
                      <span>Defect Probability:</span>
                      <span className={veh.riskScore > 50 ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                        {veh.predictedQualityDefectProbability}%
                      </span>
                    </div>
                    {veh.keyAnomalyNote && (
                      <p className="text-[9px] text-amber-300 italic pt-1 border-t border-slate-800/60">
                        {veh.keyAnomalyNote}
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
};
