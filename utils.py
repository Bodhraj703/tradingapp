import pandas as pd
import pandas_ta as ta

def calculate_indicators(df):

    # Ensure datetime column exists
    if "Datetime" not in df.columns:
        df["Datetime"] = df.index

    # Fix any missing values
    df = df.copy()

    # ================= RSI ====================
    df["RSI"] = ta.rsi(df["Close"], length=14)

    # ================= EMA ====================
    df["EMA20"] = ta.ema(df["Close"], length=20)
    df["EMA50"] = ta.ema(df["Close"], length=50)

    # ================= MACD ===================
    macd = ta.macd(df["Close"])
    df["MACD"] = macd["MACD_12_26_9"]
    df["MACD_Signal"] = macd["MACDs_12_26_9"]
    df["MACD_Hist"] = macd["MACDh_12_26_9"]

    # ================= VWAP ===================
    df["VWAP"] = ta.vwap(df["High"], df["Low"], df["Close"], df["Volume"])

    # ================= SIGNALS =================
    df["Signal"] = ""

    # ----- RSI Signals -----
    df.loc[df["RSI"] < 30, "Signal"] = "BUY (RSI < 30)"
    df.loc[df["RSI"] > 70, "Signal"] = "SELL (RSI > 70)"

    # ----- EMA Crossover -----
    df["CROSS"] = df["EMA20"] - df["EMA50"]

    df.loc[
        (df["CROSS"] > 0) & (df["CROSS"].shift(1) < 0),
        "Signal"
    ] = "BUY (EMA20 Cross Up)"

    df.loc[
        (df["CROSS"] < 0) & (df["CROSS"].shift(1) > 0),
        "Signal"
    ] = "SELL (EMA20 Cross Down)"

    # ----- MACD Cross -----
    df.loc[
        (df["MACD"] > df["MACD_Signal"]) &
        (df["MACD"].shift(1) < df["MACD_Signal"].shift(1)),
        "Signal"
    ] = "BUY (MACD Bullish)"

    df.loc[
        (df["MACD"] < df["MACD_Signal"]) &
        (df["MACD"].shift(1) > df["MACD_Signal"].shift(1)),
        "Signal"
    ] = "SELL (MACD Bearish)"

    return df


