"""
HiWay RS+ATR Engine - REST API for Dashboard Integration
Provides HTTP endpoints for external systems (MetaTrader, ThinkorSwim, etc.)
"""

from flask import (
    Flask,
    jsonify,
    request,
    render_template
)

from typing import Dict, Any
from datetime import datetime
import pandas as pd
import json
import os

from .hiway_rs_atr_core import RSATREngine, RSATRConfig
from .data_provider import (
    DataAggregator,
    AlpacaDataProvider,
    YahooFinanceDataProvider
)


class RSATRRestAPI:
    """REST API wrapper for RSATR engine"""

    def __init__(self, engine: RSATREngine, data_provider):
        self.engine = engine
        self.data_provider = data_provider

        base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

        self.app = Flask(
            __name__,
            template_folder=os.path.join(base_dir, "templates"),
            static_folder=os.path.join(base_dir, "static")
        )

        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route("/")
        def home():
            return render_template("index.html")

        @self.app.route("/health", methods=["GET"])
        def health():
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat()
            })

        @self.app.route("/docs")
        def docs():
            return jsonify({
                "service": "HiWay RS+ATR Engine",
                "version": "1.0.0",
                "endpoints": {
                    "calculate": "/api/v1/calculate",
                    "snapshot": "/api/v1/snapshot",
                    "config": "/api/v1/config",
                    "health": "/health"
                }
            })

        @self.app.route("/api/v1/calculate", methods=["POST"])
        def calculate():
            try:
                data = request.get_json()

                symbol = data.get("symbol", "AAPL")
                benchmark = data.get("benchmark", "SPY")
                timeframe = data.get("timeframe", "1d")
                bars = data.get("bars", 500)

                stock_df = self.data_provider.get_dataframe(
                    symbol,
                    timeframe,
                    bars
                )

                benchmark_df = self.data_provider.get_dataframe(
                    benchmark,
                    timeframe,
                    bars
                )

                result_df = self.engine.calculate_dataframe(
                    stock_df,
                    benchmark_df
                )

                return jsonify({
                    "symbol": symbol,
                    "benchmark": benchmark,
                    "timeframe": timeframe,
                    "timestamp": datetime.utcnow().isoformat(),
                    "current": {
                        "rs_atr": float(result_df["rs_atr"].iloc[-1]),
                        "regime": int(result_df["regime"].iloc[-1]),
                        "close": float(result_df["close"].iloc[-1])
                    },
                    "data": (
                        result_df[
                            [
                                "open",
                                "high",
                                "low",
                                "close",
                                "rs_atr",
                                "regime"
                            ]
                        ]
                        .tail(50)
                        .to_dict("records")
                    )
                })

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route("/api/v1/snapshot", methods=["GET"])
        def snapshot():
            try:
                symbols = request.args.get(
                    "symbols",
                    "AAPL"
                ).split(",")

                benchmark = request.args.get("benchmark", "SPY")
                timeframe = request.args.get("timeframe", "1d")

                results = []

                benchmark_df = self.data_provider.get_dataframe(
                    benchmark,
                    timeframe,
                    500
                )

                for symbol in symbols:
                    stock_df = self.data_provider.get_dataframe(
                        symbol,
                        timeframe,
                        500
                    )

                    result_df = self.engine.calculate_dataframe(
                        stock_df,
                        benchmark_df
                    )

                    results.append({
                        "symbol": symbol,
                        "rs_atr": float(
                            result_df["rs_atr"].iloc[-1]
                        ),
                        "regime": int(
                            result_df["regime"].iloc[-1]
                        ),
                        "price": float(
                            result_df["close"].iloc[-1]
                        ),
                        "timestamp": datetime.utcnow().isoformat()
                    })

                return jsonify({"snapshots": results})

            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @self.app.route(
            "/api/v1/config",
            methods=["GET", "POST"]
        )
        def config():

            if request.method == "GET":
                return jsonify({
                    "rs_lookback":
                        self.engine.config.rs_lookback,
                    "atr_length":
                        self.engine.config.atr_length,
                    "smoothing_length":
                        self.engine.config.smoothing_length,
                    "use_ema":
                        self.engine.config.use_ema
                })

            data = request.get_json()

            self.engine.config = RSATRConfig(
                rs_lookback=data.get(
                    "rs_lookback",
                    14
                ),
                atr_length=data.get(
                    "atr_length",
                    14
                ),
                smoothing_length=data.get(
                    "smoothing_length",
                    5
                ),
                use_ema=data.get(
                    "use_ema",
                    True
                )
            )

            return jsonify({"status": "updated"})

    def run(
        self,
        host: str = "0.0.0.0",
        port: int = 5000,
        debug: bool = False
    ):
        """Start Flask server"""

        self.app.run(
            host=host,
            port=port,
            debug=debug
        )


def create_api_server(
    config_dict: Dict[str, Any] = None
) -> Flask:
    """Factory function to create configured API server"""

    config = config_dict or {
        "data_provider": "yahoo",
        "rs_lookback": 14,
        "atr_length": 14,
        "smoothing_length": 5,
        "use_ema": True
    }

    engine_config = RSATRConfig(
        rs_lookback=config["rs_lookback"],
        atr_length=config["atr_length"],
        smoothing_length=config["smoothing_length"],
        use_ema=config["use_ema"]
    )

    engine = RSATREngine(engine_config)

    if config["data_provider"] == "yahoo":
        data_provider = YahooFinanceDataProvider()

    elif config["data_provider"] == "alpaca":
        data_provider = AlpacaDataProvider(
            config.get("alpaca_key"),
            config.get("alpaca_secret")
        )

    else:
        data_provider = YahooFinanceDataProvider()

    api = RSATRRestAPI(
        engine,
        data_provider
    )

    return api.app


app = create_api_server()

if __name__ == "__main__":
    port = int(
        os.environ.get("PORT", 5000)
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
