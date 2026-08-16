import React from 'react';
import { FactorySimulationProvider, useFactorySimulation } from './context/FactorySimulationContext';
import { Header } from './components/Header';
import { SceneGuidedTourBar } from './components/SceneGuidedTourBar';
import { FactoryLineCanvas } from './components/FactoryLineCanvas';
import { DigitalTwinGraphView } from './components/DigitalTwinGraphView';
import { TrajectoryDeviationChart } from './components/TrajectoryDeviationChart';
import { PredictiveBottleneckCard } from './components/PredictiveBottleneckCard';
import { BottleneckMigrationView } from './components/BottleneckMigrationView';
import { CommandCenterMatrix } from './components/CommandCenterMatrix';
import { ExplainabilityModal } from './components/ExplainabilityModal';
import { CounterfactualSimulationModal } from './components/CounterfactualSimulationModal';
import { UncertaintyViewModal } from './components/UncertaintyViewModal';
import { VehicleInspectorDrawer } from './components/VehicleInspectorDrawer';
import { StationDetailDrawer } from './components/StationDetailDrawer';
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  CheckCircle2,
  Cpu,
  GitBranch,
  Layers,
  Sparkles,
  ShieldCheck,
  Zap,
  HelpCircle
} from 'lucide-react';

const MainContent: React.FC = () => {
  const {
    viewMode,
    currentScene,
    openWhyModal,
    openWhatIfModal,
    openUncertaintyModal
  } = useFactorySimulation();

  return (
    <main className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      
      {/* Dynamic View Mode Router */}
      {viewMode === 'COMMAND_CENTER' ? (
        <CommandCenterMatrix />
      ) : viewMode === 'DIGITAL_TWIN' ? (
        <div className="space-y-6">
          <PredictiveBottleneckCard />
          <DigitalTwinGraphView />
          <TrajectoryDeviationChart />
          <BottleneckMigrationView />
        </div>
      ) : viewMode === 'SYNCHRONIZED' ? (
        <div className="space-y-6">
          <FactoryLineCanvas />
          <PredictiveBottleneckCard />
          <TrajectoryDeviationChart />
          <BottleneckMigrationView />
        </div>
      ) : (
        /* LIVE_FACTORY View */
        <div className="space-y-6">
          <FactoryLineCanvas />
          <PredictiveBottleneckCard />
          <TrajectoryDeviationChart />
        </div>
      )}

      {/* Global Hackathon Manifesto & Causal Architecture Footer */}
      <footer className="w-full mt-10 p-6 rounded-2xl bg-[#0b0e17] border border-slate-800 shadow-2xl relative overflow-hidden font-mono">
        <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-heading font-bold text-lg text-white">DIGITALTWIN<span className="text-cyan-400">.AI</span></span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/30 text-cyan-300 font-semibold">
                END-TO-END PREDICTIVE OPERATING SYSTEM
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Transforming automotive factories from reactive alarm response into anticipatory cyber-physical intervention.
            </p>
          </div>

          {/* Core Pipeline Ribbon */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-slate-300">
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400">OBSERVE</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-300">SYNCHRONIZE</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-amber-300">PREDICT</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-purple-300">EXPLAIN</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-emerald-400">SIMULATE</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-600" />
            <span className="px-2.5 py-1 rounded bg-emerald-950 border border-emerald-500/40 text-emerald-300">INTERVENE</span>
          </div>
        </div>

        {/* Final Hero Quotation */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-center sm:text-left">
          <div className="text-xs text-slate-300 italic">
            “Predict the trajectory. Explain the cause. Simulate the consequence. Intervene before the bottleneck arrives.”
          </div>

          <div className="text-[10px] text-slate-500">
            SIMULATED DATA • CONCEPT PROTOTYPE FOR HACKATHON PITCH
          </div>
        </div>
      </footer>

      {/* Global Interactive Drawers & Modals */}
      <ExplainabilityModal />
      <CounterfactualSimulationModal />
      <UncertaintyViewModal />
      <VehicleInspectorDrawer />
      <StationDetailDrawer />

    </main>
  );
};

export default function App() {
  return (
    <FactorySimulationProvider>
      <div className="min-h-screen bg-[#080B11] text-slate-100 flex flex-col">
        <Header />
        <SceneGuidedTourBar />
        <MainContent />
      </div>
    </FactorySimulationProvider>
  );
}
