from flask import Flask, render_template, request, jsonify
import requests
import threading
import time

app = Flask(__name__)

# ============== TRADOVATE CLIENT ==============
class TradovateClient:
    def __init__(self, name, password, cid=0, sec=None):
        self.name = name
        self.password = password
        self.cid = cid
        self.sec = sec
        self.access_token = None
        self.account_id = None
    
    def authenticate(self):
        """Auth con credenciales + API secret"""
        url = "https://live.tradovateapi.com/v1/auth/accesstokenrequest"
        
        payload = {
            "name": self.name,
            "password": self.password,
            "appId": "TradovateCopyTrading",
            "appVersion": "1.0",
            "cid": self.cid,
            "sec": self.sec or ""
        }
        
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('accessToken')
                return True
            else:
                print(f"Auth error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Auth exception: {e}")
            return False
    
    def authenticate_with_token(self, access_token):
        """Usar access token existente"""
        self.access_token = access_token
        return True
    
    def get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    def get_accounts(self):
        url = "https://live.tradovateapi.com/v1/account/list"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}
    
    def get_account_id(self):
        accounts = self.get_accounts()
        items = accounts.get('json', [])
        return items[0].get('id') if items else None
    
    def get_positions(self, account_id):
        if not account_id:
            return []
        url = f"https://live.tradovateapi.com/v1/position/list?accountId={account_id}"
        response = requests.get(url, headers=self.get_headers())
        data = response.json()
        return data.get('json', [])
    
    def get_account_info(self, account_id):
        url = f"https://live.tradovateapi.com/v1/account/{account_id}"
        response = requests.get(url, headers=self.get_headers())
        return response.json() if response.status_code == 200 else {}
    
    def place_order(self, symbol, quantity, side, account_id, order_type="Market"):
        url = "https://live.tradovateapi.com/v1/order/placeorder"
        
        order = {
            "accountId": account_id,
            "accountSpec": self.name,
            "symbol": symbol,
            "quantity": int(quantity),
            "side": side,
            "orderType": order_type,
            "isAutomated": True
        }
        
        try:
            response = requests.post(url, headers=self.get_headers(), json=order, timeout=10)
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
        self.ratio = 1.0
    
    def log(self, msg):
        self.logs.insert(0, f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.logs = self.logs[:50]
    
    def start(self, master_name, master_password, master_cid, master_sec, 
              follower_name, follower_password, follower_cid, follower_sec, ratio=1.0):
        try:
            # Master
            self.master = TradovateClient(master_name, master_password, master_cid, master_sec)
            if not self.master.authenticate():
                return False, "Error autenticando cuenta master"
            
            # Follower
            self.follower = TradovateClient(follower_name, follower_password, follower_cid, follower_sec)
            if not self.follower.authenticate():
                return False, "Error autenticando cuenta follower"
            
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
                result = self.follower.place_order(symbol, qty, side, self.follower_account)
                if result:
                    self.log(f"📋 Copiado: {side} {qty} {symbol}")
            else:
                follower_qty = follower_pos.get('quantity', 0)
                if follower_qty != qty:
                    diff = qty - follower_qty
                    if diff != 0:
                        result = self.follower.place_order(symbol, abs(diff), side, self.follower_account)
                        if result:
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
        data.get('master_name'),
        data.get('master_password'),
        int(data.get('master_cid', 0)),
        data.get('master_sec'),
        data.get('follower_name'),
        data.get('follower_password'),
        int(data.get('follower_cid', 0)),
        data.get('follower_sec'),
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
