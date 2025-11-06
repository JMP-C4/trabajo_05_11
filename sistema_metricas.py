import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class MetricasTesting:
    defects_csv: str
    history_df: pd.DataFrame = None

    def __post_init__(self):
        try:
            self.history_df = pd.read_csv(self.defects_csv, parse_dates=["day"]) if self.defects_csv else pd.DataFrame()
        except Exception:
            self.history_df = pd.DataFrame()

    def calcular_cobertura(self, total_tests: int, executed_tests: int) -> float:
        """Simple coverage percentage: executed / total (0-100)."""
        if total_tests <= 0:
            return 0.0
        return round(100.0 * executed_tests / total_tests, 2)

    def detectar_tendencia(self, window: int = 7) -> pd.Series:
        """Detect trend of daily defects using rolling mean slope.
        Returns a pandas Series indexed by day with the rolling mean of defects.
        """
        if self.history_df is None or self.history_df.empty:
            return pd.Series(dtype=float)
        # Count defects per day
        daily = self.history_df.groupby('day').size().rename('defects').sort_index()
        roll = daily.rolling(window=window, min_periods=1).mean()
        return roll

    def criterios_salida(self, coverage_pct: float, max_open_defects: int, trend_window: int = 7) -> Dict[str, Any]:
        """Return a dict of exit criteria evaluation booleans and reasons.
        Example criteria:
        - coverage_pct >= 80
        - open defects <= max_open_defects
        - trend decreasing (rolling mean last value <= previous)
        """
        res = {"coverage_ok": False, "open_defects_ok": False, "trend_ok": False, "details": {}}
        res['details']['coverage_pct'] = coverage_pct
        res['coverage_ok'] = coverage_pct >= 80.0

        if self.history_df is None or self.history_df.empty:
            res['details']['open_defects'] = 0
            res['open_defects_ok'] = max_open_defects >= 0
            res['details']['trend'] = None
            res['trend_ok'] = False
            return res

        # open defects are those with status != CLOSED if such column exists; otherwise use all defects
        if 'status' in self.history_df.columns:
            open_count = int((self.history_df['status'] != 'CLOSED').sum())
        else:
            open_count = int(len(self.history_df))
        res['details']['open_defects'] = open_count
        res['open_defects_ok'] = open_count <= max_open_defects

        trend_series = self.detectar_tendencia(window=trend_window)
        if not trend_series.empty and len(trend_series) >= 2:
            last = trend_series.iloc[-1]
            prev = trend_series.iloc[-2]
            res['details']['trend_last'] = float(last)
            res['details']['trend_prev'] = float(prev)
            res['trend_ok'] = last <= prev
        else:
            res['details']['trend_last'] = None
            res['details']['trend_prev'] = None
            res['trend_ok'] = False

        return res

    # helper functions
    def defect_summary(self) -> Dict[str, Any]:
        if self.history_df is None or self.history_df.empty:
            return {}
        s = {}
        s['total_defects'] = int(len(self.history_df))
        if 'severity' in self.history_df.columns:
            s['by_severity'] = self.history_df['severity'].value_counts().to_dict()
        return s


# Small utility to generate a defects CSV (used if user wants to regenerate)
def generar_dataset(path: str, n: int = 500, start_date: str = '2025-01-01'):
    import random
    import pandas as pd
    dates = pd.date_range(start=start_date, periods=30).to_pydatetime().tolist()
    rows = []
    for i in range(1, n + 1):
        d = random.choice(dates)
        severity = random.randint(1, 10)
        occurrence = random.randint(1, 10)
        detection = random.randint(1, 10)
        rows.append({
            'id': i,
            'day': d.date().isoformat(),
            'severity': severity,
            'occurrence': occurrence,
            'detection': detection,
            'description': f"Defecto simulado {i}",
            'status': random.choice(['OPEN', 'IN_PROGRESS', 'CLOSED'])
        })
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return df
