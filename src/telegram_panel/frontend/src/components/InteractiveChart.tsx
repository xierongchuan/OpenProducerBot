import { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type Time,
} from 'lightweight-charts';
import type { ChartData } from '../api/types';

interface InteractiveChartProps {
  data: ChartData;
  fullscreen: boolean;
  onToggleFullscreen: () => void;
}

const EMA12_COLOR = '#2196f3';
const SMA26_COLOR = '#ff9800';

const CHART_BG = 'transparent';
const TEXT_COLOR = '#8b8b8b';
const GRID_COLOR = 'rgba(255,255,255,0.04)';

export function InteractiveChart({ data, fullscreen, onToggleFullscreen }: InteractiveChartProps) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.candles.length === 0) return;

    // Cleanup previous chart
    chartRef.current?.remove();
    chartRef.current = null;

    const chartHeight = fullscreen ? 640 : 480;

    // ===== SINGLE CHART =====
    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid as const, color: CHART_BG },
        textColor: TEXT_COLOR,
      },
      grid: {
        vertLines: { color: GRID_COLOR },
        horzLines: { color: GRID_COLOR },
      },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.0, bottom: 0.4 },
      },
      timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
      crosshair: { mode: CrosshairMode.Magnet },
      handleScroll: { vertTouchDrag: false },
      height: chartHeight,
    });
    chartRef.current = chart;

    // ===== PRICE ZONE (top 60%) =====
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderUpColor: '#26a69a',
      borderDownColor: '#ef5350',
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candleSeries.setData(
      data.candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );

    // Volume (overlaps bottom of price zone)
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.48, bottom: 0.4 },
    });
    volumeSeries.setData(
      data.candles.map((c) => ({
        time: c.time as Time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(38,166,154,0.25)' : 'rgba(239,83,80,0.25)',
      }))
    );

    // EMA 12
    const ema12Data = data.indicators.ema12 || [];
    if (ema12Data.length > 0) {
      const ema12Series = chart.addLineSeries({
        color: EMA12_COLOR,
        lineWidth: 1,
        title: 'EMA 12',
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ema12Series.setData(ema12Data.map((p) => ({ time: p.time as Time, value: p.value })));
    }

    // SMA 26
    const sma26Data = data.indicators.sma26 || [];
    if (sma26Data.length > 0) {
      const sma26Series = chart.addLineSeries({
        color: SMA26_COLOR,
        lineWidth: 1,
        title: 'SMA 26',
        priceLineVisible: false,
        lastValueVisible: false,
      });
      sma26Series.setData(sma26Data.map((p) => ({ time: p.time as Time, value: p.value })));
    }

    // Position markers
    if (data.position && data.position.entry_price > 0) {
      const pos = data.position;
      const posColor = pos.side === 'LONG' ? '#00e676' : '#ff1744';

      candleSeries.createPriceLine({
        price: pos.entry_price,
        color: posColor,
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${pos.side} @ ${pos.entry_price}`,
      });
      if (pos.sl > 0) {
        candleSeries.createPriceLine({
          price: pos.sl,
          color: '#ef5350',
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          title: `SL: ${pos.sl}`,
        });
      }
      if (pos.tp > 0) {
        candleSeries.createPriceLine({
          price: pos.tp,
          color: '#26a69a',
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          title: `TP: ${pos.tp}`,
        });
      }
    }

    // ===== RSI ZONE (middle ~18%) =====
    const rsiData = data.indicators.rsi || [];
    if (rsiData.length > 0) {
      const rsiSeries = chart.addLineSeries({
        color: '#2ca02c',
        lineWidth: 1,
        title: 'RSI',
        priceScaleId: 'rsi',
        priceLineVisible: false,
        lastValueVisible: true,
      });
      chart.priceScale('rsi').applyOptions({
        scaleMargins: { top: 0.62, bottom: 0.22 },
        borderVisible: false,
      });
      rsiSeries.setData(rsiData.map((p) => ({ time: p.time as Time, value: p.value })));

      rsiSeries.createPriceLine({
        price: 70,
        color: 'rgba(239,83,80,0.4)',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: false,
        title: '',
      });
      rsiSeries.createPriceLine({
        price: 30,
        color: 'rgba(38,166,154,0.4)',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: false,
        title: '',
      });
    }

    // ===== MACD ZONE (bottom ~18%) =====
    const macdData = data.indicators.macd || [];
    const signalData = data.indicators.macd_signal || [];
    const histData = data.indicators.macd_histogram || [];

    if (macdData.length > 0) {
      // Histogram
      if (histData.length > 0) {
        const histSeries = chart.addHistogramSeries({
          priceScaleId: 'macd',
          priceLineVisible: false,
          lastValueVisible: false,
          title: '',
        });
        histSeries.setData(
          histData.map((p) => ({
            time: p.time as Time,
            value: p.value,
            color: p.value >= 0 ? 'rgba(38,166,154,0.5)' : 'rgba(239,83,80,0.5)',
          }))
        );
      }

      // MACD line
      const macdSeries = chart.addLineSeries({
        color: '#2196f3',
        lineWidth: 1,
        title: 'MACD',
        priceScaleId: 'macd',
        priceLineVisible: false,
        lastValueVisible: true,
      });
      chart.priceScale('macd').applyOptions({
        scaleMargins: { top: 0.82, bottom: 0.02 },
        borderVisible: false,
      });
      macdSeries.setData(macdData.map((p) => ({ time: p.time as Time, value: p.value })));

      // Signal line
      if (signalData.length > 0) {
        const signalSeries = chart.addLineSeries({
          color: '#ff9800',
          lineWidth: 1,
          title: 'Signal',
          priceScaleId: 'macd',
          priceLineVisible: false,
          lastValueVisible: true,
        });
        signalSeries.setData(signalData.map((p) => ({ time: p.time as Time, value: p.value })));
      }

      // Zero line
      if (macdData.length >= 2) {
        const zeroSeries = chart.addLineSeries({
          color: 'rgba(255,255,255,0.1)',
          lineWidth: 1,
          priceScaleId: 'macd',
          priceLineVisible: false,
          lastValueVisible: false,
          title: '',
        });
        zeroSeries.setData([
          { time: macdData[0].time as Time, value: 0 },
          { time: macdData[macdData.length - 1].time as Time, value: 0 },
        ]);
      }
    }

    // ===== FIT =====
    chart.timeScale().fitContent();

    // Resize
    const resizeObserver = new ResizeObserver(() => {
      const w = wrapperRef.current?.clientWidth;
      if (!w) return;
      chart.applyOptions({ width: w });
    });
    if (wrapperRef.current) resizeObserver.observe(wrapperRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data, fullscreen]);

  return (
    <div ref={wrapperRef} className="relative w-full">
      {/* Fullscreen toggle */}
      <button
        onClick={onToggleFullscreen}
        className="absolute top-1 right-1 z-10 bg-black/50 text-white text-[10px] px-2 py-1 rounded hover:bg-black/70 transition-colors"
      >
        {fullscreen ? 'Exit' : 'Fullscreen'}
      </button>

      <div ref={containerRef} />
    </div>
  );
}
