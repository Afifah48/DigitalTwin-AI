import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  Activity,
  Cpu,
  Layers,
  LayoutGrid,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  HelpCircle,
  GitBranch,
  ShieldAlert,
  Sparkles,
  ChevronRight
} from 'lucide-react';
import { AppViewMode } from '../types';

export const Header: React.FC = () => {
  const {
    viewMode,
    setViewMode,
    isPlaying,
    togglePlay,
    simSpeed,
    setSimSpeed,
    resetSimulation,
    simTimeSec,
    countdownSec,
    openWhyModal,
    openWhatIfModal,
    openUncertaintyModal,
    isSoundMuted,
    toggleSound,
    interventionApplied,
    currentScene,
    nextScene
  } = useFactorySimulation();

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const navItems: { id: AppViewMode; label: string; icon: React.ReactNode }[] = [
    { id: 'LIVE_FACTORY', label: 'PHYSICAL LINE', icon: <Activity className="w-4 h-4 text-cyan-400" /> },
    { id: 'SYNCHRONIZED', label: 'SYNCHRONIZED TWIN', icon: <Layers className="w-4 h-4 text-cyan-300" /> },
    { id: 'DIGITAL_TWIN', label: 'COMPUTATIONAL TWIN', icon: <Cpu className="w-4 h-4 text-purple-400" /> },
    { id: 'COMMAND_CENTER', label: 'COMMAND MATRIX', icon: <LayoutGrid className="w-4 h-4 text-emerald-400" /> }
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800/80 bg-[#080B11]/90 backdrop-blur-xl px-4 py-2.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        
        {/* Brand & Factory Status */}
        <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-start">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 via-blue-600 to-indigo-700 p-0.5 shadow-lg shadow-cyan-500/20 flex items-center justify-center">
              <div className="w-full h-full bg-[#080B11] rounded-[7px] flex items-center justify-center">
                <Cpu className="w-4 h-4 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-heading font-bold tracking-wider text-base text-white">DIGITALTWIN<span className="text-cyan-400">.AI</span></span>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-cyan-950/80 border border-cyan-500/30 text-cyan-300 font-mono font-medium">v3.4 PROTOTYPE</span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono tracking-tight hidden sm:block">
                AUTONOMOUS AUTOMOTIVE MANUFACTURING PREDICTIVE CONTROL
              </p>
            </div>
          </div>

          {/* Live Sync Beacon */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-900/90 border border-slate-700/60 text-xs font-mono">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
            <span className="text-cyan-300 text-[11px] font-medium tracking-wide">● LIVE FACTORY SYNC</span>
            <span className="text-slate-500 text-[10px]">| 100Hz</span>
          </div>
        </div>

        {/* View Mode Navigation Tabs */}
        <div className="flex items-center bg-slate-950/80 p-1 rounded-lg border border-slate-800">
          {navItems.map((item) => {
            const isActive = viewMode === item.id;
            return (
              <button
                key={item.id}
                id={`nav-${item.id.toLowerCase()}`}
                onClick={() => setViewMode(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-heading font-medium tracking-wide transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-slate-800 to-slate-800/90 text-white border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
                }`}
              >
                {item.icon}
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Quick Analytical Deep Dive Shortcuts & Simulation Controls */}
        <div className="flex items-center gap-2">
          {/* Quick AI Action Buttons */}
          <div className="hidden lg:flex items-center gap-1.5 border-r border-slate-800 pr-2">
            <button
              id="header-why-btn"
              onClick={openWhyModal}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-amber-950/40 hover:bg-amber-900/60 border border-amber-500/40 text-amber-300 text-[11px] font-mono transition-colors"
              title="Explain Root Cause Attribution"
            >
              <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
              <span>WHY S3?</span>
            </button>

            <button
              id="header-whatif-btn"
              onClick={() => openWhatIfModal()}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-emerald-950/40 hover:bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 text-[11px] font-mono transition-colors"
              title="Run 4 Counterfactual Scenarios"
            >
              <GitBranch className="w-3.5 h-3.5 text-emerald-400" />
              <span>WHAT IF?</span>
            </button>

            <button
              id="header-confidence-btn"
              onClick={openUncertaintyModal}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-purple-950/40 hover:bg-purple-900/60 border border-purple-500/40 text-purple-300 text-[11px] font-mono transition-colors"
              title="Monte Carlo Dropout Uncertainty Analysis"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-purple-400" />
              <span>UNCERTAINTY</span>
            </button>
          </div>

          {/* Time & Playback Controls */}
          <div className="flex items-center gap-1.5 bg-slate-900/80 px-2 py-1 rounded-md border border-slate-800">
            <button
              id="playback-toggle-btn"
              onClick={togglePlay}
              className="p-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors"
              title={isPlaying ? 'Pause Simulation' : 'Resume Simulation'}
            >
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 text-cyan-400" />}
            </button>

            {/* Speed Multiplier */}
            <div className="flex items-center gap-0.5">
              {([1, 2, 5] as const).map((spd) => (
                <button
                  key={spd}
                  onClick={() => setSimSpeed(spd)}
                  className={`px-1.5 py-0.5 rounded text-[10px] font-mono ${
                    simSpeed === spd
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>

            <button
              id="reset-sim-btn"
              onClick={resetSimulation}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title="Reset Simulation State"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <button
              id="toggle-audio-btn"
              onClick={toggleSound}
              className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
              title={isSoundMuted ? 'Unmute Industrial Telemetry Audio' : 'Mute Audio'}
            >
              {isSoundMuted ? <VolumeX className="w-3.5 h-3.5 text-slate-500" /> : <Volume2 className="w-3.5 h-3.5 text-cyan-400" />}
            </button>
          </div>
        </div>

      </div>
    </header>
  );
};
