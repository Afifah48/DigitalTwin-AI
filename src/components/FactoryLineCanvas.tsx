import React from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import {
  StationData,
  StationId,
  Vehicle,
  ExposureLevel
} from '../types';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Eye,
  Flame,
  Layers,
  Sparkles,
  Timer,
  TrendingUp,
  Wrench,
  Zap
} from 'lucide-react';

export const FactoryLineCanvas: React.FC = () => {
  const {
    stations,
    vehicles,
    viewMode,
    selectStationById,
    selectVehicleById,
    selectedStation,
    selectedVehicle,
    interventionApplied,
    countdownSec,
    openWhyModal,
    openWhatIfModal
  } = useFactorySimulation();

  const isSynchronized = viewMode === 'SYNCHRONIZED';
  const isDigitalTwinOnly = viewMode === 'DIGITAL_TWIN';

  const formatCountdown = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Helper to render vehicle icon / styling
  const renderVehicleBadge = (vehicle: Vehicle, isTwin: boolean = false) => {
    const isSelected = selectedVehicle?.id === vehicle.id;
    const exposureColors = {
      LOW: 'border-cyan-500/40 bg-cyan-950/80 text-cyan-200',
      MEDIUM: 'border-amber-500/80 bg-amber-950/90 text-amber-200 shadow-sm shadow-amber-500/30',
      HIGH: 'border-red-500 bg-red-950 text-red-200 shadow-md shadow-red-500/50 animate-pulse'
    };

    return (
      <button
        key={`${vehicle.id}-${isTwin ? 'twin' : 'phys'}`}
        id={`vehicle-btn-${vehicle.id.toLowerCase()}`}
        onClick={(e) => {
          e.stopPropagation();
          selectVehicleById(vehicle.id);
        }}
        className={`group relative flex flex-col items-center p-1.5 rounded-lg border transition-all cursor-pointer ${
          exposureColors[vehicle.qualityExposure]
        } ${isSelected ? 'ring-2 ring-cyan-400 scale-105 z-20' : 'hover:scale-102'} ${
          isTwin ? 'backdrop-blur-md bg-slate-900/90' : ''
        }`}
        title={`Click to inspect vehicle telemetry & quality risk: ${vehicle.id} (${vehicle.model})`}
      >
        {/* Car Silhouette / Top View SVG representation */}
        <div className="relative w-16 h-8 flex items-center justify-center">
          <svg viewBox="0 0 64 32" className="w-full h-full drop-shadow">
            {/* Chassis outline */}
            <rect
              x="6"
              y="4"
              width="52"
              height="24"
              rx="6"
              fill={isTwin ? '#1e293b' : vehicle.color}
              stroke={isTwin ? '#38bdf8' : '#ffffff'}
              strokeWidth={isTwin ? '1.5' : '0.8'}
              strokeDasharray={isTwin ? '3 1' : 'none'}
              opacity={isTwin ? 0.85 : 0.95}
            />
            {/* Windshield */}
            <polygon points="20,8 36,8 34,14 22,14" fill="#0f172a" opacity="0.8" />
            {/* Rear Window */}
            <polygon points="42,9 50,9 49,13 43,13" fill="#0f172a" opacity="0.8" />
            {/* Headlights */}
            <circle cx="8" cy="8" r="1.5" fill="#38bdf8" />
            <circle cx="8" cy="24" r="1.5" fill="#38bdf8" />
            {/* Wheels */}
            <rect x="14" y="2" width="8" height="3" rx="1" fill="#090d16" />
            <rect x="42" y="2" width="8" height="3" rx="1" fill="#090d16" />
            <rect x="14" y="27" width="8" height="3" rx="1" fill="#090d16" />
            <rect x="42" y="27" width="8" height="3" rx="1" fill="#090d16" />
          </svg>

          {/* Exposure Alert Icon if High/Med */}
          {vehicle.qualityExposure !== 'LOW' && (
            <span className="absolute -top-1.5 -right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-600 text-[9px] font-bold text-white shadow">
              !
            </span>
          )}
        </div>

        {/* Vehicle ID & Progress */}
        <div className="flex items-center gap-1 mt-1 font-mono text-[10px] font-semibold">
          <span>{vehicle.id}</span>
          <span className="text-[8px] text-slate-400">({Math.round(vehicle.progressInStation)}%)</span>
        </div>

        {/* Tooltip on Hover */}
        <div className="absolute -bottom-8 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900/95 border border-slate-700 text-slate-200 text-[9px] px-1.5 py-0.5 rounded shadow whitespace-nowrap pointer-events-none z-30 font-mono">
          {vehicle.model} • Risk: {vehicle.riskScore}%
        </div>
      </button>
    );
  };

  // Station Machine Render helper with distinctive physical equipment visuals
  const renderStationEquipmentGraphic = (station: StationData, isTwin: boolean = false) => {
    switch (station.id) {
      case 'S1': // Framing Robotic Welder
        return (
          <div className="relative w-full h-14 flex items-center justify-center bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <rect x="10" y="28" width="80" height="6" fill="#334155" />
              {/* Robotic Arm 1 */}
              <line x1="25" y1="28" x2="35" y2="12" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="35" y1="12" x2="48" y2="20" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" />
              <circle cx="35" cy="12" r="3" fill="#38bdf8" />
              {/* Welder Tip */}
              <circle cx="48" cy="20" r="2" fill="#e0f2fe" />
              {/* Welding Sparks Animation */}
              <circle cx="48" cy="20" r="4" fill="#38bdf8" className="animate-ping opacity-75" />
              {/* Robotic Arm 2 */}
              <line x1="75" y1="28" x2="65" y2="12" stroke="#38bdf8" strokeWidth="2.5" strokeLinecap="round" />
              <line x1="65" y1="12" x2="52" y2="20" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" />
              <circle cx="65" cy="12" r="3" fill="#38bdf8" />
            </svg>
            <span className="absolute bottom-1 right-1 text-[8px] font-mono text-cyan-400/80">WELD_ARM_OK</span>
          </div>
        );

      case 'S2': // Paint Atomizers
        return (
          <div className="relative w-full h-14 flex items-center justify-center bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <rect x="10" y="28" width="80" height="6" fill="#334155" />
              {/* Spray Atomizer Heads */}
              <rect x="25" y="4" width="8" height="12" fill="#06b6d4" rx="2" />
              <rect x="65" y="4" width="8" height="12" fill="#06b6d4" rx="2" />
              {/* Spray Mist Cone */}
              <polygon points="29,16 18,28 40,28" fill="url(#paintGrad1)" opacity="0.6" />
              <polygon points="69,16 58,28 80,28" fill="url(#paintGrad1)" opacity="0.6" />
              <defs>
                <linearGradient id="paintGrad1" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#0891b2" stopOpacity="0.05" />
                </linearGradient>
              </defs>
            </svg>
            <span className="absolute bottom-1 right-1 text-[8px] font-mono text-cyan-300/80">ATOMIZER_ROTARY</span>
          </div>
        );

      case 'S3': // Chassis Marriage Decking Rig (The Anomaly Station)
        const isDegraded = !interventionApplied && station.deviationScore > 0.4;
        return (
          <div className={`relative w-full h-14 flex items-center justify-center rounded border overflow-hidden transition-all ${
            isDegraded ? 'bg-amber-950/40 border-amber-500/50 shadow-inner' : 'bg-slate-900/60 border-slate-800/80'
          }`}>
            <svg viewBox="0 0 100 40" className="w-full h-full">
              {/* AGV Lifter Scissor Jack */}
              <line x1="25" y1="34" x2="45" y2="18" stroke="#f59e0b" strokeWidth="2.5" />
              <line x1="45" y1="34" x2="25" y2="18" stroke="#f59e0b" strokeWidth="2.5" />
              <line x1="75" y1="34" x2="55" y2="18" stroke="#f59e0b" strokeWidth="2.5" />
              <line x1="55" y1="34" x2="75" y2="18" stroke="#f59e0b" strokeWidth="2.5" />
              <rect x="20" y="14" width="60" height="5" fill="#b45309" rx="1" />
              {/* Multi-Spindle Heads */}
              <rect x="30" y="6" width="5" height="9" fill={isDegraded ? '#ef4444' : '#f59e0b'} />
              <rect x="45" y="6" width="5" height="9" fill={isDegraded ? '#f59e0b' : '#f59e0b'} />
              <rect x="60" y="6" width="5" height="9" fill={isDegraded ? '#ef4444' : '#f59e0b'} />
              {/* Spindle #4 Warning flash if degraded */}
              {isDegraded && (
                <circle cx="62" cy="10" r="6" fill="#ef4444" className="animate-ping opacity-60" />
              )}
            </svg>
            <span className={`absolute bottom-1 right-1 text-[8px] font-mono ${isDegraded ? 'text-red-400 font-bold' : 'text-amber-400'}`}>
              {isDegraded ? 'SPINDLE_#4_TORQUE_DRIFT' : 'DECKING_NOMINAL'}
            </span>
          </div>
        );

      case 'S4': // Powertrain Crane & Inverter Station
        const isStarved = !interventionApplied && station.telemetry.machineState === 'STARVED';
        return (
          <div className="relative w-full h-14 flex items-center justify-center bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <rect x="10" y="4" width="80" height="4" fill="#64748b" />
              <rect x="46" y="8" width="8" height="10" fill="#818cf8" rx="1" />
              <line x1="50" y1="18" x2="50" y2="28" stroke="#a5b4fc" strokeWidth="1.5" strokeDasharray="2 2" />
              <rect x="35" y="26" width="30" height="6" fill="#4f46e5" rx="2" />
            </svg>
            <span className="absolute bottom-1 right-1 text-[8px] font-mono text-indigo-400">
              {isStarved ? 'STARVATION_IDLE' : 'POWERTRAIN_800V'}
            </span>
          </div>
        );

      case 'S5': // Interior & Wiring
        return (
          <div className="relative w-full h-14 flex items-center justify-center bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <rect x="10" y="28" width="80" height="6" fill="#334155" />
              <rect x="25" y="10" width="16" height="18" fill="#7c3aed" rx="2" opacity="0.8" />
              <path d="M 41 18 Q 55 10 70 24" stroke="#c084fc" strokeWidth="2" fill="none" />
              <circle cx="70" cy="24" r="3" fill="#a855f7" />
            </svg>
            <span className="absolute bottom-1 right-1 text-[8px] font-mono text-purple-300">MANUAL_COCKPIT</span>
          </div>
        );

      case 'S6': // Final Inspection 3D Optical Laser
        return (
          <div className="relative w-full h-14 flex items-center justify-center bg-slate-900/60 rounded border border-slate-800/80 overflow-hidden">
            <svg viewBox="0 0 100 40" className="w-full h-full">
              <rect x="10" y="28" width="80" height="6" fill="#334155" />
              {/* Laser Scanner Arch */}
              <path d="M 20 30 L 20 8 L 80 8 L 80 30" stroke="#10b981" strokeWidth="3" fill="none" />
              {/* Laser Scan Beam */}
              <line x1="30" y1="8" x2="45" y2="28" stroke="#34d399" strokeWidth="1.5" className="animate-pulse" />
              <line x1="70" y1="8" x2="55" y2="28" stroke="#34d399" strokeWidth="1.5" className="animate-pulse" />
            </svg>
            <span className="absolute bottom-1 right-1 text-[8px] font-mono text-emerald-400">3D_METROLOGY</span>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="w-full bg-[#080B11] p-4 lg:p-6 rounded-2xl border border-slate-800/80 shadow-2xl relative overflow-hidden">
      
      {/* Background Tech Grid */}
      <div className="absolute inset-0 bg-grid-pattern opacity-30 pointer-events-none" />
      <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Top Banner / Mode Explanation */}
      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-heading font-bold text-lg text-white tracking-wider flex items-center gap-2">
              <span>AUTOMOTIVE PRODUCTION LINE & SYNCHRONIZED TWIN</span>
              {isSynchronized && (
                <span className="px-2 py-0.5 rounded bg-cyan-950 border border-cyan-500/40 text-cyan-300 text-xs font-mono">
                  CYBER-PHYSICAL PARALLEL DUAL
                </span>
              )}
            </h3>
          </div>
          <p className="text-xs text-slate-400 font-mono">
            6 Connected Discrete Stations • Sequential Part Flow • 5 Finite Inter-Station Buffers (B12–B56)
          </p>
        </div>

        {/* S3 Anomaly Alert / Countdown Pill */}
        {!interventionApplied ? (
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-amber-950/80 border border-amber-500/50 shadow-md shadow-amber-500/10">
            <AlertTriangle className="w-4 h-4 text-amber-400 animate-bounce" />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-mono text-xs font-bold text-amber-300">PREDICTED BOTTLENECK: S3</span>
                <span className="text-[10px] px-1 py-0.2 rounded bg-red-900/80 text-red-200 font-mono font-bold">87% RISK</span>
              </div>
              <div className="text-[10px] font-mono text-slate-300 flex items-center gap-1">
                <Timer className="w-3 h-3 text-amber-400" />
                <span>Time-to-Lockup: <strong className="text-amber-200">{formatCountdown(countdownSec)}</strong></span>
                <span className="text-slate-500">|</span>
                <button
                  onClick={openWhyModal}
                  className="text-cyan-400 hover:text-cyan-300 underline font-semibold cursor-pointer"
                >
                  WHY?
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-500/50 shadow-md shadow-emerald-500/10">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="font-mono text-xs font-bold text-emerald-300">INTERVENTION ACTIVE: SCENARIO B</span>
              <p className="text-[10px] font-mono text-slate-300">
                S3 Cycle Time Restored (52s) • Throughput: <strong className="text-emerald-400">+9 UPH</strong> • Line Balanced
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Main Assembly Line Grid Layout (6 Stations + 5 Buffers) */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3.5 my-2">
        {stations.map((station, index) => {
          const isSelected = selectedStation?.id === station.id;
          const isS3 = station.id === 'S3';
          const isS2 = station.id === 'S2';
          const isS4 = station.id === 'S4';
          const isDegraded = !interventionApplied && station.deviationScore > 0.4;
          const isStarved = !interventionApplied && station.telemetry.machineState === 'STARVED';
          const isBlocked = !interventionApplied && station.telemetry.queueLength >= 4 && isS2;

          // Vehicles currently at this station
          const stationVehicles = vehicles.filter((v) => v.currentStationId === station.id);

          return (
            <div
              key={station.id}
              id={`station-card-${station.id.toLowerCase()}`}
              onClick={() => selectStationById(station.id)}
              className={`group relative flex flex-col rounded-xl border transition-all duration-300 cursor-pointer overflow-hidden p-3 ${
                isDegraded
                  ? 'glass-panel-amber ring-1 ring-amber-500/50 hover:border-amber-400'
                  : isStarved
                  ? 'glass-panel border-indigo-500/40 hover:border-indigo-400'
                  : isSelected
                  ? 'glass-panel-cyan ring-2 ring-cyan-400'
                  : 'glass-panel hover:border-slate-600'
              }`}
            >
              {/* Station Header */}
              <div className="flex items-start justify-between gap-1 mb-2">
                <div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono text-xs font-extrabold px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-cyan-400">
                      {station.id}
                    </span>
                    <h4 className="font-heading font-bold text-xs text-white tracking-wide">
                      {station.name}
                    </h4>
                  </div>
                  <p className="text-[9px] text-slate-400 truncate max-w-[130px]" title={station.subTitle}>
                    {station.subTitle}
                  </p>
                </div>

                {/* State Pill */}
                <span className={`text-[8px] font-mono px-1 py-0.5 rounded font-semibold ${
                  isDegraded
                    ? 'bg-red-900/80 text-red-200 border border-red-500/40 animate-pulse'
                    : isStarved
                    ? 'bg-indigo-900/80 text-indigo-200 border border-indigo-500/40'
                    : isBlocked
                    ? 'bg-amber-900/80 text-amber-200 border border-amber-500/40'
                    : 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/30'
                }`}>
                  {station.telemetry.machineState}
                </span>
              </div>

              {/* Physical Machine Isometric Graphic */}
              <div className="my-1.5">
                {renderStationEquipmentGraphic(station, false)}
              </div>

              {/* Vehicles Occupying Station */}
              <div className="min-h-[44px] flex items-center justify-center gap-1.5 p-1 rounded bg-slate-950/80 border border-slate-800/80 my-1">
                {stationVehicles.length > 0 ? (
                  stationVehicles.map((v) => renderVehicleBadge(v, false))
                ) : (
                  <span className="text-[9px] font-mono text-slate-600 italic">No Active Carrier</span>
                )}
              </div>

              {/* Live Telemetry Readout Grid */}
              <div className="grid grid-cols-2 gap-1.5 pt-2 border-t border-slate-800/80 font-mono text-[10px]">
                <div className="bg-slate-900/70 p-1 rounded">
                  <span className="text-slate-400 text-[8px] block">CYCLE TIME</span>
                  <div className="flex items-center gap-0.5">
                    <span className={`font-bold ${station.telemetry.cycleTime > 65 ? 'text-red-400 font-extrabold' : 'text-slate-200'}`}>
                      {station.telemetry.cycleTime.toFixed(1)}s
                    </span>
                    <span className="text-slate-500 text-[8px]">/{station.telemetry.baselineCycleTime}s</span>
                  </div>
                </div>

                <div className="bg-slate-900/70 p-1 rounded">
                  <span className="text-slate-400 text-[8px] block">QUEUE / WIP</span>
                  <div className="flex items-center gap-1 font-bold text-slate-200">
                    <span>{station.telemetry.queueLength}</span>
                    <div className="flex gap-0.5">
                      {Array.from({ length: station.telemetry.bufferMax }).map((_, bi) => (
                        <div
                          key={bi}
                          className={`w-1 h-2 rounded-2xs ${
                            bi < station.telemetry.queueLength
                              ? station.telemetry.queueLength >= 4
                                ? 'bg-amber-400'
                                : 'bg-cyan-400'
                              : 'bg-slate-800'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                </div>

                <div className="bg-slate-900/70 p-1 rounded">
                  <span className="text-slate-400 text-[8px] block">CURRENT (A)</span>
                  <span className={`font-semibold ${station.telemetry.currentVariance > 1.5 ? 'text-amber-300' : 'text-slate-300'}`}>
                    {station.telemetry.motorCurrent.toFixed(1)}A
                  </span>
                </div>

                <div className="bg-slate-900/70 p-1 rounded">
                  <span className="text-slate-400 text-[8px] block">δ(t) DEVIATION</span>
                  <span className={`font-bold ${station.deviationScore > 0.4 ? 'text-red-400' : 'text-cyan-400'}`}>
                    {station.deviationScore > 0 ? `+${(station.deviationScore * 100).toFixed(0)}%` : '0%'}
                  </span>
                </div>
              </div>

              {/* S3 Anomaly Overlay / Trigger */}
              {isS3 && isDegraded && (
                <div className="mt-2 pt-1.5 border-t border-amber-500/30 flex items-center justify-between">
                  <span className="text-[9px] font-mono text-amber-300 font-bold">14m to bottleneck</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openWhyModal();
                    }}
                    className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold transition-all"
                  >
                    EXPLAIN WHY
                  </button>
                </div>
              )}

              {/* S4 Downstream Starvation Indicator */}
              {isS4 && isStarved && (
                <div className="mt-2 pt-1.5 border-t border-indigo-500/30 flex items-center justify-between text-[9px] font-mono text-indigo-300">
                  <span>Downstream Starvation</span>
                  <span className="text-slate-400">Idle 31.6%</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Cyber-Physical Digital Twin Mirrored Layer (Rendered when in Synchronized mode) */}
      {isSynchronized && (
        <div className="mt-6 pt-4 border-t border-cyan-500/30 relative">
          
          {/* Cyber-Physical Data Links Connection Header */}
          <div className="flex items-center justify-between mb-3 px-2">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              <h4 className="font-heading font-bold text-sm text-cyan-300 tracking-wider flex items-center gap-2">
                <span>DIGITAL TWIN COMPUTATIONAL MIRROR</span>
                <span className="text-[10px] font-mono text-slate-400 font-normal">
                  State Vector x(t) ∈ ℝ¹¹² • GATv2 Attention Graph • Microsecond Sync
                </span>
              </h4>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 bg-cyan-950/60 px-2.5 py-1 rounded border border-cyan-500/30">
              <Cpu className="w-3.5 h-3.5" />
              <span>DES BASELINE ↔ OBSERVATION COMPARATOR ACTIVE</span>
            </div>
          </div>

          {/* Mirrored Digital Twin Nodes with Glowing Cyan Telemetry Links */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3.5">
            {stations.map((station) => {
              const isS3 = station.id === 'S3';
              const isDegraded = !interventionApplied && station.deviationScore > 0.4;

              return (
                <div
                  key={`twin-${station.id}`}
                  className={`p-3 rounded-xl border transition-all ${
                    isDegraded
                      ? 'bg-amber-950/30 border-amber-500/50 shadow-lg shadow-amber-500/10'
                      : 'bg-slate-900/80 border-cyan-500/30 shadow-md shadow-cyan-500/5'
                  }`}
                >
                  <div className="flex items-center justify-between text-[10px] font-mono mb-2">
                    <span className="text-cyan-300 font-bold">TWIN_{station.id}</span>
                    <span className="text-slate-400">Conf: {station.telemetry.confidence}%</span>
                  </div>

                  {/* Computational Graph Node */}
                  <div className="h-12 bg-slate-950/90 rounded border border-cyan-500/20 p-2 flex flex-col justify-between mb-2">
                    <div className="flex items-center justify-between text-[9px] font-mono">
                      <span className="text-slate-400">State Vector:</span>
                      <span className="text-cyan-400 font-bold">dim=128</span>
                    </div>
                    <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${isDegraded ? 'bg-amber-400' : 'bg-cyan-400'}`}
                        style={{ width: `${station.telemetry.confidence}%` }}
                      />
                    </div>
                  </div>

                  {/* Synchronized Twin Metrics */}
                  <div className="space-y-1 text-[9px] font-mono">
                    <div className="flex justify-between text-slate-300">
                      <span>DES Nominal:</span>
                      <span className="text-slate-400">{station.telemetry.baselineCycleTime}s</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-300">Twin Forecast:</span>
                      <span className={`font-bold ${isDegraded ? 'text-amber-400' : 'text-cyan-300'}`}>
                        {station.telemetry.cycleTime.toFixed(1)}s
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-300">Spatial Weight:</span>
                      <span className="text-purple-300">
                        α={station.attentionWeights[station.id]?.toFixed(2) || '0.32'}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      )}

      {/* Bottom Production Flow Causal Chain Bar */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono text-slate-400">
        <div className="flex items-center gap-1.5">
          <span className="text-slate-300 font-semibold uppercase">Causal Chain:</span>
          <span>Physical Line</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
          <span>Live Digital Twin</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
          <span className="text-amber-300">δ(t) Drift</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
          <span className="text-purple-300">Spatio-Temporal AI</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
          <span className="text-red-400">Bottleneck Prediction (T+14m)</span>
          <ArrowRight className="w-3 h-3 text-cyan-400" />
          <span className="text-emerald-400">Preemptive Intervention</span>
        </div>

        <div className="flex items-center gap-3">
          <span>Target Takt Time: <strong className="text-slate-200">54.0s</strong></span>
          <span>Line Throughput: <strong className={interventionApplied ? 'text-emerald-400' : 'text-amber-400'}>
            {interventionApplied ? '43 UPH (+9)' : '34 UPH (-8)'}
          </strong></span>
        </div>
      </div>

    </div>
  );
};
