from flask import Flask, render_template, request, jsonify
import requests
import threading
import time

app = Flask(__name__)

# ============== TRADOVATE CLIENT ==============
TRADOVATE_API = "https://api.tradovate.com/v1"

class TradovateClient:
    def __init__(self, api_key=None, access_token=None):
        self.api_key = api_key
        self.access_token = access_token
        self.account_id = None
        
    def authenticate_with_api_key(self, api_key):
        """Autenticar con API Key"""
        try:
            response = requests.post(
                f"{TRADOVATE_API}/authenticate",
                json={"authorizationToken": api_key},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken') or data.get('access_token')
                return True
            return False
        except Exception as e:
            print(f"Auth error: {e}")
            return False
    
    def authenticate_with_token(self, access_token):
        """Usar access token directo"""
        self.access_token = access_token
        return True
    
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_accounts(self):
        response = requests.get(f"{TRADOVATE_API}/account/list", headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}
    
    def get_account_id(self):
        accounts = self.get_accounts()
        items = accounts.get('json', [])
        return items[0].get('id') if items else None
    
    def get_positions(self, account_id):
        if not account_id:
            return []
        response = requests.get(f"{TRADOVATE_API}/position/list?accountId={account_id}", headers=self.get_headers())
        data = response.json()
        return data.get('json', [])
    
    def get_account_info(self, account_id):
        response = requests.get(f"{TRADOVATE_API}/account/{account_id}", headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}
    
    def place_order(self, symbol, quantity, side, account_id, order_type="Market"):
        order = {
            "accountId": account_id,
            "symbol": symbol,
            "quantity": int(quantity),
            "side": side,
            "orderType": order_type,
            "route": "TRADE"
        }
        try:
            response = requests.post(
                f"{TRADOVATE_API}/order/placeOrder",
                headers=self.get_headers(),
                json=order,
                timeout=10
            )
            return response.json() if response.status_code == 200 else None
        except:
            return None


# ============== COPY TRADING ENGINE ==============
class CopyEngine:
    def __init__(self):
        self.master = None
        self.follower = None
        self.master_account = None
        self.follower_account = None
        self.running = False
        self.positions = {}
        self.balance = {}
        self.logs = []
    
    def log(self, msg):
        self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.logs = self.logs[:50]
    
    def start(self, master_type, master_value, follower_type, follower_value, ratio=1.0):
        """Iniciar con API Key o Access Token"""
        try:
            # Master
            self.master = TradovateClient()
            if master_type == "api_key":
                if not self.master.authenticate_with_api_key(master_value):
                    return False, "Error con API Key master"
            else:
                self.master.authenticate_with_token(master_value)
            
            # Follower
            self.follower = TradovateClient()
            if follower_type == "api_key":
                if not self.follower.authenticate_with_api_key(follower_value):
                    return False, "Error con API Key follower"
            else:
                self.follower.authenticate_with_token(follower_value)
            
            # Get accounts
            self.master_account = self.master.get_account_id()
            self.follower_account = self.follower.get_account_id()
            
            if not self.master_account:
                return False, "No se pudo obtener cuenta master"
            if not self.follower_account:
                return False, "No se pudo obtener cuenta follower"
            
            self.running = True
            self.ratio = ratio
            self.log("✅ Copy trading iniciado")
            
            # Start thread
            thread = threading.Thread(target=self._run_loop)
            thread.daemon = True
            thread.start()
            
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    def stop(self):
        self.running = False
        self.log("⏹️ Detenido")
    
    def _run_loop(self):
        while self.running:
            try:
                self._sync()
            except Exception as e:
                self.log(f"Error: {e}")
            time.sleep(10)
    
    def _sync(self):
        if not self.master or not self.follower:
            return
        
        master_positions = self.master.get_positions(self.master_account)
        follower_positions = self.follower.get_positions(self.follower_account)
        
        follower_by_symbol = {p['symbol']: p for p in follower_positions}
        
        for pos in master_positions:
            symbol = pos['symbol']
            qty = int(pos['quantity'] * self.ratio)
            side = pos['side']
            
            follower_pos = follower_by_symbol.get(symbol)
            
            if follower_pos is None:
                self.follower.place_order(symbol, qty, side, self.follower_account)
                self.log(f"📋 Copiado: {side} {qty} {symbol}")
            else:
                follower_qty = follower_pos.get('quantity', 0)
                if follower_qty != qty:
                    diff = qty - follower_qty
                    if diff != 0:
                        self.follower.place_order(symbol, abs(diff), side, self.follower_account)
                        self.log(f"🔄 Ajustado: {side} {abs(diff)} {symbol}")
        
        self.positions = {'master': master_positions, 'follower': follower_positions}
        
        try:
            master_info = self.master.get_account_info(self.master_account)
            follower_info = self.follower.get_account_info(self.follower_account)
            self.balance = {'master': master_info.get('json', {}), 'follower': follower_info.get('json', {})}
        except:
            pass
    
    def status(self):
        return {
            'running': self.running,
            'positions': self.positions,
            'balance': self.balance,
            'logs': self.logs[:20]
        }


# ============== FLASK ROUTES ==============
engine = CopyEngine()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/start', methods=['POST'])
def start():
    data = request.json
    success, msg = engine.start(
        data.get('master_type'),      # "api_key" o "token"
        data.get('master_value'),     # La API key o access token
        data.get('follower_type'),
        data.get('follower_value'),
        float(data.get('ratio', 1.0))
    )
    return jsonify({'success': success, 'message': msg})

@app.route('/api/stop', methods=['POST'])
def stop():
    engine.stop()
    return jsonify({'success': True})

@app.route('/api/status')
def status():
    return jsonify(engine.status())


if __name__ == '__main__':
    print("🌐 Tradovate Copy Trading...")
    print("📍 http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
