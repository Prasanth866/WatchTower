"""Technical Indicators Calculator Service"""
import json
from typing import Any
import pandas as pd
import numpy as np

class IndicatorService:
    @staticmethod
    def compute_all(prices_with_timestamps: list[list[Any]]) -> dict:
        """
        Computes technical indicators, quant score, and confidence rating.
        prices_with_timestamps is a list of [timestamp, price].
        """
        if not prices_with_timestamps or len(prices_with_timestamps) < 2:
            return {}

        try:
            # Convert to pandas DataFrame
            df = pd.DataFrame(prices_with_timestamps, columns=["timestamp", "price"])
            df["price"] = df["price"].astype(float)
            prices = df["price"]

            n = len(prices)
            if n < 50:
                # Fallback parameters for short data series (e.g. initial launch or test data)
                span_fast = min(12, max(2, n // 4))
                span_slow = min(26, max(3, n // 2))
                span_signal = min(9, max(2, n // 5))
                window_rsi = min(14, max(2, n // 3))
                window_bb = min(20, max(2, n // 3))
                window_atr = min(14, max(2, n // 3))
                span_ema20 = min(20, max(2, n // 3))
                span_ema50 = min(50, max(3, n // 2))
            else:
                span_fast = 12
                span_slow = 26
                span_signal = 9
                window_rsi = 14
                window_bb = 20
                window_atr = 14
                span_ema20 = 20
                span_ema50 = 50

            # 1. EMA 20 & 50
            df["ema20"] = prices.ewm(span=span_ema20, adjust=False).mean()
            df["ema50"] = prices.ewm(span=span_ema50, adjust=False).mean()

            # 2. RSI 14
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=window_rsi).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=window_rsi).mean()
            rs = gain / (loss + 1e-10)
            df["rsi"] = 100 - (100 / (1 + rs))

            # 3. MACD (12, 26, 9)
            df["ema12"] = prices.ewm(span=span_fast, adjust=False).mean()
            df["ema26"] = prices.ewm(span=span_slow, adjust=False).mean()
            df["macd"] = df["ema12"] - df["ema26"]
            df["macd_signal"] = df["macd"].ewm(span=span_signal, adjust=False).mean()

            # 4. Bollinger Bands (20, 2)
            df["bb_middle"] = prices.rolling(window=window_bb).mean()
            df["bb_std"] = prices.rolling(window=window_bb).std()
            df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
            df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]

            # 5. ATR (Average True Range) 14 - approximated on close-to-close differences
            df["tr"] = delta.abs()
            df["atr"] = df["tr"].rolling(window=window_atr).mean()

            # Clean NaNs
            df = df.bfill().ffill()

            # Default fallback if standard deviation is NaN
            df["bb_upper"] = df["bb_upper"].fillna(df["price"])
            df["bb_lower"] = df["bb_lower"].fillna(df["price"])
            df["bb_middle"] = df["bb_middle"].fillna(df["price"])
            df["rsi"] = df["rsi"].fillna(50.0)
            df["macd"] = df["macd"].fillna(0.0)
            df["macd_signal"] = df["macd_signal"].fillna(0.0)
            df["atr"] = df["atr"].fillna(0.0)

            latest = df.iloc[-1]

            price_val = float(latest["price"])
            rsi_val = float(latest["rsi"])
            ema20_val = float(latest["ema20"])
            ema50_val = float(latest["ema50"])
            macd_val = float(latest["macd"])
            macd_sig_val = float(latest["macd_signal"])
            bb_middle_val = float(latest["bb_middle"])
            bb_upper_val = float(latest["bb_upper"])
            bb_lower_val = float(latest["bb_lower"])
            atr_val = float(latest["atr"])

            signals = []

            # RSI Signal rules
            if rsi_val < 30:
                rsi_sig = "Bullish"
                rsi_contrib = 20
            elif rsi_val > 70:
                rsi_sig = "Bearish"
                rsi_contrib = 0
            elif rsi_val > 50:
                rsi_sig = "Bullish"
                rsi_contrib = 15
            else:
                rsi_sig = "Bearish"
                rsi_contrib = 5
            signals.append(rsi_sig)

            # MACD Crossover rules
            macd_sig = "Bullish" if macd_val > macd_sig_val else "Bearish"
            macd_contrib = 20 if macd_sig == "Bullish" else 0
            signals.append(macd_sig)

            # EMA Trend Crossover rules
            ema_sig = "Bullish" if ema20_val > ema50_val else "Bearish"
            ema_contrib = 20 if ema_sig == "Bullish" else 0
            signals.append(ema_sig)

            # Bollinger Bands rules
            if price_val <= bb_lower_val:
                bb_sig = "Bullish"
                bb_contrib = 20
            elif price_val >= bb_upper_val:
                bb_sig = "Bearish"
                bb_contrib = 0
            elif price_val >= bb_middle_val:
                bb_sig = "Bullish"
                bb_contrib = 15
            else:
                bb_sig = "Bearish"
                bb_contrib = 5
            signals.append(bb_sig)

            # Price vs EMA20 rule
            price_vs_ema_sig = "Bullish" if price_val > ema20_val else "Bearish"
            price_vs_ema_contrib = 20 if price_vs_ema_sig == "Bullish" else 0
            signals.append(price_vs_ema_sig)

            # Compute Score & Rating
            score = rsi_contrib + macd_contrib + ema_contrib + bb_contrib + price_vs_ema_contrib

            if score >= 80:
                rating = "Strong Bullish"
            elif score >= 60:
                rating = "Bullish"
            elif score >= 40:
                rating = "Neutral"
            elif score >= 20:
                rating = "Bearish"
            else:
                rating = "Strong Bearish"

            # Compute Confidence (%)
            bullish_count = sum(1 for s in signals if s == "Bullish")
            bearish_count = sum(1 for s in signals if s == "Bearish")
            majority_count = max(bullish_count, bearish_count)
            confidence = int((majority_count / len(signals)) * 100)

            return {
                "rsi": round(rsi_val, 2),
                "ema20": round(ema20_val, 2),
                "ema50": round(ema50_val, 2),
                "macd": {
                    "value": round(macd_val, 2),
                    "signal": round(macd_sig_val, 2)
                },
                "bollinger": {
                    "middle": round(bb_middle_val, 2),
                    "upper": round(bb_upper_val, 2),
                    "lower": round(bb_lower_val, 2)
                },
                "atr": round(atr_val, 2),
                "score": score,
                "confidence": confidence,
                "rating": rating
            }

        except Exception as e:
            # Fallback values if computation encounters numerical edge cases
            return {
                "rsi": 50.0,
                "ema20": 0.0,
                "ema50": 0.0,
                "macd": {"value": 0.0, "signal": 0.0},
                "bollinger": {"middle": 0.0, "upper": 0.0, "lower": 0.0},
                "atr": 0.0,
                "score": 50,
                "confidence": 100,
                "rating": "Neutral"
            }
