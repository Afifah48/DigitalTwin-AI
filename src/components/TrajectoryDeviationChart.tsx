import React, { useState } from 'react';
import { useFactorySimulation } from '../context/FactorySimulationContext';
import { HISTORICAL_AND_FORECAST_TRAJECTORY } from '../data/factoryData';
import { TrajectoryPoint } from '../types';
import {
  TrendingUp,
  LineChart,
  HelpCircle,
  Clock,
  Sparkles,
  Layers,
  ArrowRight
} from 'lucide-react';

export const TrajectoryDeviationChart: React.FC = () => {
  const { openWhyModal, openWhatIfModal, interventionApplied } = useFactorySimulation();
  const [hoveredPoint, setHoveredPoint] = useState<TrajectoryPoint | null>(null);

  const data = HISTORICAL_AND_FORECAST_TRAJECTORY;

  // Chart dimensions & scaling
  const width = 800;
  const height = 280;
  const padding = { top: 30, right: 30, bottom: 40, left: 50 };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Min / Max values
  const minVal = 40;
  const maxVal = 200;

  const getX = (index: number) => {
    return padding.left + (index / (data.length - 1)) * chartWidth;
  };

  const getY = (val: number) => {
    const clamped = Math.max(minVal, Math.min(maxVal, val));
    return padding.top + chartHeight - ((clamped - minVal) / (maxVal - minVal)) * chartHeight;
  };

  // Generate SVG path for Baseline
  const baselinePath = data.reduce((acc, pt, i) => {
    const x = getX(i);
    const y = getY(pt.baseline);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  // Generate SVG path for Observed / Forecasted
  const observedPath = data.reduce((acc, pt, i) => {
    const x = getX(i);
    // If intervention is applied in UI, show normalized path for forecast
    const val = interventionApplied && pt.isForecast ? 52 + (i - 6) * -0.3 : pt.observed;
    const y = getY(val);
    return i === 0 ? `M ${x} ${y}` : `${acc} L ${x} ${y}`;
  }, '');

  // Generate Confidence Envelope area
  const confidenceAreaPath = () => {
    const upperPoints = data.map((pt, i) => {
      const val = interventionApplied && pt.isForecast ? 54 : pt.upperBand;
      return `${getX(i)},${getY(val)}`;
    });
    const lowerPoints = data.map((pt, i) => {
      const val = interventionApplied && pt.isForecast ? 50 : pt.lowerBand;
      return `${getX(i)},${getY(val)}`;
    }).reverse();
    return `M ${upperPoints[0]} L ${upperPoints.join(' L ')} L ${lowerPoints.join(' L ')} Z`;
  };

  const nowIndex = data.findIndex((p) => p.timestampLabel === 'NOW');
  const nowX = getX(nowIndex);

  return (
    <div className="w-full bg-[#080B11] p-4 lg:p-6 rounded-2xl border border-slate-800 shadow-2xl relative overflow-hidden">
      
      {/* Background Glow */}
      <div className="absolute top-0 left-1/3 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header & Mathematical Definition */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pb-4 mb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
            <h3 className="font-heading font-bold text-lg text-white tracking-wider">
              NORMAL TRAJECTORY & DEVIATION δ(t) AT S3
            </h3>
          </div>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Discrete Event Simulation (DES) Baseline vs Observed Creep vs 20-Minute Trajectory Projection
          </p>
        </div>

        {/* Mathematical Equation Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/90 border border-cyan-500/30 text-xs font-mono">
          <span className="text-cyan-400 font-bold text-sm">δ(t)</span>
          <span className="text-slate-400">=</span>
          <span className="text-amber-300 font-medium">Observed State(t)</span>
          <span className="text-slate-400">−</span>
          <span className="text-slate-300">Expected DES Baseline(t)</span>
        </div>
      </div>

      {/* Trajectory SVG Chart */}
      <div className="relative w-full overflow-x-auto">
        <div className="min-w-[700px]">
          <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto drop-shadow-md">
            
            {/* Grid lines */}
            {[50, 75, 100, 125, 150, 175].map((gridVal) => {
              const y = getY(gridVal);
              return (
                <g key={gridVal}>
                  <line
                    x1={padding.left}
                    y1={y}
                    x2={width - padding.right}
                    y2={y}
                    stroke="#1e293b"
                    strokeWidth="1"
                    strokeDasharray="4 4"
                  />
                  <text
                    x={padding.left - 8}
                    y={y + 4}
                    fill="#64748b"
                    fontSize="10"
                    fontFamily="monospace"
                    textAnchor="end"
                  >
                    {gridVal}s
                  </text>
                </g>
              );
            })}

            {/* NOW Vertical Marker line */}
            <line
              x1={nowX}
              y1={padding.top}
              x2={nowX}
              y2={height - padding.bottom}
              stroke="#f59e0b"
              strokeWidth="1.5"
              strokeDasharray="3 3"
            />
            <rect x={nowX - 22} y={padding.top - 18} width="44" height="16" rx="3" fill="#78350f" />
            <text x={nowX} y={padding.top - 6} fill="#fef3c7" fontSize="9" fontFamily="monospace" textAnchor="middle" fontWeight="bold">
              NOW
            </text>

            {/* Past vs Forecast Background Shading */}
            <rect
              x={nowX}
              y={padding.top}
              width={width - padding.right - nowX}
              height={chartHeight}
              fill="rgba(168, 85, 247, 0.04)"
            />
            <text
              x={width - padding.right - 10}
              y={padding.top + 16}
              fill="#c084fc"
              fontSize="10"
              fontFamily="monospace"
              textAnchor="end"
              fontWeight="bold"
            >
              PREDICTIVE FORECAST HORIZON →
            </text>

            {/* 90% Confidence Interval Envelope Area */}
            <path
              d={confidenceAreaPath()}
              fill={interventionApplied ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.12)'}
              stroke="none"
            />

            {/* Baseline Path (White Dotted Line) */}
            <path
              d={baselinePath}
              fill="none"
              stroke="#94a3b8"
              strokeWidth="2"
              strokeDasharray="5 5"
            />

            {/* Observed / Forecasted Trajectory Path */}
            <path
              d={observedPath}
              fill="none"
              stroke={interventionApplied ? '#10b981' : '#f59e0b'}
              strokeWidth="3.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />

            {/* Data Points */}
            {data.map((pt, idx) => {
              const x = getX(idx);
              const val = interventionApplied && pt.isForecast ? 52 + (idx - 6) * -0.3 : pt.observed;
              const y = getY(val);
              const isNow = pt.timestampLabel === 'NOW';
              const isBottleneck = pt.timestampLabel === 'T+14m' && !interventionApplied;

              return (
                <g
                  key={pt.timestampLabel}
                  className="cursor-pointer"
                  onMouseEnter={() => setHoveredPoint(pt)}
                  onMouseLeave={() => setHoveredPoint(null)}
                >
                  <circle
                    cx={x}
                    cy={y}
                    r={isBottleneck ? 7 : isNow ? 6 : 4.5}
                    fill={isBottleneck ? '#ef4444' : isNow ? '#f59e0b' : pt.isForecast ? '#a855f7' : '#06b6d4'}
                    stroke="#080b11"
                    strokeWidth="2"
                  />
                  {isBottleneck && (
                    <circle cx={x} cy={y} r="12" fill="#ef4444" className="animate-ping opacity-50" />
                  )}

                  {/* X-axis Timestamp labels */}
                  <text
                    x={x}
                    y={height - padding.bottom + 18}
                    fill={isNow ? '#fbbf24' : pt.isForecast ? '#c084fc' : '#94a3b8'}
                    fontSize="10"
                    fontFamily="monospace"
                    textAnchor="middle"
                    fontWeight={isNow || isBottleneck ? 'bold' : 'normal'}
                  >
                    {pt.timestampLabel}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Legend & Hovered Point Inspection Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-3 pt-4 border-t border-slate-800 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-4 text-slate-300">
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 border-t-2 border-dashed border-slate-400 inline-block" />
            <span>DES Expected Baseline (54.0s)</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className={`w-3.5 h-1.5 rounded-full inline-block ${interventionApplied ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <span>{interventionApplied ? 'Cured Trajectory' : 'Observed Drift & Forecast'}</span>
          </div>

          <div className="flex items-center gap-1.5">
            <span className={`w-3.5 h-3 rounded-sm inline-block ${interventionApplied ? 'bg-emerald-950 border border-emerald-500/40' : 'bg-red-950 border border-red-500/40'}`} />
            <span>90% MC Dropout Confidence Envelope</span>
          </div>
        </div>

        {/* Hovered Point Detail */}
        {hoveredPoint ? (
          <div className="p-2 rounded bg-slate-900 border border-cyan-500/40 text-cyan-300 text-[11px] flex items-center gap-3">
            <span><strong>{hoveredPoint.timestampLabel}:</strong> Cycle Time: {hoveredPoint.observed}s</span>
            <span>δ(t): <strong>+{hoveredPoint.deltaT}s</strong></span>
            <span>90% CI: [{hoveredPoint.lowerBand}s – {hoveredPoint.upperBand}s]</span>
          </div>
        ) : (
          <div className="text-slate-500 text-[11px] italic">
            Hover any point on the trajectory curve to view exact δ(t) delta & bounds
          </div>
        )}
      </div>

      {/* Insight Callout */}
      <div className="mt-4 p-3 bg-amber-950/20 rounded-xl border border-amber-500/20 text-xs font-mono text-slate-300 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span>
            <strong>Key Insight:</strong> S3 failure is NOT instantaneous. Degradation starts 40 minutes prior with micro-torque jitter. AI flags the deviation when δ(t) exceeds 2.5σ.
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={openWhyModal}
            className="px-2.5 py-1 rounded bg-amber-900/40 hover:bg-amber-900/60 border border-amber-500/40 text-amber-300 text-xs font-semibold"
          >
            EXPLAIN CAUSE
          </button>
          <button
            onClick={() => openWhatIfModal()}
            className="px-2.5 py-1 rounded bg-emerald-900/40 hover:bg-emerald-900/60 border border-emerald-500/40 text-emerald-300 text-xs font-semibold"
          >
            SIMULATE INTERVENTION
          </button>
        </div>
      </div>

    </div>
  );
};
