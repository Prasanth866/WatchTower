import React, { useState, useEffect, useRef } from 'react';
import { api, subscribeToPrices, SUPPORTED_COINS } from '../api';
import { CoinId, CoinInfo, CoinHistoryPoint, QuantIndicators } from '../types';
import { useToast } from './ToastProvider';
import { Activity, BarChart2, TrendingUp, TrendingDown, Clock, Calendar, Database, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface CoinAnalysisProps {
  selectedCoinId: CoinId;
  onSelectCoin: (id: CoinId) => void;
}

type Period = '1d' | '7d' | '30d';

export const CoinAnalysis: React.FC<CoinAnalysisProps> = ({ selectedCoinId, onSelectCoin }) => {
  const [coins, setCoins] = useState<Record<CoinId, CoinInfo> | null>(null);
  const [history, setHistory] = useState<CoinHistoryPoint[]>([]);
  const [indicators, setIndicators] = useState<QuantIndicators | null>(null);
  const [period, setPeriod] = useState<Period>('7d');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  // Chart interaction ref & state
  const chartRef = useRef<SVGSVGElement | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; price: number; date: string } | null>(null);

  const { addToast } = useToast();

  // 1. Listen for real-time WebSocket tick updates
  useEffect(() => {
    const unsubscribe = subscribeToPrices((latestPrices) => {
      setCoins(latestPrices);
    });
    return () => unsubscribe();
  }, []);

  // 2. Fetch historic prices based on chosen period
  const fetchHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await api.getCoinHistory(selectedCoinId, period);
      setHistory(res.history);
      setIndicators(res.indicators);
    } catch {
      addToast('error', 'History Error', 'Failed to retrieve cache historical charts.');
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [selectedCoinId, period]);

  // Adjust history's latest element in real-time as prices stream in
  useEffect(() => {
    if (coins && coins[selectedCoinId] && history.length > 0) {
      setHistory((prev) => {
        if (prev.length === 0) return prev;
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          price: coins[selectedCoinId].price,
        };
        return next;
      });
    }
  }, [coins, selectedCoinId]);

  if (!coins) {
    return (
      <div id="coin-analysis-loading" className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-pulse">
        <div className="lg:col-span-4 bg-zinc-950/40 border border-zinc-900 rounded-2xl h-[500px]" />
        <div className="lg:col-span-8 bg-zinc-950/40 border border-zinc-900 rounded-2xl h-[500px]" />
      </div>
    );
  }

  const activeCoin = coins[selectedCoinId];

  // Calculate coordinates for custom high-fidelity SVG chart
  const prices = history.map((p) => p.price);
  const minPrice = prices.length > 0 ? Math.min(...prices) * 0.995 : 0;
  const maxPrice = prices.length > 0 ? Math.max(...prices) * 1.005 : 100;
  const priceRange = maxPrice - minPrice;

  const volumes = history.map((p) => p.volume);
  const maxVolume = volumes.length > 0 ? Math.max(...volumes) : 100;

  // Chart layout dimensions
  const svgWidth = 600;
  const svgHeight = 280;
  const paddingX = 40;
  const paddingY = 25;
  const chartWidth = svgWidth - paddingX * 2;
  const chartHeight = svgHeight - paddingY * 2;

  // Points mapping
  const points = history.map((pt, index) => {
    const x = paddingX + (index / (history.length - 1)) * chartWidth;
    // Invert Y axis for SVG rendering
    const y = paddingY + chartHeight - ((pt.price - minPrice) / priceRange) * chartHeight;
    return { x, y, price: pt.price, date: new Date(pt.timestamp).toLocaleString() };
  });

  // Construct path definitions
  let dPath = '';
  let areaPath = '';
  if (points.length > 0) {
    dPath = `M ${points[0].x} ${points[0].y} ` + points.slice(1).map((p) => `L ${p.x} ${p.y}`).join(' ');
    areaPath = `${dPath} L ${points[points.length - 1].x} ${svgHeight - paddingY} L ${points[0].x} ${svgHeight - paddingY} Z`;
  }

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement, MouseEvent>) => {
    if (!chartRef.current || points.length === 0) return;
    const rect = chartRef.current.getBoundingClientRect();
    const scaleX = svgWidth / rect.width;
    const svgClientX = (e.clientX - rect.left) * scaleX;
    const percentage = (svgClientX - paddingX) / chartWidth;

    // Find closest index
    let index = Math.round(percentage * (points.length - 1));
    index = Math.max(0, Math.min(points.length - 1, index));

    const p = points[index];
    setHoveredPoint(p);
  };

  const handleMouseLeave = () => {
    setHoveredPoint(null);
  };

  return (
    <div id="coin-analysis-container" className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      
      {/* LEFT COLUMN: Asset Selection Card Grid */}
      <div className="lg:col-span-4 flex flex-col gap-4">
        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-xl">
          <div className="flex items-center justify-between mb-4 pb-2 border-b border-zinc-900">
            <span className="text-xs font-bold font-mono text-zinc-400 uppercase tracking-widest">
              SUPPORTED TOKENS ({Object.keys(SUPPORTED_COINS).length})
            </span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] text-zinc-500 font-mono">
              <Database size={10} className="text-indigo-400" />
              <span>CACHED</span>
            </div>
          </div>

          <div className="flex flex-col gap-2 max-h-[520px] overflow-y-auto no-scrollbar">
            {(Object.values(coins) as CoinInfo[]).map((coin) => {
              const isSelected = selectedCoinId === coin.id;
              const isUp = coin.change24h >= 0;

              return (
                <button
                  key={coin.id}
                  id={`coin-list-item-${coin.id}`}
                  onClick={() => onSelectCoin(coin.id)}
                  className={`w-full flex items-center justify-between p-3.5 rounded-xl border text-left cursor-pointer transition-all duration-300 ${
                    isSelected
                      ? 'bg-indigo-500/10 border-indigo-500/40 shadow-[0_0_15px_rgba(99,102,241,0.08)]'
                      : 'bg-zinc-900/30 border-zinc-900 hover:bg-zinc-900/50 hover:border-zinc-800/80'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg font-mono font-bold text-xs flex items-center justify-center border ${
                      isSelected
                        ? 'bg-indigo-500/10 border-indigo-400/40 text-indigo-400'
                        : 'bg-zinc-950/50 border-zinc-800 text-zinc-400'
                    }`}>
                      {coin.symbol.substring(0, 2)}
                    </div>
                    <div>
                      <span className="block text-xs font-semibold text-zinc-100 tracking-wide font-sans leading-none">
                        {SUPPORTED_COINS[coin.id].name}
                      </span>
                      <span className="text-[10px] text-zinc-500 font-mono mt-1 block">
                        {coin.symbol}/USD
                      </span>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="block text-xs font-bold font-mono text-zinc-100 leading-none">
                      ${coin.price.toLocaleString(undefined, {
                        minimumFractionDigits: coin.id === 'doge' || coin.id === 'ada' ? 4 : 2,
                        maximumFractionDigits: coin.id === 'doge' || coin.id === 'ada' ? 4 : 2,
                      })}
                    </span>
                    <span className={`text-[10px] font-mono mt-1 inline-flex items-center gap-0.5 leading-none ${
                      isUp ? 'text-emerald-400' : 'text-rose-400'
                    }`}>
                      {isUp ? '+' : ''}
                      {coin.change24h.toFixed(2)}%
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* RIGHT COLUMN: Interactive Charts & Metrics Deep Dive */}
      <div className="lg:col-span-8 flex flex-col gap-6">
        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-6">
          
          {/* Section Header: Coin Metadata */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-900 pb-5">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-indigo-500/5 border border-indigo-500/20 rounded-xl flex items-center justify-center font-mono text-xl font-bold text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.05)]">
                {activeCoin.symbol}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-extrabold text-zinc-100 font-sans tracking-tight leading-none">
                    {SUPPORTED_COINS[activeCoin.id].name}
                  </h2>
                  <span className="text-xs text-zinc-500 font-mono font-semibold bg-zinc-900 border border-zinc-800 px-1.5 py-0.5 rounded">
                    {activeCoin.symbol}/USD
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 text-zinc-500 text-xs font-mono">
                  <span className="flex items-center gap-1">
                    <Clock size={12} className="text-indigo-400" />
                    WS LIVE ENGINE
                  </span>
                  <span className="w-1 h-1 rounded-full bg-zinc-700" />
                  <span>CACHE TIME-TO-LIVE: 30S</span>
                </div>
              </div>
            </div>

            <div className="flex flex-col md:items-end">
              <span className="text-2xl font-black text-zinc-100 font-mono tracking-tight leading-none">
                ${activeCoin.price.toLocaleString(undefined, {
                  minimumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 4 : 2,
                  maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 4 : 2,
                })}
              </span>
              <span className={`text-xs font-mono font-bold flex items-center gap-1 mt-1.5 leading-none ${
                activeCoin.change24h >= 0 ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {activeCoin.change24h >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                {activeCoin.change24h >= 0 ? '+' : ''}
                {activeCoin.change24h.toFixed(2)}% (24H)
              </span>
            </div>
          </div>

          {/* Price Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-zinc-900/30 border border-zinc-900 p-4 rounded-xl" title={`$${activeCoin.marketCap.toLocaleString()}`}>
              <span className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">MARKET CAP</span>
              <span className="block text-sm font-bold text-zinc-200 font-mono leading-none">
                ${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(activeCoin.marketCap)}
              </span>
            </div>
            <div className="bg-zinc-900/30 border border-zinc-900 p-4 rounded-xl" title={`$${activeCoin.totalVolume.toLocaleString()}`}>
              <span className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">TOTAL VOLUME (24H)</span>
              <span className="block text-sm font-bold text-zinc-200 font-mono leading-none">
                ${new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(activeCoin.totalVolume)}
              </span>
            </div>
            <div className="bg-zinc-900/30 border border-zinc-900 p-4 rounded-xl">
              <span className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">PERIOD HIGH</span>
              <span className="block text-sm font-bold text-emerald-400 font-mono leading-none">
                ${maxPrice ? maxPrice.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 4 : 2 }) : '-'}
              </span>
            </div>
            <div className="bg-zinc-900/30 border border-zinc-900 p-4 rounded-xl">
              <span className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">PERIOD LOW</span>
              <span className="block text-sm font-bold text-rose-400 font-mono leading-none">
                ${minPrice ? minPrice.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 4 : 2 }) : '-'}
              </span>
            </div>
          </div>

          {/* Chart Section: Controller Tabs */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart2 size={16} className="text-indigo-400" />
              <span className="text-xs font-bold font-mono text-zinc-300 uppercase tracking-wider">PRICE CHART OVERVIEW</span>
            </div>

            <div className="flex bg-zinc-900 p-1 rounded-lg border border-zinc-800">
              {(['1d', '7d', '30d'] as Period[]).map((p) => (
                <button
                  key={p}
                  id={`period-tab-${p}`}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1 text-[10px] font-mono font-bold rounded-md tracking-wider transition-all cursor-pointer uppercase ${
                    period === p
                      ? 'bg-zinc-800 text-indigo-400 border border-zinc-700/80 shadow-md'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {p === '1d' ? '24 HOURS' : p === '7d' ? '7 DAYS' : '30 DAYS'}
                </button>
              ))}
            </div>
          </div>

          {/* The High-Fidelity SVG Chart Wrapper */}
          <div className="relative bg-zinc-950 border border-zinc-900 rounded-xl overflow-hidden p-2">
            
            {/* Ambient charts glowing grid lines */}
            {isLoadingHistory && (
              <div className="absolute inset-0 bg-zinc-950/85 z-10 flex flex-col items-center justify-center gap-2">
                <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-[10px] font-mono text-indigo-400 tracking-wider">RETRIEVING CHART HISTORY...</span>
              </div>
            )}

            <svg
              ref={chartRef}
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="w-full h-auto cursor-crosshair overflow-visible select-none"
              onMouseMove={handleMouseMove}
              onMouseLeave={handleMouseLeave}
            >
              <defs>
                {/* Glow Area under chart curve */}
                <linearGradient id={`gradient-${selectedCoinId}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity="0.18" />
                  <stop offset="100%" stopColor="#6366f1" stopOpacity="0.00" />
                </linearGradient>
                {/* Stroke line glow filter */}
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Grid Lines */}
              {[0, 1, 2, 3, 4].map((gridLine) => {
                const yPos = paddingY + (gridLine / 4) * chartHeight;
                const gridPrice = maxPrice - (gridLine / 4) * priceRange;
                return (
                  <g key={gridLine} className="opacity-40">
                    <line
                      x1={paddingX}
                      y1={yPos}
                      x2={svgWidth - paddingX}
                      y2={yPos}
                      stroke="#18181b"
                      strokeWidth="1"
                      strokeDasharray="4 4"
                    />
                    <text
                      x={svgWidth - paddingX + 5}
                      y={yPos + 3}
                      fill="#52525b"
                      fontSize="9"
                      fontFamily="monospace"
                    >
                      ${gridPrice.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 0 })}
                    </text>
                  </g>
                );
              })}

              {/* Vertical timeline coordinate indicators */}
              {[0, 1, 2, 3].map((timeLine, i) => {
                const xPos = paddingX + (timeLine / 3) * chartWidth;
                const ptIndex = Math.round((timeLine / 3) * (points.length - 1));
                const point = points[ptIndex];
                if (!point) return null;

                const dateStr = new Date(history[ptIndex]?.timestamp).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                });

                return (
                  <g key={timeLine} className="opacity-40">
                    <line
                      x1={xPos}
                      y1={paddingY}
                      x2={xPos}
                      y2={svgHeight - paddingY}
                      stroke="#18181b"
                      strokeWidth="1"
                    />
                    <text
                      x={xPos}
                      y={svgHeight - paddingY + 14}
                      fill="#52525b"
                      fontSize="9"
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {dateStr}
                    </text>
                  </g>
                );
              })}

              {/* Volumes bar charts at the bottom */}
              {points.map((pt, idx) => {
                const barHeight = (volumes[idx] / maxVolume) * 45; // 45px max height
                const barWidth = Math.max(1, (chartWidth / points.length) * 0.7);
                return (
                  <rect
                    key={idx}
                    x={pt.x - barWidth / 2}
                    y={svgHeight - paddingY - barHeight}
                    width={barWidth}
                    height={barHeight}
                    fill="#4338ca"
                    opacity="0.12"
                  />
                );
              })}

              {/* Gradient Glowing Area Path */}
              {areaPath && (
                <path d={areaPath} fill={`url(#gradient-${selectedCoinId})`} />
              )}

              {/* Glow Stroke Line Path */}
              {dPath && (
                <path
                  d={dPath}
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="2.2"
                  filter="url(#glow)"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* Interactive Tooltip Cursor Crosshair */}
              {hoveredPoint && (
                <g>
                  {/* Vertical coordinate tracker */}
                  <line
                    x1={hoveredPoint.x}
                    y1={paddingY}
                    x2={hoveredPoint.x}
                    y2={svgHeight - paddingY}
                    stroke="#4f46e5"
                    strokeWidth="1"
                    strokeDasharray="2 2"
                    opacity="0.6"
                  />
                  {/* Horizontal coordinate tracker */}
                  <line
                    x1={paddingX}
                    y1={hoveredPoint.y}
                    x2={svgWidth - paddingX}
                    y2={hoveredPoint.y}
                    stroke="#4f46e5"
                    strokeWidth="1"
                    strokeDasharray="2 2"
                    opacity="0.6"
                  />
                  {/* Glow cursor dot */}
                  <circle
                    cx={hoveredPoint.x}
                    cy={hoveredPoint.y}
                    r="4.5"
                    fill="#818cf8"
                    stroke="#4f46e5"
                    strokeWidth="1.5"
                    filter="url(#glow)"
                  />
                </g>
              )}
            </svg>

            {/* Dynamic floating tooltip coordinate details */}
            {hoveredPoint && (
              <div
                id="chart-floating-tooltip"
                className="absolute bg-zinc-950 border border-indigo-500/30 p-2.5 rounded-lg shadow-xl z-20 pointer-events-none"
                style={{
                  left: `${(hoveredPoint.x / svgWidth) * 100}%`,
                  transform: hoveredPoint.x / svgWidth < 0.2
                    ? 'translateX(10%)'
                    : hoveredPoint.x / svgWidth > 0.8
                    ? 'translateX(-110%)'
                    : 'translateX(-50%)',
                  top: '12px',
                }}
              >
                <div className="text-[10px] font-bold text-indigo-400 font-mono tracking-wider">COORDINATE INSIGHT</div>
                <div className="text-xs font-black text-zinc-100 font-mono mt-0.5">
                  ${hoveredPoint.price.toLocaleString(undefined, {
                    minimumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 4 : 2,
                  })}
                </div>
                <div className="text-[9px] text-zinc-500 font-mono mt-0.5 leading-none">{hoveredPoint.date}</div>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2 justify-end text-[10px] text-zinc-600 font-mono">
            <span>* DOUBLE-TAP PERIOD TO INVALIDATE MEMORY RETRIEVAL (TTL MAPPED).</span>
          </div>

        </div>

        {/* QUANT ENGINE & TECHNICAL INDICATORS */}
        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} className="text-indigo-400 animate-pulse" />
              <span className="text-xs font-bold font-mono text-zinc-300 uppercase tracking-wider">QUANTITATIVE RATING ENGINE</span>
            </div>
            {indicators && (
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-semibold tracking-wider ${
                indicators.rating.includes('Strong Bullish') ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                indicators.rating.includes('Bullish') ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                indicators.rating.includes('Neutral') ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
                indicators.rating.includes('Strong Bearish') ? 'bg-rose-600/10 border-rose-600/30 text-rose-500' :
                'bg-rose-500/10 border-rose-500/30 text-rose-400'
              }`}>
                {indicators.rating.toUpperCase()}
              </span>
            )}
          </div>

          {!indicators ? (
            <div className="text-center py-6 text-xs font-mono text-zinc-500">
              SELECT A COIN OR INVALIDATE CACHE TO LOAD QUANT ANALYSIS
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
              {/* Gauge and Score details */}
              <div className="md:col-span-4 flex flex-col items-center justify-center p-4 bg-zinc-900/30 border border-zinc-900 rounded-xl text-center">
                <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-wider mb-2">Quant Score</span>
                <div className="relative w-24 h-24 flex items-center justify-center">
                  {/* Circular progress SVG */}
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                    <path
                      className="text-zinc-800"
                      strokeWidth="2.5"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                    <path
                      className={
                        indicators.score >= 80 ? 'text-emerald-400' :
                        indicators.score >= 60 ? 'text-green-400' :
                        indicators.score >= 40 ? 'text-amber-400' :
                        'text-rose-400'
                      }
                      strokeDasharray={`${indicators.score}, 100`}
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      stroke="currentColor"
                      fill="none"
                      d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    />
                  </svg>
                  <div className="absolute text-center">
                    <span className="text-xl font-black font-mono text-zinc-100">{indicators.score}</span>
                    <span className="block text-[8px] font-mono text-zinc-500 mt-0.5">SCORE</span>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-1.5">
                  <span className="text-[10px] font-mono text-zinc-400">Confidence:</span>
                  <span className="text-xs font-bold font-mono text-indigo-400">{indicators.confidence}%</span>
                </div>
              </div>

              {/* Grid of indicators */}
              <div className="md:col-span-8 grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* RSI */}
                <div className="p-3.5 bg-zinc-900/20 border border-zinc-900 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider block">RSI (14)</span>
                    <span className="text-base font-bold font-mono text-zinc-200 mt-1 block">{indicators.rsi}</span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[8px] font-mono text-zinc-500">MOMENTUM</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      indicators.rsi < 30 ? 'bg-emerald-500/10 text-emerald-400' :
                      indicators.rsi > 70 ? 'bg-rose-500/10 text-rose-400' :
                      'bg-zinc-800 text-zinc-400'
                    }`}>
                      {indicators.rsi < 30 ? 'OVERSOLD' : indicators.rsi > 70 ? 'OVERBOUGHT' : 'NEUTRAL'}
                    </span>
                  </div>
                </div>

                {/* EMA Trend */}
                <div className="p-3.5 bg-zinc-900/20 border border-zinc-900 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider block">EMA CROSS</span>
                    <span className="text-[11px] font-semibold font-mono text-zinc-300 mt-1 block">
                      20: ${indicators.ema20.toLocaleString(undefined, { minimumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 1 })}
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500 mt-0.5 block">
                      50: ${indicators.ema50.toLocaleString(undefined, { minimumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 1 })}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[8px] font-mono text-zinc-500">TREND</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      indicators.ema20 > indicators.ema50 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {indicators.ema20 > indicators.ema50 ? 'BULLISH' : 'BEARISH'}
                    </span>
                  </div>
                </div>

                {/* MACD */}
                <div className="p-3.5 bg-zinc-900/20 border border-zinc-900 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider block">MACD (12, 26, 9)</span>
                    <span className="text-[11px] font-semibold font-mono text-zinc-300 mt-1 block">
                      MACD: {indicators.macd.value}
                    </span>
                    <span className="text-[11px] font-mono text-zinc-500 mt-0.5 block">
                      Signal: {indicators.macd.signal}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[8px] font-mono text-zinc-500">CROSSOVER</span>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded font-semibold ${
                      indicators.macd.value > indicators.macd.signal ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {indicators.macd.value > indicators.macd.signal ? 'BULLISH' : 'BEARISH'}
                    </span>
                  </div>
                </div>

                {/* Bollinger Bands */}
                <div className="p-3.5 bg-zinc-900/20 border border-zinc-900 rounded-xl flex flex-col justify-between">
                  <div>
                    <span className="text-[9px] font-mono text-zinc-500 uppercase tracking-wider block">BOLLINGER BANDS (20, 2)</span>
                    <span className="text-[10px] font-mono text-zinc-300 mt-1 block">
                      Upper: ${indicators.bollinger.upper.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 1 })}
                    </span>
                    <span className="text-[10px] font-mono text-zinc-300 block">
                      Lower: ${indicators.bollinger.lower.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 1 })}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between">
                    <span className="text-[8px] font-mono text-zinc-500 font-semibold text-indigo-400">ATR: {indicators.atr}</span>
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400">
                      Mid: ${indicators.bollinger.middle.toLocaleString(undefined, { maximumFractionDigits: activeCoin.id === 'doge' || activeCoin.id === 'ada' ? 3 : 1 })}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
};
