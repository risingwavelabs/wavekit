import logging
import threading


def run(*fs):
    for f in fs:
        threading.Thread(target=f).start()


def demo_simple():
    from datetime import datetime
    from wavekit import RisingWave
    import time
    import pandas as pd
    import random
    import pytz

    # Init logging
    logging.basicConfig(filename='wavekit.log', level=logging.INFO)



    # if the connection info is not provided, it will try to start RisingWave in your local machine.
    rw = RisingWave()

    rw.execute(
        sql="""
            CREATE TABLE IF NOT EXISTS wavekit_demo_tick (
                symbol     STRING,
                timestamp  TIMESTAMPTZ,
                open       FLOAT,
                high       FLOAT,
                low        FLOAT,
                close      FLOAT,
                volume     FLOAT
            )"""
    )

    def handle_tick(data):
        for _, row in data.iterrows():
            rw.insert("wavekit_demo_tick", **row.to_dict()),

    def subscribe_tick():
        MAX_NUM_ROWS_PER_TICK = 5
        TICK_INTERVAL_MS = 1000
        SYMBOLS = ["ethusdt", "btcusdt", "adausdt", "dogeusdt", "xrpusdt"]

        while True:
            num_rows = random.randint(1, MAX_NUM_ROWS_PER_TICK)
            data = pd.DataFrame({
                "symbol": [random.choice(SYMBOLS) for _ in range(num_rows)],
                "timestamp": [str(datetime.now(pytz.UTC)) for _ in range(num_rows)],  # Use current timestamp with UTC timezone
                "open": [round(random.uniform(100, 500), 2) for _ in range(num_rows)],
                "high": [round(random.uniform(500, 1000), 2) for _ in range(num_rows)],
                "low": [round(random.uniform(50, 100), 2) for _ in range(num_rows)],
                "close": [round(random.uniform(100, 500), 2) for _ in range(num_rows)],
                "volume": [round(random.uniform(1000, 10000), 2) for _ in range(num_rows)],
            })
            handle_tick(data)
            time.sleep(TICK_INTERVAL_MS / 1000)
        

    def subscribe_tick_stream():
        rw.mv(
            name="wavekit_demo_tick_stream",
            stmt="SELECT * FROM wavekit_demo_tick",
        ).on_change(lambda data: print(data))
    
    def subscribe_tick_analytics():
        rw.mv(
            name="wavekit_demo_tick_total_volume_by_symbol",
            stmt="SELECT symbol, sum(volume) FROM wavekit_demo_tick group by symbol",
        ).on_change(lambda data: print(data))

    run(subscribe_tick, subscribe_tick_analytics)


def demo_boll():
    import binance

    from datetime import datetime
    from wavekit import RisingWave

    # if the connection info is not provided, it will try to start RisingWave in your local machine.
    rw = RisingWave()

    rw.execute(
        sql="""
            CREATE TABLE IF NOT EXISTS usdm_futures_klins_1m (
                symbol     STRING,
                timestamp  TIMESTAMPTZ,
                open       FLOAT,
                high       FLOAT,
                low        FLOAT,
                close      FLOAT,
                volume     FLOAT
            )"""
    )

    def handle_binance_klines_update(data):
        k = data["data"]["k"]
        rw.insert(
            table_name="usdm_futures_klins_1m",
            symbol=k["s"],
            timestamp=datetime.fromtimestamp(k["t"] / 1000),
            open=float(k["o"]),
            high=float(k["h"]),
            low=float(k["l"]),
            close=float(k["c"]),
            volume=float(k["v"]),
        )

    def subscribe_binance():
        binance.subscribe_bars(
            streams=["ethusdt@kline_1m", "ethusdt@kline_5m", "ethusdt@kline_15m"],
            handler=handle_binance_klines_update,
        )

    def subscribe_mv():
        rw.mv(
            name="ethusdt_1m",
            stmt="SELECT * FROM usdm_futures_klins_1m",
        ).on_change(lambda data: print(data))

    run(subscribe_binance, subscribe_mv)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python demo.py <demo_name>")
        print("  e.g. python demo.py simple\n")
        print(
            "Available demos:"
            + "\n  simple: a simple demo that subscribes to Binance klines and streams them to the console."
            + "\n  boll: a demo that subscribes to Binance klines and calculates Bollinger Bands."
        )
        sys.exit(1)

    getattr(sys.modules[__name__], f"demo_{sys.argv[1]}")()
