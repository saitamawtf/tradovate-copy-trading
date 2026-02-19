# Tradovate Copy Trading

Web app para copy trading entre cuentas Tradovate.

## Archivos

| Archivo | Descripción |
|---------|-------------|
| `app.py` | Servidor Flask con la app web |
| `templates/index.html` | Interfaz de usuario |
| `orb_monitor.py` | Monitor ORB para Nasdaq Futures (MNQ) |
| `ilm_strategy.pine` | Estrategia ILM para TradingView |
| `orb_strategy.pine` | Estrategia ORB para TradingView |

## Cómo usar

### 1. Copy Trading (Web)

```bash
pip install flask requests
python app.py
```

Abre http://localhost:5000

### 2. Monitor ORB

```bash
python orb_monitor.py
```

## Estrategias TradingView

### ILM Strategy
- Detecta liquidity sweeps
- Fair Value Gap (FVG)
- Swing high/low configurable

### ORB Strategy (MEJORADO)
- Opening Range Breakout 9:30-9:45 NY
- Stop Loss: max(0.5x rango, 1.5x ATR)
- Take Profit: 2:1 R:R

## API Tradovate

```
Base URL: https://live.tradovateapi.com/v1

Auth:
POST /auth/accesstokenrequest
{
  "name": "email",
  "password": "password",
  "appId": "TuApp",
  "appVersion": "1.0"
}
```

## Requisitos

- Cuenta Tradovate con API Access
- $1000+ equity o $30/mes
