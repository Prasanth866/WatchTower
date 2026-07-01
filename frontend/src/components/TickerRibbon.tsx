import React, { useEffect, useState, useRef } from 'react';
import { CoinInfo, CoinId } from '../types';
import { subscribeToPrices, SUPPORTED_COINS, subscribeToWsStatus } from '../api';
import { TrendingUp, TrendingDown } from 'lucide-react';

export const TickerRibbon: React.FC<{ onSelectCoin?: (id: CoinId) => void; selectedCoinId?: CoinId }> = ({
  onSelectCoin,
  selectedCoinId,
}) => {
  const [prices, setPrices] = useState<Record<CoinId, CoinInfo> | null>(null);
  const prevPricesRef = useRef<Record<CoinId, number>>({} as Record<CoinId, number>);
  const [tickDirections, setTickDirections] = useState<Record<CoinId, 'up' | 'down' | null>>({} as Record<CoinId, 'up' | 'down' | null>);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    const unsubscribe = subscribeToWsStatus((connected) => {
      setWsConnected(connected);
    });
    return () => unsubscribe();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeToPrices((latestPrices) => {
      // Check tick directions
      const newDirs: Record<CoinId, 'up' | 'down' | null> = { ...tickDirections };
      (Object.keys(latestPrices) as CoinId[]).forEach((id) => {
        const prevPrice = prevPricesRef.current[id];
        const newPrice = latestPrices[id].price;
        if (prevPrice !== undefined) {
          if (newPrice > prevPrice) {
            newDirs[id] = 'up';
          } else if (newPrice < prevPrice) {
            newDirs[id] = 'down';
          }
        }
        prevPricesRef.current[id] = newPrice;
      });

      setPrices(latestPrices);
      setTickDirections(newDirs);

      // Reset flash effect after 800ms
      const timer = setTimeout(() => {
        setTickDirections((prev) => {
          const reset: Record<CoinId, 'up' | 'down' | null> = { ...prev };
          (Object.keys(reset) as CoinId[]).forEach((id) => {
            reset[id] = null;
          });
          return reset;
        });
      }, 800);

      return () => clearTimeout(timer);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  if (!prices) {
    return (
      <div id="ticker-ribbon-loading" className="w-full h-14 bg-zinc-950 border-b border-zinc-900 flex items-center justify-between px-6 animate-pulse">
        <span className="text-xs text-zinc-600 font-mono">CONNECTING WS PROTOCOL...</span>
        <div className="flex gap-4">
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <div key={i} className="h-6 w-20 bg-zinc-900 rounded" />
          ))}
        </div>
      </div>
    );
  }

  const coinList = Object.values(prices) as CoinInfo[];

  return (
    <div id="ticker-ribbon-container" className="w-full bg-zinc-950/80 border-b border-zinc-900 overflow-x-auto select-none no-scrollbar backdrop-blur-md">
      <div className="flex items-center min-w-max px-4 py-2.5 gap-6">
        <div className={`flex items-center gap-1.5 px-3 py-1 border rounded-md transition-colors duration-300 ${wsConnected ? 'bg-indigo-500/10 border-indigo-500/20' : 'bg-rose-500/10 border-rose-500/20'}`}>
          <span className="relative flex h-2 w-2">
            {wsConnected && (
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            )}
            <span className={`relative inline-flex rounded-full h-2 w-2 ${wsConnected ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
          </span>
          <span className={`text-[10px] font-mono tracking-widest font-bold ${wsConnected ? 'text-indigo-400' : 'text-rose-400'}`}>
            {wsConnected ? 'WS:LIVE' : 'WS:OFFLINE'}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {coinList.map((coin) => {
            const direction = tickDirections[coin.id];
            const isUp = coin.change24h >= 0;
            const isSelected = selectedCoinId === coin.id;

            let tickClass = 'border-transparent';
            if (direction === 'up') {
              tickClass = 'bg-emerald-500/10 border-emerald-500/40 shadow-[0_0_8px_rgba(16,185,129,0.15)]';
            } else if (direction === 'down') {
              tickClass = 'bg-rose-500/10 border-rose-500/40 shadow-[0_0_8px_rgba(244,63,94,0.15)]';
            }

            return (
              <button
                key={coin.id}
                id={`ticker-item-${coin.id}`}
                onClick={() => onSelectCoin?.(coin.id)}
                className={`flex items-center gap-3 px-3.5 py-1.5 rounded-lg border text-left cursor-pointer transition-all duration-300 ${tickClass} ${
                  isSelected
                    ? 'bg-zinc-900/60 border-zinc-800 shadow-[0_0_12px_rgba(99,102,241,0.08)]'
                    : 'hover:bg-zinc-900/40 hover:border-zinc-800'
                }`}
              >
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-zinc-200 font-mono leading-none tracking-wide">
                    {coin.symbol}
                  </span>
                  <span className="text-[9px] text-zinc-500 font-mono mt-0.5">
                    {SUPPORTED_COINS[coin.id].name}
                  </span>
                </div>

                <div className="flex flex-col items-end pl-1">
                  <span className={`text-xs font-semibold font-mono leading-none transition-colors duration-200 ${
                    direction === 'up' ? 'text-emerald-400' : direction === 'down' ? 'text-rose-400' : 'text-zinc-100'
                  }`}>
                    ${coin.price.toLocaleString(undefined, {
                      minimumFractionDigits: coin.id === 'doge' || coin.id === 'ada' ? 4 : 2,
                      maximumFractionDigits: coin.id === 'doge' || coin.id === 'ada' ? 4 : 2,
                    })}
                  </span>
                  <span className={`text-[9px] font-mono font-medium flex items-center gap-0.5 mt-0.5 leading-none ${
                    isUp ? 'text-emerald-400' : 'text-rose-400'
                  }`}>
                    {isUp ? <TrendingUp size={8} /> : <TrendingDown size={8} />}
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
  );
};
