import { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  LineStyle,
  type IChartApi,
  type Time,
} from 'lightweight-charts';
import type { SeriesPoint } from '../api/types';

interface RsiChartProps {
  data: SeriesPoint[];
}

export function RsiChart({ data }: RsiChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#8b8b8b',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.04)' },
        horzLines: { color: 'rgba(255,255,255,0.04)' },
      },
      rightPriceScale: {
        borderVisible: false,
        scaleMargins: { top: 0.05, bottom: 0.05 },
      },
      timeScale: { visible: false },
      handleScroll: false,
      handleScale: false,
    });
    chartRef.current = chart;

    const rsiSeries = chart.addLineSeries({
      color: '#2ca02c',
      lineWidth: 2,
      title: 'RSI',
      priceLineVisible: false,
    });
    rsiSeries.setData(
      data.map((p) => ({ time: p.time as Time, value: p.value }))
    );

    // Overbought / oversold
    rsiSeries.createPriceLine({
      price: 70,
      color: 'rgba(239,83,80,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: '',
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: 'rgba(38,166,154,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: '',
    });

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
        });
      }
    });
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [data]);

  return <div ref={containerRef} className="w-full h-[100px]" />;
}
