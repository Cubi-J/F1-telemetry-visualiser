import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';

interface PlotlyGraphProps {
  data: Plotly.Data[];
  layout: Partial<Plotly.Layout>;
}

export const PlotlyGraph: React.FC<PlotlyGraphProps> = ({ data, layout }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    Plotly.newPlot(containerRef.current, data, layout, { responsive: true });

    return () => {
      if (containerRef.current) {
        Plotly.purge(containerRef.current);
      }
    };
  }, [data, layout]);

  return <div ref={containerRef} style={{ width: '100%', height: '700px' }} />;
};