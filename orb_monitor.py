#!/usr/bin/env python3
"""
ORB Break Alert - Nasdaq Futures (MNQ)
Monitoreo continuo desde apertura NY hasta 12:00 PM NY
"""

import yfinance as yf
from datetime import datetime, date, time
import pytz
import sys
import json
import os

NY_TZ = pytz.timezone('America/New_York')
BERLIN_TZ = pytz.timezone('Europe/Berlin')

TRADE_FILE = '/tmp/orb_active_trade.json'

def save_trade(señal):
    """Guarda el trade cuando hay breakout"""
    trade = {
        "direccion": señal['señal'],
        "precio_entrada": señal['precio_actual'],
        "sl": señal['sl'],
        "tp": señal['tp'],
        "or_alto": señal['or_alto'],
        "or_bajo": señal['or_bajo'],
        "hora_breakout": señal['hora_actual'],
        "timestamp": datetime.now().isoformat()
    }
    with open(TRADE_FILE, 'w') as f:
        json.dump(trade, f)
    print(f"💾 Trade guardado: {trade['direccion']} @ ${trade['precio_entrada']:,}")

def has_active_trade():
    """Verifica si ya hay un trade activo"""
    return os.path.exists(TRADE_FILE)

# Rango horario de monitoreo (NY time)
MARKET_OPEN = time(9, 30)   # 9:30 AM NY
MARKET_NOON = time(11, 0)   # 11:00 AM NY (fin de monitoreo)

def is_market_hours():
    """Verifica si estamos dentro del horario de monitoreo"""
    now_ny = datetime.now(NY_TZ)
    current_time = now_ny.time()
    
    # Es weekday?
    if now_ny.weekday() >= 5:  # Sábado = 5, Domingo = 6
        return False, "Fin de semana"
    
    # Está dentro del rango?
    if MARKET_OPEN <= current_time <= MARKET_NOON:
        return True, f"Dentro de mercado ({current_time.strftime('%H:%M')} NY)"
    
    if current_time < MARKET_OPEN:
        return False, f"Antes de abrir ({current_time.strftime('%H:%M')} NY)"
    
    return False, f"Después del monitoreo ({current_time.strftime('%H:%M')} NY)"

def get_orb_signal():
    """Analiza ORB y retorna señal"""
    try:
        # MNQ = E-mini Nasdaq 100 Futures (CME)
        mnq = yf.Ticker("MNQ=F")
        
        # Obtener datos históricos de los últimos 2 días en interval 5min
        hist = mnq.history(period="2d", interval="5m")
        
        if hist.empty:
            return None, "Sin datos"
        
        # Los datos ya vienen en NY timezone
        now_ny = datetime.now(NY_TZ)
        today = now_ny.date()
        
        # Filtrar solo hoy
        hoy = hist[hist.index.date == today]
        
        if hoy.empty:
            return None, "Sin datos de hoy - mercado aún no abre"
        
        # Buscar vela de 9:45 AM NY (Opening Range)
        ny_945 = hoy.between_time('09:45', '09:45')
        
        if ny_945.empty:
            # Si no hay vela de 9:45, usar la primera vela de 9:30-9:35
            ny_945 = hoy.between_time('09:30', '09:35')
        
        if ny_945.empty:
            return None, "Mercado aún no abre (9:30 AM NY)"
        
        # Calcular Opening Range
        or_alto = ny_945['High'].iloc[0]
        or_bajo = ny_945['Low'].iloc[0]
        
        # Precio actual (último cierre)
        precio_actual = hoy['Close'].iloc[-1]
        hora_actual = hoy.index[-1].strftime('%H:%M NY')
        
        # Calcular breakout
        rango = or_alto - or_bajo
        
        if precio_actual > or_alto:
            señal = "BREAKOUT_ARRIBA"
            distancia = precio_actual - or_alto
            distancia_pct = (distancia / or_alto) * 100
            status = "🚀 BREAKOUT"
        elif precio_actual < or_bajo:
            señal = "BREAKOUT_ABAJO"
            distancia = or_bajo - precio_actual
            distancia_pct = (distancia / or_bajo) * 100
            status = "📉 BREAKOUT"
        else:
            señal = "DENTRO_RANGO"
            distancia = 0
            distancia_pct = 0
            status = "🔄 Dentro rango"
        
        # Calcular SL y TP (MEJORADO con ATR)
        rango_15 = or_alto - or_bajo
        
        # Obtener ATR para stop más robusto
        try:
            hist_daily = mnq.history(period="5d", interval="1d")
            atr = hist_daily['High'].iloc[-1] - hist_daily['Low'].iloc[-1]
            # Usar 1.5x ATR como stop mínimo
            sl_dist = max(rango_15 * 0.5, atr * 1.5)  # Mayor de: 0.5x rango O 1.5x ATR
        except:
            # Fallback si no hay ATR
            sl_dist = rango_15 * 1.0  # Usar 1x rango como mínimo
        
        tp_dist = sl_dist * 2  # 2:1 R:R siempre
        
        if precio_actual > or_alto:
            sl = precio_actual - sl_dist
            tp = precio_actual + tp_dist
        elif precio_actual < or_bajo:
            sl = precio_actual + sl_dist
            tp = precio_actual - tp_dist
        else:
            sl = None
            tp = None
        
        return {
            "señal": señal,
            "status": status,
            "precio_actual": round(precio_actual, 2),
            "or_alto": round(or_alto, 2),
            "or_bajo": round(or_bajo, 2),
            "rango": round(rango, 2),
            "distancia": round(distancia, 2),
            "distancia_pct": round(distancia_pct, 2),
            "hora_actual": hora_actual,
            "sl": round(sl, 2) if sl else None,
            "tp": round(tp, 2) if tp else None,
            "horario_ok": True
        }, "OK"
        
    except Exception as e:
        return None, str(e)

def main():
    now_berlin = datetime.now(BERLIN_TZ)
    now_ny = datetime.now(NY_TZ)
    
    print(f"🔍 Monitoreo ORB - Nasdaq Futures (MNQ)")
    print(f"⏰ {now_berlin.strftime('%Y-%m-%d %H:%M:%S')} (Berlin)")
    print(f"🕐 {now_ny.strftime('%Y-%m-%d %H:%M:%S')} (NY)")
    print("=" * 55)
    
    # Verificar horario de mercado
    en_mercado, msg = is_market_hours()
    print(f"📡 Estado: {msg}")
    
    if not en_mercado:
        print(f"⏸️  Fuera del horario de monitoreo (9:30-12:00 NY)")
        
        # Guardar estado para debugging
        with open('/tmp/orb_monitor.json', 'w') as f:
            json.dump({"status": "off_hours", "message": msg, "check_time": now_berlin.isoformat()}, f)
        
        # NO mandar notificación fuera de horas
        print("💤 Sin notificación - fuera de horario")
        sys.exit(0)
    
    señal, estado = get_orb_signal()
    
    if señal is None:
        print(f"❌ Error: {estado}")
        with open('/tmp/orb_monitor.json', 'w') as f:
            json.dump({"status": "error", "message": estado}, f)
        sys.exit(1)
    
    # Guardar estado
    with open('/tmp/orb_monitor.json', 'w') as f:
        json.dump(señal, f)
    
    # Si hay breakout y no hay trade activo, guardarlo
    if señal['señal'] in ['BREAKOUT_ARRIBA', 'BREAKOUT_ABAJO'] and not has_active_trade():
        save_trade(señal)
    
    # Mostrar info
    print(f"📊 {señal['status']}")
    print(f"💰 Precio: ${señal['precio_actual']:,}")
    print(f"📐 ORB: ${señal['or_bajo']:,} - ${señal['or_alto']:,} (rango: ${señal['rango']:,})")
    print(f"🕐 Hora NY: {señal['hora_actual']}")
    
    if señal['sl'] and señal['tp']:
        print(f"🎯 SL: ${señal['sl']:,} | TP: ${señal['tp']:,}")
    
    # Siempre mostrar status al final para que cron pueda parsear
    print(f"\n>>> STATUS: {señal['señal']} <<<")

if __name__ == "__main__":
    main()
