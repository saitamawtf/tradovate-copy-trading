"""Symbol mapping between brokers.

Tradovate uses root + month code (e.g. MNQM5 = MNQ June 2025).
ProjectX uses contractId like 'CON.F.US.MNQ.M25'.

We normalize everything through a ``root_symbol`` (MNQ, ES, NQ, CL, GC, ...).
"""
import re
from dataclasses import dataclass

KNOWN_ROOTS: set[str] = {
    "MNQ", "NQ", "MES", "ES", "MYM", "YM", "M2K", "RTY",
    "CL", "MCL", "GC", "MGC", "SI", "SIL", "NG", "QG",
    "ZB", "ZN", "ZF", "ZT", "6E", "6B", "6J", "6A", "6C",
    "HE", "LE", "ZC", "ZS", "ZW", "BTC", "MBT", "ETH", "MET",
}

_TRADOVATE_RE = re.compile(r"^([A-Z0-9]{2,4})([FGHJKMNQUVXZ])(\d{1,2})$")
_PROJECTX_RE = re.compile(r"^CON\.F\.[A-Z]+\.([A-Z0-9]+)\.([FGHJKMNQUVXZ])(\d{1,2})$")


@dataclass(frozen=True)
class NormalizedSymbol:
    root: str
    month_code: str | None
    year_short: str | None

    def tradovate_native(self, front_month: str | None = None) -> str:
        if front_month:
            return front_month
        if self.month_code and self.year_short:
            return f"{self.root}{self.month_code}{self.year_short[-1]}"
        return self.root

    def projectx_contract_id(self, front_contract_id: str | None = None) -> str | None:
        return front_contract_id


def normalize(symbol: str) -> NormalizedSymbol:
    """Parse a broker-native symbol into a normalized form."""
    sym = symbol.strip().upper()

    m = _PROJECTX_RE.match(sym)
    if m:
        root, month, year = m.group(1), m.group(2), m.group(3)
        return NormalizedSymbol(root=root, month_code=month, year_short=year)

    m = _TRADOVATE_RE.match(sym)
    if m:
        root, month, year = m.group(1), m.group(2), m.group(3)
        return NormalizedSymbol(root=root, month_code=month, year_short=year)

    for root in sorted(KNOWN_ROOTS, key=len, reverse=True):
        if sym.startswith(root):
            return NormalizedSymbol(root=root, month_code=None, year_short=None)

    return NormalizedSymbol(root=sym, month_code=None, year_short=None)


def extract_root(symbol: str) -> str:
    return normalize(symbol).root
