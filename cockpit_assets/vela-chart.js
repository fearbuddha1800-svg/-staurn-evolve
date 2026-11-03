/* STAURN Vela Chart — TradingView-grade chart engine powered by LuxAlgo Vela + PineTS.
 * Replaces the Canvas 2D chart with a full Vela chart: candles, Pine Script overlays,
 * live bar updates, native indicators, and responsive scale.
 * Read-only: consumes /api/candles broker rows, never places orders.
 */
'use strict';

window.STURN = window.STURN || {};

STURN.VelaChart = class {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.container = document.getElementById(containerId);
    if (!this.container) throw new Error(`VelaChart: container '#${containerId}' not found`);
    this.symbol = options.symbol || 'XAUUSD';
    this.timeframe = options.timeframe || 'H1';
    this.theme = options.theme || 'dark';
    this.chart = null;
    this.pineEngine = null;
    this.bars = []; // [[t,o,h,l,c,v], ...]
    this.pollTimer = null;
    this.pollInterval = options.pollInterval || 5000;
    this.lastBarTime = null;
    this.indicators = new Map(); // name -> handle
    this._onBarUpdate = options.onBarUpdate || (() => {});
    this._onChartReady = options.onChartReady || (() => {});
    this._ready = false;
  }

  async init() {
    if (typeof window.Vela === 'undefined') {
      throw new Error('VelaChart: window.Vela not loaded — include vela.global.js before vela-chart.js');
    }

    // Build Vela-compatible bar store: [{time, open, high, low, close, volume}, ...]
    const velaBars = this.bars.map(([t, o, h, l, c, v]) => ({
      time: t, open: o, high: h, low: l, close: c, volume: v
    }));

    this.chart = new window.Vela(this.container, {
      symbol: this.symbol,
      timeframe: this.timeframe,
      bars: velaBars,
      theme: this.theme,
      priceStyle: 'candle',
      upColor: '#00f0ff',
      downColor: '#ff3366',
      currentPriceLine: true,
      logScale: false,
      nativeBackend: 'canvas',
      glow: 0,
      animations: { pan: true, zoom: true, scroll: true, autoscale: true, liveBar: true, intro: 'settle' },
      renderer: null, // Vela default NativeRenderer
      priceAxisTicks: 6,
    });

    // Register Pine Script engine if Vela-pinets is loaded
    if (typeof window.VelaPinets !== 'undefined' && window.VelaPinets.PineEngine) {
      this.pineEngine = new window.VelaPinets.PineEngine();
      this.chart.registerEngine('pine', this.pineEngine);
    }

    await this.chart.ready();
    this._ready = true;
    this._onChartReady(this.chart);
    this._startPolling();
    return this.chart;
  }

  /* Replace chart data (full refresh). */
  async setBars(bars) {
    this.bars = bars || [];
    if (!this.chart) return;
    const velaBars = this.bars.map(([t, o, h, l, c, v]) => ({
      time: t, open: o, high: h, low: l, close: c, volume: v
    }));
    try {
      await this.chart.setMarket({
        symbol: this.symbol,
        timeframe: this.timeframe,
        bars: velaBars,
      });
      this.lastBarTime = this.bars.length ? this.bars[this.bars.length - 1][0] : null;
    } catch (e) {
      console.warn('VelaChart: setBars failed', e);
    }
  }

  /* Append a single new bar (live update). */
  updateBar([t, o, h, l, c, v]) {
    if (!this.chart) return;
    if (this.lastBarTime && t === this.lastBarTime) {
      // Update last bar in place — Vela handles via setMarket ideally, but live bar
      // updates go through the chart's live bar path if available.
      return;
    }
    this.bars.push([t, o, h, l, c, v]);
    this.lastBarTime = t;
    this._onBarUpdate([t, o, h, l, c, v]);
  }

  /* Run a Pine Script indicator via Vela-pinets. */
  async addPineIndicator(source, name, options = {}) {
    if (!this.chart) throw new Error('VelaChart: chart not initialized');
    if (!this.pineEngine) {
      throw new Error('VelaChart: PineScript engine not available — load vela-pinets.global.js');
    }
    if (this.indicators.has(name)) {
      this.removeIndicator(name);
    }
    try {
      const result = await this.chart.runIndicator(source, {
        language: 'pine',
        overlay: options.overlay !== false,
        ...options,
      });
      if (result.ok && result.handle) {
        this.indicators.set(name, result.handle);
        return { ok: true, handle: result.handle, context: result.context };
      }
      return { ok: false, error: result.error, context: result.context };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  /* Run a Pine Script and return computed values without adding to chart. */
  async runPine(source, options = {}) {
    if (!this.chart) throw new Error('VelaChart: chart not initialized');
    if (!this.pineEngine) {
      throw new Error('VelaChart: PineScript engine not available');
    }
    try {
      const result = await this.chart.runScript(source, {
        language: 'pine',
        ...options,
      });
      return result;
    } catch (e) {
      return { ok: false, error: e.message };
    }
  }

  removeIndicator(name) {
    const handle = this.indicators.get(name);
    if (handle && typeof handle.remove === 'function') {
      handle.remove();
    }
    this.indicators.delete(name);
  }

  clearIndicators() {
    for (const [name] of this.indicators) this.removeIndicator(name);
    this.indicators.clear();
  }

  listNativeIndicators() {
    return this.chart ? this.chart.availableNativeIndicators() : [];
  }

  addNativeIndicator(type, options = {}) {
    if (!this.chart) throw new Error('VelaChart: chart not initialized');
    return this.chart.addNativeIndicator(type, options);
  }

  destroy() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.clearIndicators();
    if (this.chart && typeof this.chart.destroy === 'function') {
      this.chart.destroy();
    }
    this.chart = null;
    this._ready = false;
  }

  /* Poll /api/candles for new bars. Called internally; can be overridden externally. */
  _startPolling() {
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.pollTimer = setInterval(async () => {
      try {
        const resp = await fetch(`/api/candles?symbol=${encodeURIComponent(this.symbol)}&timeframe=${encodeURIComponent(this.timeframe)}&count=10&closed_only=false`, {
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!resp.ok) return;
        const data = await resp.json();
        const candles = data.candles || [];
        if (!candles.length) return;
        const latest = candles[candles.length - 1];
        if (!this.lastBarTime || latest[0] > this.lastBarTime) {
          this.updateBar(latest);
        }
      } catch (e) {
        // Silent — polling is best-effort
      }
    }, this.pollInterval);
  }
};
