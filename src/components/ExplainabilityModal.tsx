import React, { useState } from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import { EXPLAINABILITY_DATA } from '../data/factoryData';
import {
  HelpCircle,
  X,
  Network,
  Clock,
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  GitBranch,
  ArrowRight
} from 'lucide-react';

export const ExplainabilityModal: React.FC = () => {
  const { isWhyModalOpen, closeWhyModal, openWhatIfModal, explainabilityData } = useFactorySimulation();
  const [activeTab, setActiveTab] = useState<'FEATURE' | 'SPATIAL' | 'TEMPORAL'>('FEATURE');

  if (!isWhyModalOpen) return null;

  const { featureAttributions, spatialAttribution, temporalAttribution } = explainabilityData;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-[#0c101a] border border-amber-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between gap-4 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/50 flex items-center justify-center">
              <HelpCircle className="w-5 h-5 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-amber-950 border border-amber-500/30 text-amber-300 font-bold">
                  EXPLAINABLE AI (XAI)
                </span>
                <span className="text-xs font-mono text-slate-400">Attribution Engine v4.1</span>
              </div>
              <h2 className="font-heading font-bold text-xl text-white tracking-wide mt-0.5">
                WHY S3? ROOT CAUSE EVIDENCE & ATTRIBUTION
              </h2>
            </div>
          </div>

          <button
            onClick={closeWhyModal}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-5 py-2.5 bg-slate-900/50 border-b border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveTab('FEATURE')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'FEATURE'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BarChart3 className="w-3.5 h-3.5" />
            <span>FEATURE IMPORTANCE (SHAP)</span>
          </button>

          <button
            onClick={() => setActiveTab('SPATIAL')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'SPATIAL'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-3.5 h-3.5" />
            <span>SPATIAL ATTRIBUTION</span>
          </button>

          <button
            onClick={() => setActiveTab('TEMPORAL')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-all ${
              activeTab === 'TEMPORAL'
                ? 'bg-amber-500 text-slate-950 font-bold shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock className="w-3.5 h-3.5" />
            <span>TEMPORAL TIMELINE</span>
          </button>
        </div>

        {/* Modal Body Content */}
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          
          {/* TAB 1: Feature Importance */}
          {activeTab === 'FEATURE' && (
            <div className="space-y-4">
              <p className="text-xs font-mono text-slate-300">
                Ranked SHAP feature contributions isolating the sensory signals that shifted S3 beyond nominal threshold bounds:
              </p>

              <div className="space-y-3">
                {featureAttributions.map((feat, idx) => (
                  <div
                    key={feat.feature}
                    className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-amber-500/40 transition-all font-mono"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-full bg-slate-800 text-amber-400 text-xs font-bold flex items-center justify-center">
                          {idx + 1}
                        </span>
                        <span className="font-bold text-sm text-white">{feat.feature}</span>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-amber-400 font-bold">Delta: {feat.delta}</span>
                        <span className="text-slate-500">•</span>
                        <span className="text-purple-300 font-bold">{feat.importance}% Importance</span>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-gradient-to-r from-amber-500 to-red-500 rounded-full"
                        style={{ width: `${feat.importance}%` }}
                      />
                    </div>

                    <p className="text-[11px] text-slate-400 leading-relaxed">
                      {feat.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: Spatial Attribution */}
          {activeTab === 'SPATIAL' && (
            <div className="space-y-4">
              <p className="text-xs font-mono text-slate-300">
                GATv2 Graph topology breakdown: identifying which stations exerted upstream pressure or experienced downstream starvation:
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {spatialAttribution.map((sp) => (
                  <div
                    key={sp.stationId}
                    className={`p-4 rounded-xl border font-mono text-xs ${
                      sp.role === 'PRIMARY_SOURCE'
                        ? 'bg-red-950/40 border-red-500/50'
                        : sp.role === 'UPSTREAM_BACKLOG'
                        ? 'bg-amber-950/40 border-amber-500/40'
                        : 'bg-slate-950/80 border-slate-800'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-1.5">
                        <span className="font-bold text-cyan-400">{sp.stationId}</span>
                        <span className="text-white font-bold">{sp.stationName}</span>
                      </div>
                      <span className="text-purple-300 font-bold">{sp.influenceWeight}% Influence</span>
                    </div>

                    <span className={`inline-block px-1.5 py-0.5 rounded text-[9px] font-bold uppercase mb-2 ${
                      sp.role === 'PRIMARY_SOURCE' ? 'bg-red-900 text-red-200' :
                      sp.role === 'UPSTREAM_BACKLOG' ? 'bg-amber-900 text-amber-200' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {sp.role.replace('_', ' ')}
                    </span>

                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {sp.reason}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: Temporal Timeline */}
          {activeTab === 'TEMPORAL' && (
            <div className="space-y-4">
              <p className="text-xs font-mono text-slate-300">
                Chronological degradation path showing the gradual emergence of the bottleneck:
              </p>

              <div className="space-y-3 relative pl-6 border-l border-slate-800">
                {temporalAttribution.map((item) => (
                  <div key={item.timeLabel} className="relative font-mono text-xs">
                    {/* Circle on timeline */}
                    <span className={`absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 border-[#0c101a] ${
                      item.anomalySeverity === 'HIGH' ? 'bg-red-500 ring-2 ring-red-500/40' :
                      item.anomalySeverity === 'MEDIUM' ? 'bg-amber-500' : 'bg-cyan-400'
                    }`} />

                    <div className="p-3 bg-slate-950/80 rounded-xl border border-slate-800">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-bold text-amber-300">{item.timeLabel}</span>
                        <span className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${
                          item.anomalySeverity === 'HIGH' ? 'bg-red-950 text-red-300 border border-red-500/30' :
                          item.anomalySeverity === 'MEDIUM' ? 'bg-amber-950 text-amber-300' : 'bg-slate-800 text-slate-400'
                        }`}>
                          {item.anomalySeverity} SEVERITY
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300">{item.event}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-950/90 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 font-mono text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Root cause verified with <strong>98% sensor confidence</strong></span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={closeWhyModal}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white"
            >
              DISMISS
            </button>
            <button
              onClick={() => {
                closeWhyModal();
                openWhatIfModal();
              }}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-md shadow-emerald-600/20"
            >
              <GitBranch className="w-3.5 h-3.5" />
              <span>SIMULATE COUNTERFACTUAL WHAT-IF</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
