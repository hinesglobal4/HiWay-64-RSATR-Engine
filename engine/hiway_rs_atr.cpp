"""
HiWay RS+ATR Engine - C++ Implementation
High-performance calculation engine for institutional deployment
Compile: g++ -O3 -std=c++17 hiway_rs_atr.cpp -o hiway_rs_atr
"""

#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <stdexcept>

struct BarData {
    double open;
    double high;
    double low;
    double close;
    long volume;
};

struct RSATRConfig {
    int rs_lookback = 14;
    int atr_length = 14;
    int smoothing_length = 5;
    bool use_ema = true;
};

class RSATREngine {
private:
    RSATRConfig config;
    
public:
    RSATREngine(const RSATRConfig& cfg = RSATRConfig()) : config(cfg) {}
    
    // Calculate True Range
    static std::vector<double> calculateTR(
        const std::vector<double>& high,
        const std::vector<double>& low,
        const std::vector<double>& close) {
        
        std::vector<double> tr(high.size(), 0.0);
        
        for (size_t i = 1; i < high.size(); ++i) {
            double tr1 = high[i] - low[i];
            double tr2 = std::abs(high[i] - close[i-1]);
            double tr3 = std::abs(low[i] - close[i-1]);
            tr[i] = std::max({tr1, tr2, tr3});
        }
        
        return tr;
    }
    
    // Calculate ATR using Wilder's Smoothing
    std::vector<double> calculateATR(
        const std::vector<double>& high,
        const std::vector<double>& low,
        const std::vector<double>& close) {
        
        std::vector<double> tr = calculateTR(high, low, close);
        std::vector<double> atr(tr.size(), 0.0);
        
        if (config.atr_length >= tr.size()) {
            return atr;
        }
        
        // Initial ATR
        double sum = 0.0;
        for (int i = 1; i <= config.atr_length; ++i) {
            sum += tr[i];
        }
        atr[config.atr_length] = sum / config.atr_length;
        
        // Wilder's smoothing
        for (size_t i = config.atr_length + 1; i < tr.size(); ++i) {
            atr[i] = (atr[i-1] * (config.atr_length - 1) + tr[i]) / config.atr_length;
        }
        
        return atr;
    }
    
    // Calculate returns
    static std::vector<double> calculateReturns(
        const std::vector<double>& prices,
        int lookback) {
        
        std::vector<double> returns(prices.size(), 0.0);
        
        for (size_t i = lookback; i < prices.size(); ++i) {
            if (prices[i-lookback] != 0.0) {
                returns[i] = (prices[i] / prices[i-lookback]) - 1.0;
            }
        }
        
        return returns;
    }
    
    // Calculate Relative Strength
    static std::vector<double> calculateRS(
        const std::vector<double>& stock_returns,
        const std::vector<double>& benchmark_returns) {
        
        std::vector<double> rs(stock_returns.size());
        
        for (size_t i = 0; i < stock_returns.size(); ++i) {
            rs[i] = stock_returns[i] - benchmark_returns[i];
        }
        
        return rs;
    }
    
    // Calculate EMA
    static std::vector<double> calculateEMA(
        const std::vector<double>& series,
        int period) {
        
        std::vector<double> ema(series.size(), 0.0);
        
        if (period >= series.size()) {
            return ema;
        }
        
        double multiplier = 2.0 / (period + 1);
        
        // Initial EMA
        double sum = 0.0;
        for (int i = 0; i < period; ++i) {
            sum += series[i];
        }
        ema[period - 1] = sum / period;
        
        // Calculate remaining values
        for (size_t i = period; i < series.size(); ++i) {
            ema[i] = series[i] * multiplier + ema[i-1] * (1.0 - multiplier);
        }
        
        return ema;
    }
    
    // Calculate SMA
    static std::vector<double> calculateSMA(
        const std::vector<double>& series,
        int period) {
        
        std::vector<double> sma(series.size(), 0.0);
        
        if (period >= series.size()) {
            return sma;
        }
        
        double sum = 0.0;
        for (int i = 0; i < period; ++i) {
            sum += series[i];
        }
        sma[period - 1] = sum / period;
        
        for (size_t i = period; i < series.size(); ++i) {
            sum = sum - series[i - period] + series[i];
            sma[i] = sum / period;
        }
        
        return sma;
    }
    
    // Main calculation
    std::vector<double> calculate(
        const std::vector<double>& stock_high,
        const std::vector<double>& stock_low,
        const std::vector<double>& stock_close,
        const std::vector<double>& benchmark_close) {
        
        if (stock_high.size() != stock_low.size() ||
            stock_low.size() != stock_close.size() ||
            stock_close.size() != benchmark_close.size()) {
            throw std::invalid_argument("Input arrays must have equal length");
        }
        
        // Calculate returns
        auto stock_returns = calculateReturns(stock_close, config.rs_lookback);
        auto bench_returns = calculateReturns(benchmark_close, config.rs_lookback);
        
        // Calculate RS
        auto rs = calculateRS(stock_returns, bench_returns);
        
        // Calculate ATR
        auto atr = calculateATR(stock_high, stock_low, stock_close);
        
        // Normalize RS by ATR
        std::vector<double> rs_atr(rs.size());
        for (size_t i = 0; i < rs.size(); ++i) {
            rs_atr[i] = (atr[i] != 0.0) ? rs[i] / atr[i] : 0.0;
        }
        
        // Apply smoothing
        std::vector<double> result;
        if (config.use_ema) {
            result = calculateEMA(rs_atr, config.smoothing_length);
        } else {
            result = calculateSMA(rs_atr, config.smoothing_length);
        }
        
        return result;
    }
    
    // Get current signal
    int getSignal(double rs_atr_value) {
        return rs_atr_value >= 0.0 ? 1 : -1;
    }
    
    // Update configuration
    void setConfig(const RSATRConfig& cfg) {
        config = cfg;
    }
    
    RSATRConfig getConfig() const {
        return config;
    }
};

// Example usage
int main() {
    // Sample data
    std::vector<double> stock_high = {100.5, 101.2, 100.8, 102.1, 103.5};
    std::vector<double> stock_low = {99.8, 100.5, 100.2, 101.3, 102.8};
    std::vector<double> stock_close = {100.0, 101.0, 100.5, 102.0, 103.2};
    std::vector<double> benchmark_close = {300.0, 301.0, 300.5, 302.0, 303.0};
    
    RSATRConfig config;
    RSATREngine engine(config);
    
    auto result = engine.calculate(stock_high, stock_low, stock_close, benchmark_close);
    
    // Print results
    for (size_t i = 0; i < result.size(); ++i) {
        int signal = engine.getSignal(result[i]);
        printf("Bar %zu: RS+ATR = %.6f, Signal = %d\n", i, result[i], signal);
    }
    
    return 0;
}
