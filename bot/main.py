import websocket
import json
import requests
import pandas as pd
import time
import logging
import os

# ========== CONFIGURATION ==========
API_TOKEN = "YOUR_API_KEY"      # Replace with your Pocket Option API token
PAIR = "EURUSD"
TRADE_AMOUNT = 1                # USD
TRADE_DURATION = 1              # Minutes
INTERVAL = 60                   # Candle interval in seconds
MAX_CANDLES = 50                # Max candles to store
LOG_FILE = os.path.join("logs", "bot.log")

# ========== SETUP LOGGING ==========
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ========== GLOBAL VARIABLES ==========
candles = []

# ========== HELPER FUNCTIONS ==========
def place_trade(pair, amount, action, duration=1):
    """Place a trade using Pocket Option API."""
    url = "https://api.pocketoption.com/api/v1/trade"
    headers = {"Authorization": f"Bearer {API_TOKEN}"}
    payload = {
        "pair": pair,
        "amount": amount,
        "action": action,
        "duration": duration
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        logging.info(f"Trade Response: {response.json()}")
    except Exception as e:
        logging.error(f"Trade failed: {e}")

def analyze_strategy():
    """Analyze MA crossover and execute trades."""
    global candles
    if len(candles) < 20:
        return

    df = pd.DataFrame(candles)
    df['MA5'] = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()

    if df['MA5'].iloc[-2] < df['MA20'].iloc[-2] and df['MA5'].iloc[-1] > df['MA20'].iloc[-1]:
        logging.info("BUY Signal")
        place_trade(PAIR, TRADE_AMOUNT, "buy", TRADE_DURATION)
    elif df['MA5'].iloc[-2] > df['MA20'].iloc[-2] and df['MA5'].iloc[-1] < df['MA20'].iloc[-1]:
        logging.info("SELL Signal")
        place_trade(PAIR, TRADE_AMOUNT, "sell", TRADE_DURATION)

# ========== WEBSOCKET CALLBACKS ==========
def on_message(ws, message):
    global candles
    try:
        data = json.loads(message)
        if 'candles' in data:
            for candle in data['candles']:
                candles.append({
                    'open': candle['open'],
                    'close': candle['close'],
                    'high': candle['high'],
                    'low': candle['low'],
                    'volume': candle['volume']
                })
            if len(candles) > MAX_CANDLES:
                candles = candles[-MAX_CANDLES:]
            analyze_strategy()
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def on_open(ws):
    subscribe_message = {
        "type": "subscribe",
        "topic": "candles",
        "params": {
            "symbol": PAIR,
            "interval": INTERVAL
        }
    }
    ws.send(json.dumps(subscribe_message))
    logging.info(f"Subscribed to {PAIR} candles.")

def on_error(ws, error):
    logging.error(f"WebSocket error: {error}")

def on_close(ws):
    logging.warning("WebSocket closed, reconnecting in 5 seconds...")
    time.sleep(5)
    start_ws()

# ========== START WEBSOCKET ==========
def start_ws():
    ws = websocket.WebSocketApp(
        "wss://ws.pocketoption.com/api/v1",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

# ========== MAIN ENTRY POINT ==========
if __name__ == "__main__":
    logging.info("Starting Pocket Option Bot...")
    start_ws()
