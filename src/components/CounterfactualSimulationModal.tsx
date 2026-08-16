import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import { SIMULATION_SCENARIOS } from '../data/factoryData';
import { ScenarioId, SimulationScenario } from '../types';
import {
  GitBranch,
  X,
  CheckCircle2,
  AlertTriangle,
  Clock,
  DollarSign,
  TrendingUp,
  ShieldAlert,
  Sparkles,
  Zap,
  ArrowRight
} from 'lucide-react';

export const CounterfactualSimulationModal: React.FC = () => {
  const {
    isWhatIfModalOpen,
    closeWhatIfModal,
    activeScenarioId,
    setActiveScenarioId,
    applyIntervention,
    interventionApplied,
    revertIntervention
  } = useFactorySimulation();

  if (!isWhatIfModalOpen) return null;

  const scenarios = SIMULATION_SCENARIOS;
  const currentScenario = scenarios.find((s) => s.id === activeScenarioId) || scenarios[1];

  const handleApply = (scenarioId: ScenarioId) => {
    applyIntervention(scenarioId);
    closeWhatIfModal();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-5xl max-h-[92vh] bg-[#0c101a] border border-emerald-500/40 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-start justify-between gap-4 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/50 flex items-center justify-center">
              <GitBranch className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950 border border-emerald-500/30 text-emerald-300 font-bold">
                  COUNTERFACTUAL WHAT-IF ENGINE
                </span>
                <span className="text-xs font-mono text-slate-400">4 Parallel Virtual Futures Simulated</span>
              </div>
              <h2 className="font-heading font-bold text-xl text-white tracking-wide mt-0.5">
                SIMULATE ALTERNATIVE FUTURES & RECOMMEND INTERVENTION
              </h2>
            </div>
          </div>

          <button
            onClick={closeWhatIfModal}
            className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 4 Scenario Selection Cards */}
        <div className="p-5 overflow-y-auto space-y-5 flex-1">
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {scenarios.map((scen) => {
              const isSelected = activeScenarioId === scen.id;

              return (
                <div
                  key={scen.id}
                  onClick={() => setActiveScenarioId(scen.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? scen.isRecommended
                        ? 'bg-emerald-950/50 border-emerald-500 ring-2 ring-emerald-400/50 shadow-lg shadow-emerald-500/10'
                        : 'bg-slate-900 border-cyan-400 ring-2 ring-cyan-400/30'
                      : 'bg-slate-950/70 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5 font-mono text-[10px]">
                      <span className="text-slate-400 font-bold">{scen.label}</span>
                      {scen.isRecommended && (
                        <span className="px-1.5 py-0.2 rounded bg-emerald-500 text-slate-950 font-bold flex items-center gap-1">
                          <Sparkles className="w-2.5 h-2.5" />
                          AI OPTIMAL
                        </span>
                      )}
                    </div>

                    <h4 className="font-heading font-bold text-sm text-white mb-1">
                      {scen.name}
                    </h4>
                    <p className="text-[10px] text-slate-400 mb-3">
                      {scen.tagline}
                    </p>
                  </div>

                  {/* Summary Metrics */}
                  <div className="space-y-1 pt-2 border-t border-slate-800 font-mono text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Throughput Δ:</span>
                      <span className={`font-bold ${scen.throughputDeltaUPH >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {scen.throughputDeltaUPH > 0 ? `+${scen.throughputDeltaUPH}` : scen.throughputDeltaUPH} UPH
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-slate-400">Bottleneck Risk:</span>
                      <span className={`font-bold ${scen.bottleneckProbabilityT20 > 50 ? 'text-red-400' : 'text-emerald-400'}`}>
                        {scen.bottleneckProbabilityT20}%
                      </span>
                    </div>

                    <div className="flex justify-between">
                      <span className="text-slate-400">Downtime Cost:</span>
                      <span className="text-slate-200 font-semibold">
                        ${(scen.estimatedCostDowntime / 1000).toFixed(1)}k
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Selected Scenario Deep-Dive Panel */}
          <div className={`p-4 rounded-xl border font-mono ${
            currentScenario.isRecommended
              ? 'bg-emerald-950/30 border-emerald-500/40'
              : 'bg-slate-950/80 border-slate-800'
          }`}>
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-2 pb-3 mb-3 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-cyan-300">{currentScenario.label}: {currentScenario.name}</span>
                  {currentScenario.isRecommended && (
                    <span className="px-2 py-0.5 rounded bg-emerald-900 text-emerald-200 text-xs font-bold">
                      RECOMMENDED INTERVENTION
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                  {currentScenario.description}
                </p>
              </div>

              <div className="text-right shrink-0">
                <span className="text-[10px] text-slate-400 block">AI CONFIDENCE SCORE</span>
                <span className="text-base font-bold text-emerald-400">{currentScenario.confidenceScore}%</span>
              </div>
            </div>

            {/* Key Actions Checklist */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-300 block uppercase text-[11px]">
                Execution Protocols:
              </span>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
                {currentScenario.keyActions.map((action, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-200 flex items-start gap-2">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{action}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

        </div>

        {/* Modal Footer Actions */}
        <div className="p-4 bg-slate-950/90 border-t border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 font-mono text-xs">
          <div className="text-slate-400">
            <span>Decision Support Mode: <strong>Human-in-the-loop operator approval required</strong></span>
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            {interventionApplied && (
              <button
                onClick={() => {
                  revertIntervention();
                  closeWhatIfModal();
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-red-500/30 text-red-300 hover:bg-red-950"
              >
                REVERT TO BASELINE
              </button>
            )}

            <button
              onClick={closeWhatIfModal}
              className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white"
            >
              CLOSE
            </button>

            <button
              id="apply-to-twin-btn"
              onClick={() => handleApply(currentScenario.id)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-heading font-bold shadow-md shadow-emerald-600/25 active:scale-95 transition-all"
            >
              <Zap className="w-4 h-4" />
              <span>APPLY {currentScenario.label} TO DIGITAL TWIN</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
