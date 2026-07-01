import React, { useState, useEffect } from 'react';
import { api, SUPPORTED_COINS, subscribeToPrices } from '../api';
import { CoinId, Portfolio, Holding, Transaction } from '../types';
import { useToast } from './ToastProvider';
import { Landmark, TrendingUp, TrendingDown, ArrowDownLeft, ArrowUpRight, History, PieChart, RefreshCcw, Briefcase, HelpCircle, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export const TradingTerminal: React.FC = () => {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [holdings, setHoldings] = useState<Holding[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [activeTab, setActiveTab] = useState<'positions' | 'transactions'>('positions');
  const [livePrices, setLivePrices] = useState<Record<CoinId, number>>({} as Record<CoinId, number>);

  // Live Trading Form States
  const [tradeAction, setTradeAction] = useState<'buy' | 'sell'>('buy');
  const [selectedCoin, setSelectedCoin] = useState<CoinId>('btc');
  
  // Buy Form
  const [buyAmountUsd, setBuyAmountUsd] = useState('');
  
  // Sell Form
  const [sellQuantity, setSellQuantity] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [isResetConfirmOpen, setIsResetConfirmOpen] = useState(false);
  const { addToast } = useToast();

  const loadData = async () => {
    try {
      const [port, holds, txs] = await Promise.all([
        api.getPortfolio(),
        api.getHoldings(),
        api.getTransactions(),
      ]);
      
      setPortfolio(port);
      setHoldings(holds);
      setTransactions(txs);
    } catch {
      addToast('error', 'Sync Failure', 'Failed to synchronize paper trading balances.');
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    const unsubscribe = subscribeToPrices((latestPrices) => {
      const pricesMap = {} as Record<CoinId, number>;
      (Object.keys(latestPrices) as CoinId[]).forEach((coinId) => {
        pricesMap[coinId] = latestPrices[coinId].price;
      });
      setLivePrices(pricesMap);
    });
    return () => unsubscribe();
  }, []);

  const handleBuy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    const amount = parseFloat(buyAmountUsd);
    if (isNaN(amount) || amount <= 0) {
      addToast('error', 'Trading Error', 'Please specify a positive USD purchase amount.');
      return;
    }

    setIsLoading(true);
    try {
      await api.buyAsset(selectedCoin, amount);
      addToast(
        'success',
        'Order Executed',
        `BUY order completed: Spent $${amount.toLocaleString()} USD on ${selectedCoin.toUpperCase()}.`
      );
      setBuyAmountUsd('');
      await loadData();
    } catch (err: any) {
      addToast('error', 'Execution Denied', err.message || 'Broker refused purchase order.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSell = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isLoading) return;
    const quantity = parseFloat(sellQuantity);
    if (isNaN(quantity) || quantity <= 0) {
      addToast('error', 'Trading Error', 'Please specify a positive asset quantity to sell.');
      return;
    }

    setIsLoading(true);
    try {
      await api.sellAsset(selectedCoin, quantity);
      addToast(
        'success',
        'Order Executed',
        `SELL order completed: Liquidated ${quantity} ${selectedCoin.toUpperCase()} to cash.`
      );
      setSellQuantity('');
      await loadData();
    } catch (err: any) {
      addToast('error', 'Execution Denied', err.message || 'Broker refused sell order.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickPercentBuy = (percent: number) => {
    if (!portfolio) return;
    const targetAmount = Math.floor(portfolio.cash_balance * percent);
    setBuyAmountUsd(targetAmount > 0 ? targetAmount.toString() : '');
  };

  const handleResetAccount = async () => {
    setIsLoading(true);
    try {
      const res = await api.resetPaperTrading();
      addToast('success', 'Terminal Cleared', res.message);
      setIsResetConfirmOpen(false);
      await loadData();
    } catch {
      addToast('error', 'Reset Failed', 'Failed to reset paper trading baseline.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!portfolio) {
    return (
      <div id="trading-terminal-loading" className="w-full h-96 bg-zinc-950/40 border border-zinc-900 rounded-2xl animate-pulse flex items-center justify-center">
        <span className="text-xs text-zinc-600 font-mono">ALIGNING CLEARING PROTOCOLS...</span>
      </div>
    );
  }

  // Dynamic frontend calculations using live prices
  const holdingsValue = holdings.reduce((sum, h) => {
    const coinId = h.coin.toLowerCase() as CoinId;
    const livePrice = livePrices[coinId] || h.average_buy_price;
    return sum + (h.quantity * livePrice);
  }, 0);

  const totalValue = portfolio.cash_balance + holdingsValue;
  const totalPnL = totalValue - portfolio.initial_balance;
  const totalPnLPct = portfolio.initial_balance > 0 ? (totalPnL / portfolio.initial_balance) * 100 : 0;
  const isPnLUp = totalPnL >= 0;

  // Custom SVG Donut allocation metrics calculation
  const totalAlloc = totalValue > 0 ? totalValue : 1;
  const cashPercent = (portfolio.cash_balance / totalAlloc) * 100;
  const cryptoPercent = (holdingsValue / totalAlloc) * 100;

  // SVG Pie chart helper parameters (radius 32, center 50)
  const r = 32;
  const circ = 2 * Math.PI * r;
  const cashStrokeDash = (cashPercent / 100) * circ;
  const cryptoStrokeDash = (cryptoPercent / 100) * circ;

  return (
    <div id="trading-terminal-container" className="flex flex-col gap-6">
      
      {/* 1. Portfolio Header Stats Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        
        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-lg md:col-span-2 flex justify-between items-center relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-[0.03] text-indigo-400 pointer-events-none">
            <Briefcase size={80} />
          </div>
          <div className="z-10">
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest block mb-1">TOTAL PORTFOLIO NET WORTH</span>
            <span className="text-3xl font-black font-mono text-zinc-100 tracking-tight leading-none block">
              ${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span className={`text-xs font-mono font-bold flex items-center gap-1 mt-2.5 leading-none ${
              isPnLUp ? 'text-emerald-400' : 'text-rose-400'
            }`}>
              {isPnLUp ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {isPnLUp ? '+' : ''}${totalPnL.toLocaleString()} ({isPnLUp ? '+' : ''}{totalPnLPct.toFixed(2)}%)
            </span>
          </div>

          {/* Mini Donut visualization */}
          <div className="flex items-center gap-3">
            <svg viewBox="0 0 100 100" className="w-16 h-16 transform -rotate-90">
              <circle cx="50" cy="50" r={r} fill="transparent" stroke="#18181b" strokeWidth="12" />
              <circle
                cx="50"
                cy="50"
                r={r}
                fill="transparent"
                stroke="#6366f1"
                strokeWidth="12"
                strokeDasharray={`${cryptoStrokeDash} ${circ}`}
                strokeDashoffset={0}
              />
              <circle
                cx="50"
                cy="50"
                r={r}
                fill="transparent"
                stroke="#10b981"
                strokeWidth="12"
                strokeDasharray={`${cashStrokeDash} ${circ}`}
                strokeDashoffset={-cryptoStrokeDash}
              />
            </svg>
            <div className="text-[10px] font-mono space-y-1">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-emerald-500" />
                <span className="text-zinc-400 font-bold">CASH: {cashPercent.toFixed(0)}%</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded bg-indigo-500" />
                <span className="text-zinc-400 font-bold">CRYPTO: {cryptoPercent.toFixed(0)}%</span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest block mb-1">USD LIQUID BALANCE</span>
            <span className="text-xl font-extrabold font-mono text-zinc-100 block">
              ${portfolio.cash_balance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className="text-[10px] font-mono text-zinc-600 mt-2 block">
            BASELINE CRITERIA: $100,000.00
          </span>
        </div>

        <div className="bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-5 backdrop-blur-md shadow-lg flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-mono text-zinc-500 uppercase tracking-widest block mb-1">HOLDINGS VALUATION</span>
            <span className="text-xl font-extrabold font-mono text-indigo-400 block">
              ${holdingsValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
          <span className="text-[10px] font-mono text-zinc-600 mt-2 block">
            PRICES UPDATE VIA WS
          </span>
        </div>

      </div>

      {/* 2. Main Desk Panel: Place Trades on Left, Positions list on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Live Trading Desk form (Left) */}
        <div className="lg:col-span-5 bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl">
          <div className="flex justify-between items-center pb-3 border-b border-zinc-900 mb-5">
            <span className="text-xs font-bold font-mono text-zinc-300 uppercase tracking-wider">LIVE BROKER TRADING DESK</span>
            <Landmark size={14} className="text-zinc-500" />
          </div>

          {/* Tab Buy vs Sell */}
          <div className="grid grid-cols-2 gap-2 p-1 bg-zinc-900 rounded-lg border border-zinc-850 mb-5">
            <button
              id="trade-tab-buy"
              onClick={() => setTradeAction('buy')}
              className={`py-2 text-xs font-mono font-bold rounded-md cursor-pointer transition-all ${
                tradeAction === 'buy'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              LONG (BUY)
            </button>
            <button
              id="trade-tab-sell"
              onClick={() => setTradeAction('sell')}
              className={`py-2 text-xs font-mono font-bold rounded-md cursor-pointer transition-all ${
                tradeAction === 'sell'
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-300'
              }`}
            >
              SHORT (SELL)
            </button>
          </div>

          {tradeAction === 'buy' ? (
            /* BUY FORM */
            <form onSubmit={handleBuy} className="space-y-4">
              <div>
                <label className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">ASSET SELECTION</label>
                <select
                  id="buy-coin-select"
                  value={selectedCoin}
                  onChange={(e) => setSelectedCoin(e.target.value as CoinId)}
                  className="w-full h-11 bg-zinc-900 border border-zinc-800 focus:border-indigo-500 rounded-lg px-3 text-sm text-zinc-200 outline-none"
                >
                  {(Object.keys(SUPPORTED_COINS) as CoinId[]).map((id) => (
                    <option key={id} value={id}>
                      {SUPPORTED_COINS[id].symbol} - {SUPPORTED_COINS[id].name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">PURCHASE USD AMOUNT</label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-500 text-sm font-mono">$</span>
                  <input
                    id="buy-amount-input"
                    type="number"
                    step="any"
                    min="0"
                    required
                    value={buyAmountUsd}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === '' || parseFloat(val) >= 0) {
                        setBuyAmountUsd(val);
                      }
                    }}
                    placeholder="Enter amount in USD"
                    className="w-full h-11 bg-zinc-900 border border-zinc-800 focus:border-emerald-500 rounded-lg pl-8 pr-4 text-sm font-mono text-zinc-200 outline-none"
                  />
                </div>

                {/* Quick percentages wallet limits buttons */}
                <div className="grid grid-cols-3 gap-2 mt-2.5">
                  <button
                    id="buy-percent-25"
                    type="button"
                    onClick={() => handleQuickPercentBuy(0.25)}
                    className="h-8 bg-zinc-900 border border-zinc-850 hover:bg-zinc-850 rounded text-[10px] font-mono text-zinc-400"
                  >
                    25% WALLET
                  </button>
                  <button
                    id="buy-percent-50"
                    type="button"
                    onClick={() => handleQuickPercentBuy(0.50)}
                    className="h-8 bg-zinc-900 border border-zinc-850 hover:bg-zinc-850 rounded text-[10px] font-mono text-zinc-400"
                  >
                    50% WALLET
                  </button>
                  <button
                    id="buy-percent-100"
                    type="button"
                    onClick={() => handleQuickPercentBuy(1.00)}
                    className="h-8 bg-zinc-900 border border-zinc-850 hover:bg-zinc-850 rounded text-[10px] font-mono text-zinc-400"
                  >
                    ALL-IN Max
                  </button>
                </div>
              </div>

              <button
                id="submit-buy-btn"
                type="submit"
                disabled={isLoading}
                className="w-full h-11 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-850 text-white font-bold text-xs font-mono tracking-widest uppercase rounded-lg cursor-pointer transition-colors mt-2"
              >
                {isLoading ? 'TRANSACTING ORDER...' : `EXECUTE MARKET BUY (${selectedCoin.toUpperCase()})`}
              </button>
            </form>
          ) : (
            /* SELL FORM */
            <form onSubmit={handleSell} className="space-y-4">
              <div>
                <label className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">ASSET SELECTION</label>
                <select
                  id="sell-coin-select"
                  value={selectedCoin}
                  onChange={(e) => setSelectedCoin(e.target.value as CoinId)}
                  className="w-full h-11 bg-zinc-900 border border-zinc-800 focus:border-indigo-500 rounded-lg px-3 text-sm text-zinc-200 outline-none"
                >
                  {(Object.keys(SUPPORTED_COINS) as CoinId[]).map((id) => (
                    <option key={id} value={id}>
                      {SUPPORTED_COINS[id].symbol} - {SUPPORTED_COINS[id].name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-mono text-zinc-500 uppercase tracking-widest mb-1.5">SELL QUANTITY</label>
                <div className="relative">
                  <input
                    id="sell-quantity-input"
                    type="number"
                    step="any"
                    min="0"
                    required
                    value={sellQuantity}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === '' || parseFloat(val) >= 0) {
                        setSellQuantity(val);
                      }
                    }}
                    placeholder={`Enter amount in ${SUPPORTED_COINS[selectedCoin].symbol}`}
                    className="w-full h-11 bg-zinc-900 border border-zinc-800 focus:border-rose-500 rounded-lg px-4 text-sm font-mono text-zinc-200 outline-none"
                  />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-zinc-500 font-semibold uppercase">
                    {SUPPORTED_COINS[selectedCoin].symbol}
                  </span>
                </div>
              </div>

              <button
                id="submit-sell-btn"
                type="submit"
                disabled={isLoading}
                className="w-full h-11 bg-rose-600 hover:bg-rose-500 disabled:bg-rose-850 text-white font-bold text-xs font-mono tracking-widest uppercase rounded-lg cursor-pointer transition-colors mt-2"
              >
                {isLoading ? 'TRANSACTING ORDER...' : `EXECUTE MARKET SELL (${selectedCoin.toUpperCase()})`}
              </button>
            </form>
          )}

          {/* Account Reset safety button */}
          <div className="border-t border-zinc-900/60 pt-4 mt-6">
            <button
              id="reset-account-trigger"
              onClick={() => setIsResetConfirmOpen(true)}
              className="w-full h-9 bg-zinc-900 border border-zinc-850 hover:bg-rose-950/10 hover:border-rose-900/20 text-[10px] font-mono font-bold tracking-widest uppercase text-zinc-500 hover:text-rose-400 rounded-lg transition-all cursor-pointer flex items-center justify-center gap-1.5"
            >
              <RefreshCcw size={12} />
              Reset Paper Account Baseline
            </button>
          </div>
        </div>

        {/* Tabbed Ledgers (Right - col-span-7) */}
        <div className="lg:col-span-7 bg-zinc-950/80 border border-zinc-800/80 rounded-2xl p-6 backdrop-blur-md shadow-xl flex flex-col gap-5 min-h-[420px]">
          
          {/* Ledger Navigation Header */}
          <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
            <div className="flex gap-4">
              <button
                id="ledger-tab-positions"
                onClick={() => setActiveTab('positions')}
                className={`text-xs font-bold font-mono tracking-wider cursor-pointer uppercase transition-colors pb-3.5 -mb-3.5 ${
                  activeTab === 'positions'
                    ? 'text-indigo-400 border-b-2 border-indigo-500'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                Positions & Holdings ({holdings.length})
              </button>
              <button
                id="ledger-tab-transactions"
                onClick={() => setActiveTab('transactions')}
                className={`text-xs font-bold font-mono tracking-wider cursor-pointer uppercase transition-colors pb-3.5 -mb-3.5 ${
                  activeTab === 'transactions'
                    ? 'text-indigo-400 border-b-2 border-indigo-500'
                    : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                Order Audit Ledger ({transactions.length})
              </button>
            </div>
            
            <Briefcase size={14} className="text-zinc-500" />
          </div>

          {/* Tab Render positioning */}
          {activeTab === 'positions' ? (
            /* TAB A: ACTIVE POSITIONS */
            <div className="overflow-x-auto no-scrollbar">
              {holdings.length === 0 ? (
                <div id="positions-empty" className="flex flex-col items-center justify-center py-14 text-center">
                  <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mb-3">
                    <Briefcase size={16} />
                  </div>
                  <span className="text-xs font-bold text-zinc-400">Clear Portfolio State</span>
                  <p className="text-[10px] text-zinc-600 mt-1 max-w-xs leading-relaxed">
                    You currently hold no crypto assets. Execute a BUY order using your cash balance to allocate assets.
                  </p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-900 text-[9px] font-mono text-zinc-500 uppercase tracking-wider">
                      <th className="pb-3 font-medium">Symbol</th>
                      <th className="pb-3 font-medium">Quantity</th>
                      <th className="pb-3 font-medium">Avg Cost</th>
                      <th className="pb-3 font-medium">Live Price</th>
                      <th className="pb-3 font-medium">Asset Value</th>
                      <th className="pb-3 font-medium text-right">Return (ROI)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/40 text-xs font-mono">
                    {holdings.map((h) => {
                      const coinId = h.coin.toLowerCase() as CoinId;
                      const livePrice = livePrices[coinId] || h.average_buy_price;
                      const marketValue = h.quantity * livePrice;
                      const costBasis = h.quantity * h.average_buy_price;
                      const roiValue = marketValue - costBasis;
                      const roiPercent = costBasis > 0 ? (roiValue / costBasis) * 100 : 0;
                      const isRoiUp = roiValue >= 0;

                      return (
                        <tr key={h.coin} className="hover:bg-zinc-900/20">
                          <td className="py-3.5 font-bold text-zinc-200">{h.coin}</td>
                          <td className="py-3.5 text-zinc-400">{h.quantity}</td>
                          <td className="py-3.5 text-zinc-400">${h.average_buy_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="py-3.5 text-zinc-400">${livePrice.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="py-3.5 font-bold text-zinc-200">${marketValue.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className={`py-3.5 text-right font-bold ${isRoiUp ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {isRoiUp ? '+' : ''}{roiPercent.toFixed(2)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          ) : (
            /* TAB B: HISTORIC TRANSACTIONS AUDIT */
            <div className="overflow-x-auto no-scrollbar max-h-[380px]">
              {transactions.length === 0 ? (
                <div id="transactions-empty" className="flex flex-col items-center justify-center py-14 text-center">
                  <div className="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mb-3">
                    <History size={16} />
                  </div>
                  <span className="text-xs font-bold text-zinc-400">Audit Ledger Vacant</span>
                  <p className="text-[10px] text-zinc-600 mt-1">No execution logs registered in memory cache.</p>
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-zinc-900 text-[9px] font-mono text-zinc-500 uppercase tracking-wider">
                      <th className="pb-3 font-medium">Timestamp</th>
                      <th className="pb-3 font-medium">Type</th>
                      <th className="pb-3 font-medium">Symbol</th>
                      <th className="pb-3 font-medium">Quantity</th>
                      <th className="pb-3 font-medium">Executed Price</th>
                      <th className="pb-3 font-medium text-right">Gross USD</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-900/40 text-xs font-mono">
                    {transactions.map((tx) => {
                      const isBuy = tx.type === 'BUY';
                      return (
                        <tr key={tx.id} className="hover:bg-zinc-900/20">
                          <td className="py-3 text-zinc-500 text-[10px]">
                            {new Date(tx.created_at).toLocaleTimeString()}
                          </td>
                          <td className="py-3">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold tracking-widest ${
                              isBuy ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                            }`}>
                              {tx.type.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-3 font-bold text-zinc-300">{tx.coin}</td>
                          <td className="py-3 text-zinc-400">{tx.quantity}</td>
                          <td className="py-3 text-zinc-400">${tx.price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                          <td className="py-3 text-right font-bold text-zinc-200">
                            ${tx.total.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}

        </div>

      </div>

      {/* Safety Reset dialog modal */}
      {isResetConfirmOpen && (
        <div id="reset-confirm-overlay" className="fixed inset-0 bg-black/85 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="w-full max-w-sm bg-zinc-950 border border-zinc-800 rounded-xl overflow-hidden p-6"
          >
            <div className="flex items-center gap-3 text-rose-400 pb-3 border-b border-zinc-900 mb-4">
              <AlertTriangle size={24} />
              <h3 className="text-sm font-bold font-mono tracking-widest uppercase">HARD RESET WARNING</h3>
            </div>

            <p className="text-xs text-zinc-400 leading-relaxed font-sans mb-6">
              You are about to initiate a terminal clearing action. This will permanently wipe all historic paper trading logs, positions holdings, and restore your liquid cash to the default baseline of <span className="text-zinc-200 font-bold">$100,000.00 USD</span>. This action is irreversible.
            </p>

            <div className="flex justify-end gap-3 font-mono text-[11px] font-bold">
              <button
                id="reset-cancel-btn"
                onClick={() => setIsResetConfirmOpen(false)}
                className="px-4 py-2 bg-zinc-900 text-zinc-400 hover:bg-zinc-850 hover:text-zinc-200 rounded-lg cursor-pointer transition-all"
              >
                CANCEL
              </button>
              <button
                id="reset-confirm-btn"
                onClick={handleResetAccount}
                className="px-4 py-2 bg-rose-600 text-white hover:bg-rose-500 rounded-lg cursor-pointer transition-all"
              >
                CONFIRM RESET
              </button>
            </div>
          </motion.div>
        </div>
      )}

    </div>
  );
};
