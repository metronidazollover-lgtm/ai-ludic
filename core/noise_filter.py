"""
Ludic2 Crypto Noise Filter v6.0
Adapted from Ludic1 OTC-Screener v5.0 for crypto markets.

Filters out noisy, unreliable market conditions before entering a trade.
"""
import logging
from dataclasses import dataclass

import pandas as pd
import numpy as np

from ludic2 import config

logger = logging.getLogger("ludic2.noise_filter")


@dataclass
class FilterResult:
    """Result of a noise filter check."""
    passed: bool
    checks: list[tuple[str, bool, str]]  # (check_name, passed, detail)

    @property
    def summary(self) -> str:
        status = "✅ PASSED" if self.passed else "❌ BLOCKED"
        details = "\n".join(
            f"  {'✅' if ok else '❌'} {name}: {detail}"
            for name, ok, detail in self.checks
        )
        return f"Noise Filter: {status}\n{details}"


class CryptoNoiseFilter:
    """
    Crypto Noise Filter v6.0
    Evolved from Ludic1 OTC-Screener v5.0:
      - Shadow Threshold (v5.0)
      - Impulse Integrity (v5.0)
      - Anti-Sweep (v5.0)
      + ATR Volatility Gate (v6.0 NEW)
      + Volume Confirmation (v6.0 NEW)
    """

    def __init__(
        self,
        wick_threshold: float = config.NOISE_WICK_THRESHOLD,
        hostile_wick: float = config.NOISE_HOSTILE_WICK,
        atr_anomaly: float = config.ATR_ANOMALY_MULTIPLIER,
    ):
        self.wick_threshold = wick_threshold
        self.hostile_wick = hostile_wick
        self.atr_anomaly = atr_anomaly

    def check(self, df: pd.DataFrame, direction: str) -> FilterResult:
        """
        Run all noise filter checks.

        Args:
            df: OHLCV DataFrame with indicators (from indicators.add_all_indicators)
            direction: 'LONG' or 'SHORT'

        Returns:
            FilterResult with pass/fail and detailed check results
        """
        if len(df) < 20:
            return FilterResult(
                passed=False,
                checks=[("Data", False, "Insufficient data (need ≥20 candles)")]
            )

        checks = []

        # === Check 1: Shadow Threshold (from OTC-Screener v5.0) ===
        # Avg wick ratio of last 5 candles must be < 40%
        last_5 = df["wick_ratio"].iloc[-5:]
        avg_wick = last_5.mean()
        shadow_ok = avg_wick <= self.wick_threshold
        checks.append((
            "Shadow Threshold",
            shadow_ok,
            f"Avg wick: {avg_wick:.0%} {'≤' if shadow_ok else '>'} {self.wick_threshold:.0%}"
        ))

        # === Check 2: Impulse Integrity (from OTC-Screener v5.0) ===
        # At least 2 consecutive full-body candles in trade direction
        last_3 = df.iloc[-3:]
        if direction == "LONG":
            impulse_candles = last_3["is_bullish"] & last_3["is_full_body"]
        else:
            impulse_candles = last_3["is_bearish"] & last_3["is_full_body"]

        # Check for at least 2 consecutive
        consecutive_count = 0
        max_consecutive = 0
        for val in impulse_candles:
            if val:
                consecutive_count += 1
                max_consecutive = max(max_consecutive, consecutive_count)
            else:
                consecutive_count = 0

        impulse_ok = max_consecutive >= 2
        checks.append((
            "Impulse Integrity",
            impulse_ok,
            f"{max_consecutive} consecutive full-body candles (need ≥2)"
        ))

        # === Check 3: Anti-Sweep (from OTC-Screener v5.0) ===
        # Last candle must not have a hostile wick > 50%
        last_candle = df.iloc[-1]
        full_range = last_candle["full_range"]

        if full_range and full_range > 0:
            if direction == "LONG":
                hostile = last_candle["upper_wick"] / full_range
            else:
                hostile = last_candle["lower_wick"] / full_range
        else:
            hostile = 0

        sweep_ok = hostile <= self.hostile_wick
        checks.append((
            "Anti-Sweep",
            sweep_ok,
            f"Hostile wick: {hostile:.0%} {'≤' if sweep_ok else '>'} {self.hostile_wick:.0%}"
        ))

        # === Check 4: ATR Volatility Gate (NEW in v6.0) ===
        # Current ATR must be within normal range (not too extreme)
        if "atr" in df.columns and not df["atr"].isna().all():
            current_atr = df["atr"].iloc[-1]
            avg_atr = df["atr"].iloc[-100:].mean() if len(df) >= 100 else df["atr"].mean()

            if avg_atr > 0:
                atr_ratio = current_atr / avg_atr
                atr_too_high = atr_ratio > self.atr_anomaly
                atr_too_low = atr_ratio < 0.3
                atr_ok = not atr_too_high and not atr_too_low

                if atr_too_high:
                    atr_detail = f"ATR ratio: {atr_ratio:.1f}x (TOO HIGH, anomaly)"
                elif atr_too_low:
                    atr_detail = f"ATR ratio: {atr_ratio:.1f}x (TOO LOW, flat market)"
                else:
                    atr_detail = f"ATR ratio: {atr_ratio:.1f}x (normal)"
            else:
                atr_ok = False
                atr_detail = "ATR avg is 0"
        else:
            atr_ok = True
            atr_detail = "ATR not available, skipped"

        checks.append(("ATR Gate", atr_ok, atr_detail))

        # === Check 5: Volume Confirmation (NEW in v6.0) ===
        # Last candle volume should not be drastically below average
        if "vol_ratio" in df.columns:
            vol_ratio = df["vol_ratio"].iloc[-1]
            vol_ok = vol_ratio >= 0.5  # At least 50% of average volume
            checks.append((
                "Volume",
                vol_ok,
                f"Vol ratio: {vol_ratio:.1f}x avg {'(OK)' if vol_ok else '(too thin)'}"
            ))
        else:
            vol_ok = True
            checks.append(("Volume", True, "Volume data not available, skipped"))

        # === Final verdict ===
        all_passed = all(ok for _, ok, _ in checks)

        return FilterResult(passed=all_passed, checks=checks)
