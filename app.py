from flask import Flask, render_template, request,jsonify
import yfinance as yf
from utils import calculate_indicators
from datetime import datetime
import pandas as pd
from flask import Flask, jsonify
from flask import Flask, request, jsonify, render_template,redirect, url_for, flash
from dotenv import load_dotenv
import os
import json
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
from yahoo_client import YahooClient
 






load_dotenv()  # Load .env file



EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


ALERT_FILE = "alerts.json"

app = Flask(__name__)
yahoo = YahooClient()

# Symbols: (symbol_name, is_index)
symbols = {
    # ===== INDIAN STOCKS =====
    "Bharti Airtel": ("BHARTIARTL.NS", False),
    "Reliance Industries": ("RELIANCE.NS", False),
    "TCS": ("TCS.NS", False),
    "HDFC Bank": ("HDFCBANK.NS", False),
    "Infosys": ("INFY.NS", False),
    "ICICI Bank": ("ICICIBANK.NS", False),
    "ITC": ("ITC.NS", False),
    "State Bank of India": ("SBIN.NS", False),
    "Bajaj Finance": ("BAJFINANCE.NS", False),
    "Wipro": ("WIPRO.NS", False),
    "Vodafone Idea": ("IDEA.NS", False),

    # ===== INDIAN INDICES =====
    "Nifty 50": ("^NSEI", True),
    "BankNifty": ("^NSEBANK", True),

    # ===== CRYPTO =====
    "Bitcoin": ("BTC-USD", True),
    "Ethereum": ("ETH-USD", True),
    "Binance Coin": ("BNB-USD", True),
    "Solana": ("SOL-USD", True),
    "Dogecoin": ("DOGE-USD", True),

    # ===== GLOBAL STOCKS =====
    "Apple": ("AAPL", False),
    "Microsoft": ("MSFT", False),
    "Tesla": ("TSLA", False),
    "Amazon": ("AMZN", False),
    "Google": ("GOOGL", False),

    # ===== COMMODITIES =====
    "Gold": ("GC=F", True),
    "Silver": ("SI=F", True),
    "Crude Oil": ("CL=F", True),
}


def fetch_data(symbol, is_index=False):
    df = yahoo.history(symbol, period="5d", interval="5m")

    if df.empty:
        return []

    df = df.reset_index()
    df.rename(columns={"Date": "Datetime"}, inplace=True)

    if not is_index:
        df = df.resample("15min", on="Datetime").agg({
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum"
        }).dropna().reset_index()
    else:
        df["Volume"] = 0

    df = calculate_indicators(df)
    return df.tail(200).to_dict(orient="records")



@app.route("/")
def index():
    page = int(request.args.get("page", 1))
    per_page = 1

    items = list(symbols.items())
    total_pages = len(items)

    start = (page - 1) * per_page
    name, (symbol, is_index) = items[start]

    data = {
        name: fetch_data(symbol, is_index)
    }

    # 🔥 SEARCH ke liye mapping
    company_pages = {
        company.lower(): idx + 1
        for idx, (company, _) in enumerate(items)
    }

    return render_template(
        "index.html",
        data=data,
        page=page,
        total_pages=total_pages,
        company_pages=company_pages,  # ✅ VERY IMPORTANT
        year=datetime.now().year
    )


# =======================================================================================

@app.route('/real-financial-data')
def real_financial_data():
    import yfinance as yf
    page = int(request.args.get("page", 1))
    per_page = 1
    all_companies = list(symbols.keys())
    start = (page - 1) * per_page
    end = start + per_page
    visible_companies = all_companies[start:end]

    final = []
    for i, sym in enumerate(visible_companies):
        symbol, is_index = symbols[sym]
        try:
            t = yf.Ticker(symbol)
            info = t.info

            # Get price data - handle different data types
            current_price = info.get("currentPrice")
            if current_price is None:
                current_price = info.get("regularMarketPrice")
            if current_price is None:
                current_price = info.get("previousClose")
            if current_price is None:
                current_price = info.get("open")

            # Check if this is a commodity/crypto (no financial metrics)
            is_commodity_or_crypto = sym in [
                "Crude Oil", "Silver", "Gold", "Bitcoin", "Ethereum", "Binance Coin", "Solana", "Dogecoin"]

            if is_commodity_or_crypto or is_index:
                # For commodities, crypto, and indices - show limited data
                market_cap = info.get("marketCap")
                if market_cap:
                    market_cap_cr = market_cap / 10000000
                else:
                    market_cap_cr = 0

                final.append({
                    "sno": i + 1,
                    "name": sym,
                    "cmp": current_price if current_price else 0,
                    "pe": "N/A",  # Not applicable
                    "marCap": market_cap_cr if market_cap_cr else 0,
                    "divYld": "N/A",  # Not applicable
                    "npQtr": "N/A",  # Not applicable
                    "profitVar": "N/A",  # Not applicable
                    "salesQtr": "N/A",  # Not applicable
                    "salesVar": "N/A",  # Not applicable
                    "roce": "N/A",  # Not applicable
                })
            else:
                # For regular companies - show all financial metrics
                # Market Cap in Crores
                market_cap = info.get("marketCap")
                if market_cap:
                    market_cap_cr = market_cap / 10000000
                else:
                    market_cap_cr = 0

                # Dividend Yield (convert from decimal to percentage)
                div_yield = info.get("dividendYield", 0)
                if div_yield:
                    div_yield_pct = div_yield * 100
                else:
                    div_yield_pct = 0

                # Profit Margin (convert to percentage)
                profit_margin = info.get("profitMargins", 0)
                if profit_margin:
                    profit_var_pct = profit_margin * 100
                else:
                    profit_var_pct = 0

                # Revenue Growth (convert to percentage)
                revenue_growth = info.get("revenueGrowth", 0)
                if revenue_growth:
                    sales_var_pct = revenue_growth * 100
                else:
                    sales_var_pct = 0

                # ROCE (convert to percentage)
                roce = info.get("returnOnEquity", 0)
                if roce:
                    roce_pct = roce * 100
                else:
                    roce_pct = 0

                final.append({
                    "sno": i + 1,
                    "name": sym,
                    "cmp": current_price if current_price else 0,
                    "pe": info.get("trailingPE", 0),
                    "marCap": market_cap_cr if market_cap_cr else 0,
                    "divYld": div_yield_pct if div_yield_pct else 0,
                    "npQtr": info.get("netIncomeToCommon", 0),
                    "profitVar": profit_var_pct if profit_var_pct else 0,
                    "salesQtr": info.get("totalRevenue", 0),
                    "salesVar": sales_var_pct if sales_var_pct else 0,
                    "roce": roce_pct if roce_pct else 0,
                })

        except Exception as e:
            print(f"Error fetching data for {sym}: {e}")
            # Return empty data with N/A for all fields
            final.append({
                "sno": i + 1,
                "name": sym,
                "cmp": 0,
                "pe": "N/A",
                "marCap": 0,
                "divYld": "N/A",
                "npQtr": "N/A",
                "profitVar": "N/A",
                "salesQtr": "N/A",
                "salesVar": "N/A",
                "roce": "N/A",
            })

    return jsonify(final)

# =========================================real market overview for pie cart =====================================


@app.route('/real-market-overview')
def real_market_overview():
    import yfinance as yf

    # Symbols for the pie chart (example: top stocks)
    symbols_list = {
        "Bharti Airtel": "BHARTIARTL.NS",
        "Reliance Industries": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "Infosys": "INFY.NS",
        "ICICI Bank": "ICICIBANK.NS",
        "ITC": "ITC.NS",
        "State Bank of India": "SBIN.NS",
        "Bajaj Finance": "BAJFINANCE.NS",
        "Wipro": "WIPRO.NS",
        "Vodafone Idea": "IDEA.NS",
    }

    final = []
    for name, symbol in symbols_list.items():
        try:
            t = yf.Ticker(symbol)
            info = t.info
            # Using Market Cap for pie chart distribution
            value = info.get("marketCap", 0) or 0
            final.append({
                "name": name,
                "value": value
            })
        except:
            continue

    return jsonify(final)

# ================================================market overview=================================


@app.route("/market-overview")
def market_overview():
    indices = {
        "NIFTY": "^NSEI",
        "BANKNIFTY": "^NSEBANK",
        "GOLD": "GC=F",
        "BTC": "BTC-USD"
    }

    result = {}

    for name, symbol in indices.items():
        price = yahoo.price(symbol)
        hist = yahoo.history(symbol, period="2d")

        if price and len(hist) >= 2:
            prev = hist["Close"].iloc[-2]
            change = round(((price - prev) / prev) * 100, 2)
        else:
            change = None

        result[name] = {
            "price": round(price, 2) if price else None,
            "change": change
        }

    return jsonify(result)
    indices = {
        "NIFTY 50": "^NSEI",
        "BankNifty": "^NSEBANK",
        "Sensex": "^BSESN",
        "USD/INR": "INR=X",
        "Gold": "GC=F"
    }

    data = {}

    for name, symbol in indices.items():
        try:
            ticker = yf.Ticker(symbol)
            price = ticker.history(period="1d")["Close"].iloc[-1]
            prev = ticker.history(period="2d")["Close"].iloc[0]
            change = round(((price - prev) / prev) * 100, 2)

            data[name] = {
                "price": round(price, 2),
                "change": change
            }
        except:
            data[name] = {"price": None, "change": None}

    return jsonify(data)

# ===========================================compare-stocks========================================================


@app.route("/compare-stocks-page")
def compare_stocks_page():
    return render_template("compareStocks.html")


@app.route("/compare-stocks")
def compare_stocks():
    symbols = {
        "Bharti Airtel": "BHARTIARTL.NS",
        "Reliance Industries": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "Infosys": "INFY.NS",
        "ICICI Bank": "ICICIBANK.NS",
        "ITC": "ITC.NS",
        "State Bank of India": "SBIN.NS",
        "Bajaj Finance": "BAJFINANCE.NS",
        "Wipro": "WIPRO.NS",
        "Vodafone Idea": "IDEA.NS"
    }

    data = []

    for name, symbol in symbols.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            cmp = hist["Close"].iloc[-1]
            pe = ticker.info.get("trailingPE", 0)
            market_cap = ticker.info.get("marketCap", 0) / 1e7  # Rs.Cr.
            div_yield = ticker.info.get(
                "dividendYield", 0) * 100 if ticker.info.get("dividendYield") else 0
            np_qtr = round(cmp * 1000 / 1e7, 2)  # Dummy net profit
            profit_var = round(((cmp - cmp*0.95)/cmp)*100, 2)  # Dummy %
            sales_qtr = round(cmp * 2000 / 1e7, 2)  # Dummy sales
            sales_var = round(((cmp - cmp*0.9)/cmp)*100, 2)  # Dummy %
            roce = round(((cmp*0.15)/cmp)*100, 2)  # Dummy ROCE %

            data.append({
                "name": name,
                "symbol": symbol,
                "cmp": round(cmp, 2),
                "pe": round(pe, 2),
                "marCap": round(market_cap, 2),
                "divYld": round(div_yield, 2),
                "npQtr": np_qtr,
                "profitVar": profit_var,
                "salesQtr": sales_qtr,
                "salesVar": sales_var,
                "roce": roce
            })
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    # Sort by CMP descending (most profitable at top)
    data.sort(key=lambda x: x["cmp"], reverse=True)

    return jsonify({"status": "success", "data": data})

# ==============hot cart page=====================================================


@app.route("/hotchart")
def hot_chart_page():
    return render_template("hotchart.html")


# ================= HOT CHART REAL DATA API =====================

@app.route("/hotchart-data")
def hotchart_data():
    import yfinance as yf

    symbols = [
        "BHARTIARTL.NS", "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS",
        "ICICIBANK.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS", "WIPRO.NS",
        "IDEA.NS"
    ]

    data = []

    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="2d")

            if hist.empty:
                continue

            current = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[0]
            change = current - prev
            change_percent = round((change / prev) * 100, 2)

            volume = hist["Volume"].iloc[-1]

            data.append({
                "symbol": sym.replace(".NS", ""),
                "current_price": round(current, 2),
                "change": round(change, 2),
                "change_percent": change_percent,
                "volume": int(volume)
            })
        except:
            continue

    # split data into categories
    top_gainers = sorted(
        data, key=lambda x: x["change_percent"], reverse=True)[:5]
    top_losers = sorted(data, key=lambda x: x["change_percent"])[:5]
    most_active = sorted(data, key=lambda x: x["volume"], reverse=True)[:5]

    return jsonify({
        "gainers": top_gainers,
        "losers": top_losers,
        "active": most_active
    })


# ==============================for footer show show data =====================

# ================= FOOTER DATA =================

@app.route("/footer-data")
def footer_data():
    footer_symbols = {
        "BTC": "BTC-USD",
        "ETH": "ETH-USD",
        "AAPL": "AAPL",
        "VIX": "^VIX"
    }

    data = {}

    for name, symbol in footer_symbols.items():
        price = yahoo.price(symbol)
        hist = yahoo.history(symbol, period="2d")

        prev = hist["Close"].iloc[-2] if len(hist) >= 2 else price
        change = price - prev if price else None

        data[name] = {
            "price": round(price, 2) if price else None,
            "change": round(change, 2) if change else None,
            "is_positive": change >= 0 if change else None
        }

    return jsonify(data)
# ============================== Email send System =====================


def send_email(symbol, current_price, alert, diff):
    arrow = "⬆️ UP" if diff > 0 else "⬇️ DOWN"
    sign = "+" if diff > 0 else ""

    message = f"""
Stock Alert 🚨

{symbol} price {arrow} 

Target Price : {alert['target_price']}
Current Price: {round(current_price, 2)}
Difference   : {sign}{round(diff, 2)}

Condition    : {alert['condition'].upper()}
"""

    msg = MIMEText(message)
    msg["Subject"] = "📩 Stock Price Alert"
    msg["From"] = EMAIL_USER
    msg["To"] = alert["email"]

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.send_message(msg)
    server.quit()


def load_alerts():
    try:
        with open(ALERT_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_alerts(alerts):
    with open(ALERT_FILE, "w") as f:
        json.dump(alerts, f, indent=4)

# ==================alert route=============================


@app.route("/alert")
def alert_page():
    return render_template("alert.html")


@app.route("/set-alert", methods=["POST"])
def set_alert():
    data = request.json

    user_symbol = data["symbol"].strip()

    final_symbol = None
    for name, (sym, _) in symbols.items():
        if user_symbol.lower() == name.lower() or user_symbol.upper() == sym.replace(".NS", ""):
            final_symbol = sym
            break

    if not final_symbol:
        return jsonify({"message": "❌ Invalid company name or symbol"}), 400

    alert = {
        "symbol": final_symbol,
        "target_price": float(data["target_price"]),
        "condition": data["condition"],
        "email": data["email"]
    }

    alerts = load_alerts()
    alerts.append(alert)
    save_alerts(alerts)

    return jsonify({"message": "✅ Alert saved successfully"})


# ===============alert function check alert=========================


def check_alerts():
    alerts = load_alerts()

    for alert in alerts:
        try:
            price = yf.Ticker(alert["symbol"]).history(
                period="1d")["Close"].iloc[-1]
            price = float(price)

            target = alert["target_price"]
            diff = price - target

            # ⬆️ ABOVE CONDITION
            if alert["condition"] == "above" and price >= target:
                send_email(alert["symbol"], price, alert, diff)

            # ⬇️ BELOW CONDITION
            elif alert["condition"] == "below" and price <= target:
                send_email(alert["symbol"], price, alert, diff)

        except Exception as e:
            print("Alert error:", e)


scheduler = BackgroundScheduler()
scheduler.add_job(check_alerts, "interval", minutes=1)  # now every 1 minute
scheduler.start()


# ===================delete alert button====================

@app.route("/get-alerts")
def get_alerts():
    return jsonify(load_alerts())


@app.route("/delete-alert/<int:index>", methods=["POST"])
def delete_alert(index):
    alerts = load_alerts()
    if index < len(alerts):
        alerts.pop(index)
        save_alerts(alerts)
        return jsonify({"message": "Alert removed"})
    return jsonify({"message": "Invalid index"}), 400


# ========================AboutUs==========================================

@app.route("/about")
def about_page():
    return render_template("about.html")


# =====================contactus===========================================


@app.route("/contact")
def contact_page():
    return render_template("contact.html")


# ================= SEND CONTACT EMAIL =================

@app.route("/send-contact", methods=["POST"])
def send_contact():
    user_name = request.form.get("name")
    user_email = request.form.get("email")
    user_message = request.form.get("message")

    email_body = f"""
📩 New Contact Message Received

👤 Name:
{user_name}

📧 Email:
{user_email}

💬 Message:
{user_message}
"""

    msg = MIMEText(email_body)
    msg["Subject"] = "📬 New Contact Message from Website"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER
    msg["Reply-To"] = user_email

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    server.send_message(msg)
    server.quit()

    return render_template(
        "contact.html",
        message="✅ Your message has been sent successfully"
    )

# ================= SEND CONTACT ===================================


# if __name__ == "__main__":
#      app.run(debug=True)
    # pass

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
