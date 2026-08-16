import React, { useState } from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Presentation,
  PlayCircle,
  PauseCircle,
  HelpCircle,
  Lightbulb,
  ExternalLink
} from 'lucide-react';
import { STORY_SCENES } from '../data/factoryData';

export const SceneGuidedTourBar: React.FC = () => {
  const {
    currentScene,
    currentSceneIndex,
    totalScenes,
    nextScene,
    prevScene,
    goToScene,
    autoTourPlaying,
    toggleAutoTour,
    openWhyModal,
    openWhatIfModal,
    openUncertaintyModal
  } = useFactorySimulation();

  const [showPresenterNotes, setShowPresenterNotes] = useState<boolean>(true);

  return (
    <div className="w-full bg-slate-950/95 border-b border-cyan-500/20 backdrop-blur-md px-4 py-2.5 shadow-md">
      <div className="max-w-7xl mx-auto flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3">
        
        {/* Left: Scene Step Badge & Pitch Tagline */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono text-[11px] font-semibold">
              <Presentation className="w-3 h-3 text-cyan-400" />
              SCENE {currentScene.id} / {totalScenes}
            </span>
            <h2 className="font-heading font-bold text-sm sm:text-base text-white tracking-wide truncate">
              {currentScene.title}
            </h2>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="font-mono text-cyan-300 font-medium tracking-tight">
              {currentScene.tagline}
            </span>
            <span className="hidden md:inline text-slate-500">•</span>
            <span className="hidden md:inline text-slate-300 italic text-[11px]">
              "{currentScene.keyStatement}"
            </span>
          </div>

          {/* Collapsible Pitch Narrator Note */}
          {showPresenterNotes && (
            <div className="mt-2 p-2 rounded-md bg-slate-900/90 border border-slate-800 text-[11px] text-slate-300 flex items-start gap-2 animate-fadeIn">
              <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex-1 leading-relaxed">
                <span className="font-mono text-amber-300 font-semibold uppercase text-[10px] mr-1">Pitch Audio Cue:</span>
                <span>{currentScene.narratorScript}</span>
              </div>
            </div>
          )}
        </div>

        {/* Right: Stepper controls & Scene timeline chips */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2.5 w-full lg:w-auto justify-between lg:justify-end shrink-0">
          
          {/* 12 Scene mini-dots */}
          <div className="flex items-center gap-1 bg-slate-900/90 px-2 py-1.5 rounded-lg border border-slate-800">
            {STORY_SCENES.map((scene, idx) => {
              const isCurrent = idx === currentSceneIndex;
              return (
                <button
                  key={scene.id}
                  onClick={() => goToScene(scene.id)}
                  title={`Scene ${scene.id}: ${scene.title}`}
                  className={`w-2.5 h-5 rounded-sm transition-all text-[9px] font-mono flex items-center justify-center ${
                    isCurrent
                      ? 'bg-cyan-400 text-slate-950 font-bold scale-110 shadow-sm shadow-cyan-400/50'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-500'
                  }`}
                >
                  {scene.id}
                </button>
              );
            })}
          </div>

          {/* Stepper Buttons */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setShowPresenterNotes((prev) => !prev)}
              className={`p-1.5 rounded text-xs border transition-colors ${
                showPresenterNotes
                  ? 'bg-amber-950/40 text-amber-300 border-amber-500/30'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
              }`}
              title="Toggle Presenter Speech Notes"
            >
              <Lightbulb className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={toggleAutoTour}
              className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-mono font-medium border transition-colors ${
                autoTourPlaying
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40 animate-pulse'
                  : 'bg-slate-900 text-slate-300 border-slate-800 hover:bg-slate-800'
              }`}
              title="Auto-advance scenes every 12 seconds"
            >
              {autoTourPlaying ? <PauseCircle className="w-3.5 h-3.5 text-cyan-400" /> : <PlayCircle className="w-3.5 h-3.5 text-slate-400" />}
              <span className="hidden sm:inline">AUTO TOUR</span>
            </button>

            <button
              id="btn-prev-scene"
              onClick={prevScene}
              disabled={currentSceneIndex === 0}
              className="p-1.5 rounded bg-slate-900 text-slate-300 border border-slate-800 hover:bg-slate-800 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Previous Scene"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <button
              id="btn-next-scene"
              onClick={nextScene}
              className="flex items-center gap-1 px-3 py-1.5 rounded bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-heading font-semibold shadow-md shadow-cyan-600/20 transition-all active:scale-95"
              title="Next Scene"
            >
              <span>NEXT SCENE</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

        </div>

      </div>
    </div>
  );
};
