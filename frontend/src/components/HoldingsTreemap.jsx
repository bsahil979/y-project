import React, { useMemo, useState } from 'react';
import { Treemap, ResponsiveContainer, Tooltip } from 'recharts';

/**
 * Maps a daily percentage change to a background color.
 * Positive → shades of green, negative → shades of red, zero → neutral gray.
 */
function changeToColor(change) {
  if (change == null || !Number.isFinite(change)) return '#374151'; // gray-700
  const clamped = Math.max(-10, Math.min(10, change));
  const intensity = Math.abs(clamped) / 10;
  if (clamped > 0) {
    // Green shades: from dark muted green to vivid green
    const r = Math.round(20 - intensity * 10);
    const g = Math.round(80 + intensity * 140);
    const b = Math.round(40 + intensity * 20);
    return `rgb(${r}, ${g}, ${b})`;
  }
  if (clamped < 0) {
    // Red shades: from dark muted red to vivid red
    const r = Math.round(120 + intensity * 120);
    const g = Math.round(40 - intensity * 25);
    const b = Math.round(40 - intensity * 20);
    return `rgb(${r}, ${g}, ${b})`;
  }
  return '#374151';
}

/**
 * Custom renderer for each Treemap cell.
 * Recharts Treemap passes x, y, width, height, and the data fields to the content prop.
 */
function CustomCell(props) {
  const { x, y, width, height, name, change, displayValue } = props;
  if (width < 2 || height < 2) return null;
  const bg = changeToColor(change);
  const showTicker = width > 36 && height > 24;
  const showChange = width > 50 && height > 40;
  const showValue = width > 70 && height > 56;
  const fontSize = Math.max(10, Math.min(16, width / 6));
  const changeFontSize = Math.max(9, Math.min(13, width / 8));

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={6}
        ry={6}
        style={{
          fill: bg,
          stroke: '#0a0c14',
          strokeWidth: 2,
          cursor: 'default',
        }}
      />
      {showTicker && (
        <text
          x={x + width / 2}
          y={y + height / 2 - (showChange ? 8 : 0)}
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            fill: '#fff',
            fontSize: `${fontSize}px`,
            fontWeight: 800,
            fontFamily: 'ui-monospace, monospace',
            pointerEvents: 'none',
            textShadow: '0 1px 3px rgba(0,0,0,0.5)',
          }}
        >
          {name}
        </text>
      )}
      {showChange && (
        <text
          x={x + width / 2}
          y={y + height / 2 + (showValue ? 6 : 10)}
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            fill: change >= 0 ? '#bbf7d0' : '#fecaca',
            fontSize: `${changeFontSize}px`,
            fontWeight: 700,
            pointerEvents: 'none',
            textShadow: '0 1px 2px rgba(0,0,0,0.4)',
          }}
        >
          {change >= 0 ? '+' : ''}{change?.toFixed(1)}%
        </text>
      )}
      {showValue && (
        <text
          x={x + width / 2}
          y={y + height / 2 + 22}
          textAnchor="middle"
          dominantBaseline="central"
          style={{
            fill: 'rgba(255,255,255,0.55)',
            fontSize: `${Math.max(8, changeFontSize - 2)}px`,
            fontWeight: 500,
            pointerEvents: 'none',
          }}
        >
          {displayValue}
        </text>
      )}
    </g>
  );
}

/**
 * Custom Tooltip for the Treemap
 */
function TreemapTooltip({ active, payload }) {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div className="bg-[#161822] border border-gray-700 rounded-xl px-4 py-3 shadow-xl text-sm">
      <p className="font-mono font-bold text-white text-base">{data.name}</p>
      <p className="text-gray-400 mt-1">
        Market value:{' '}
        <span className="text-white font-semibold">
          {data.displayValue}
        </span>
      </p>
      <p className="text-gray-400">
        Daily change:{' '}
        <span className={`font-semibold ${data.change >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
          {data.change >= 0 ? '+' : ''}{data.change?.toFixed(2)}%
        </span>
      </p>
      {data.dailyPnl != null && (
        <p className="text-gray-400">
          Today:{' '}
          <span className={`font-semibold ${data.dailyPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {data.dailyPnl >= 0 ? '+' : ''}{data.dailyPnl.toLocaleString(undefined, { style: 'currency', currency: data.currency || 'USD' })}
          </span>
        </p>
      )}
    </div>
  );
}

const PERIOD_OPTIONS = [
  { label: '1d', key: 'daily' },
];

export default function HoldingsTreemap({ holdings }) {
  const [period] = useState('daily');

  const treemapData = useMemo(() => {
    const items = holdings
      .filter((h) => h.marketValue != null && h.marketValue > 0)
      .map((h) => ({
        name: h.ticker,
        // Use USD-normalized value for box sizing so INR and USD are comparable
        size: h.marketValueUSD ?? h.marketValue,
        change: h.dailyPnlPct ?? 0,
        dailyPnl: h.dailyPnl,
        displayValue: h.marketValue.toLocaleString(undefined, {
          style: 'currency',
          currency: h.currency || 'USD',
          maximumFractionDigits: 0,
        }),
        currency: h.currency,
      }))
      .sort((a, b) => b.size - a.size);

    return items;
  }, [holdings, period]);

  if (treemapData.length === 0) return null;

  return (
    <section className="bg-[#11131a]/80 border border-gray-800/50 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-bold text-white">Holdings Heatmap</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Box size = market value · Color = daily change
          </p>
        </div>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map((opt) => (
            <span
              key={opt.key}
              className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
            >
              {opt.label}
            </span>
          ))}
        </div>
      </div>
      <div style={{ width: '100%', height: Math.max(260, Math.min(420, treemapData.length * 50)) }}>
        <ResponsiveContainer width="100%" height="100%">
          <Treemap
            data={treemapData}
            dataKey="size"
            nameKey="name"
            content={<CustomCell />}
            animationDuration={400}
            animationEasing="ease-out"
          >
            <Tooltip content={<TreemapTooltip />} />
          </Treemap>
        </ResponsiveContainer>
      </div>
      <div className="flex items-center justify-center gap-3 mt-3">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm" style={{ background: changeToColor(-8) }} />
          <span className="text-[10px] text-gray-500">–8%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm" style={{ background: changeToColor(-3) }} />
          <span className="text-[10px] text-gray-500">–3%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm" style={{ background: changeToColor(0) }} />
          <span className="text-[10px] text-gray-500">0%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm" style={{ background: changeToColor(3) }} />
          <span className="text-[10px] text-gray-500">+3%</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm" style={{ background: changeToColor(8) }} />
          <span className="text-[10px] text-gray-500">+8%</span>
        </div>
      </div>
    </section>
  );
}
