# Copy Trading (Tradovate + ProjectX)

Cloud-style copy trader para cuentas fondeadas, inspirado en [Tradesyncer](https://tradesyncer.com/). Replica operaciones desde una cuenta líder a N cuentas seguidoras distribuidas entre brokers que corren sobre Tradovate y ProjectX (Topstep, TickTickTrader, TakeProfitTrader, etc.).

## Estado v1

- 1 leader → N followers (escalado por `ratio`, `fixed`, `equity_scaled`).
- Event-driven: WebSocket Tradovate + SignalR User Hub ProjectX.
- Reverse copy por follower.
- Persistencia SQLite, credenciales cifradas con Fernet.
- API REST + WebSocket de eventos para el frontend.
- Frontend React (Vite + Tailwind + TanStack Query).
- Arquitectura preparada para multi-tenant (user_id en schema; login se añadirá después).

Fuera de alcance v1: daily-loss lockout, trade journal con gráficos, órdenes pendientes/stop, NinjaTrader/Rithmic/TradingView.

## Estructura

```
backend/                 FastAPI app
  main.py                entrypoint + lifespan
  brokers/               adapters + base ABC
    tradovate.py         REST + WS (wss://.../v1/websocket)
    projectx.py          REST + SignalR (/hubs/user)
    symbols.py           MNQ↔CON.F.US.MNQ.M25
  copy/
    engine.py            CopyEngine async (una task por grupo)
    sizing.py            ratio/fixed/equity_scaled
  api/
    accounts.py          CRUD cuentas broker
    groups.py            CRUD + start/stop grupos
    ws.py                WS app-side para push al frontend
frontend/                Vite + React + Tailwind
tests/                   pytest
orb_monitor.py           (legacy) monitor ORB MNQ — se mantiene
*.pine                   (legacy) estrategias TradingView — se mantienen
```

## Instalación

```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

Genera una clave Fernet y ponla en `.env`:

```bash
python -c "from backend.security import generate_key; print(generate_key())"
echo "FERNET_KEY=<pega_la_clave_aqui>" > .env
```

## Desarrollo

```bash
# Terminal 1: backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend && npm run dev
```

Frontend en http://localhost:5173 (proxy a FastAPI en 8000).

## Tests

```bash
pytest
```

## APIs utilizadas

- [Tradovate](https://api.tradovate.com/) — REST + WS, `user/syncrequest`.
- [ProjectX Gateway](https://gateway.docs.projectx.com/) — REST + SignalR User Hub (`GatewayUserPosition`, `GatewayUserTrade`).

## Flujo end-to-end

1. `POST /api/accounts` para dar de alta credenciales Tradovate y/o ProjectX.
2. `POST /api/accounts/{id}/test` valida auth y guarda el `external_account_id`.
3. `POST /api/groups` crea un grupo con un leader + N followers, cada uno con `size_mode`/`size_value`/`reverse`.
4. `POST /api/groups/{id}/start` lanza una task async que suscribe al stream del leader y replica eventos a todos los followers.
5. El frontend recibe eventos en vivo por `/ws`.

## Seguridad

- Credenciales cifradas con Fernet (clave en `.env`, nunca commiteada).
- CORS restringido a `localhost:5173` en dev.
- Tokens nunca se loggean.
