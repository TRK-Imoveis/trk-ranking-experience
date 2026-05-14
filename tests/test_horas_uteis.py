"""Testes unitários para calculate.horas_uteis."""
from __future__ import annotations

import sys
import zoneinfo
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from calculate import horas_uteis

BSB = zoneinfo.ZoneInfo("America/Sao_Paulo")


def t(y: int, m: int, d: int, h: int = 0, mi: int = 0) -> pd.Timestamp:
    """Cria Timestamp tz-aware Brasília."""
    return pd.Timestamp(year=y, month=m, day=d, hour=h, minute=mi, tz=BSB)


def utc(y: int, m: int, d: int, h: int = 0, mi: int = 0) -> pd.Timestamp:
    """Cria Timestamp tz-aware UTC."""
    return pd.Timestamp(year=y, month=m, day=d, hour=h, minute=mi, tz="UTC")


def approx(a: float, b: float, eps: float = 1e-6) -> bool:
    return abs(a - b) < eps


def main() -> None:
    cases = []

    # ----- mesmo dia útil -----
    # Mon 09:00 -> Mon 11:00 = 2h
    cases.append(("mesmo dia 9-11", horas_uteis(t(2026, 5, 11, 9), t(2026, 5, 11, 11)), 2.0))
    # Mon 09:30 -> Mon 09:45 = 0.25h
    cases.append(("15min", horas_uteis(t(2026, 5, 11, 9, 30), t(2026, 5, 11, 9, 45)), 0.25))
    # Mon 07:00 -> Mon 19:00 = todo o dia útil = 10h
    cases.append(("clip antes/depois", horas_uteis(t(2026, 5, 11, 7), t(2026, 5, 11, 19)), 10.0))
    # Mon 19:00 -> Mon 23:00 = 0h (fora do horário)
    cases.append(("totalmente fora", horas_uteis(t(2026, 5, 11, 19), t(2026, 5, 11, 23)), 0.0))

    # ----- multi-dia útil -----
    # Mon 17:00 -> Tue 09:00 = 1h (Mon) + 1h (Tue) = 2h
    cases.append(("mon17 -> tue9", horas_uteis(t(2026, 5, 11, 17), t(2026, 5, 12, 9)), 2.0))
    # Tue 10:00 -> Wed 12:00 = 8h (Tue) + 4h (Wed) = 12h
    cases.append(("tue10 -> wed12", horas_uteis(t(2026, 5, 12, 10), t(2026, 5, 13, 12)), 12.0))

    # ----- fim de semana -----
    # Sat 10:00 -> Sun 12:00 = 0h
    cases.append(("sab -> dom", horas_uteis(t(2026, 5, 16, 10), t(2026, 5, 17, 12)), 0.0))
    # Fri 17:00 -> Mon 09:00 = 1h (Fri) + 1h (Mon) = 2h
    cases.append(("fri17 -> mon9", horas_uteis(t(2026, 5, 15, 17), t(2026, 5, 18, 9)), 2.0))
    # Sat 10:00 -> Mon 09:00 = 1h (Mon 8-9)
    cases.append(("sab -> mon9", horas_uteis(t(2026, 5, 16, 10), t(2026, 5, 18, 9)), 1.0))

    # ----- caso negativo / edge -----
    # fim < inicio → 0
    cases.append(("negativo", horas_uteis(t(2026, 5, 11, 11), t(2026, 5, 11, 9)), 0.0))
    # fim == inicio → 0
    cases.append(("zero", horas_uteis(t(2026, 5, 11, 11), t(2026, 5, 11, 11)), 0.0))
    # NaT → NaN
    out_nan = horas_uteis(pd.NaT, t(2026, 5, 11, 11))
    cases.append(("NaT", float("nan") if pd.isna(out_nan) else out_nan, float("nan")))

    # ----- timezone -----
    # 21:00 UTC = 18:00 BSB → no fim do dia útil; Mon 21:00 UTC (Mon 18:00 BSB) ate Mon 22:00 UTC = 0h
    cases.append(("tz UTC fim", horas_uteis(utc(2026, 5, 11, 21), utc(2026, 5, 11, 22)), 0.0))
    # Mon 11:00 UTC (08:00 BSB) → Mon 21:00 UTC (18:00 BSB) = 10h
    cases.append(("tz UTC dia inteiro", horas_uteis(utc(2026, 5, 11, 11), utc(2026, 5, 11, 21)), 10.0))

    # ----- 1 semana útil completa -----
    # Mon 08:00 -> Mon (próximo) 08:00 = 5 dias úteis × 10h = 50h
    cases.append(("semana inteira", horas_uteis(t(2026, 5, 11, 8), t(2026, 5, 18, 8)), 50.0))

    fail = 0
    for name, got, expected in cases:
        ok = (pd.isna(got) and pd.isna(expected)) or approx(got, expected)
        marker = "OK" if ok else "FAIL"
        print(f"  [{marker}] {name:30}  got={got!r:15}  expected={expected!r}")
        if not ok:
            fail += 1
    print(f"\n{len(cases) - fail}/{len(cases)} passaram")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
