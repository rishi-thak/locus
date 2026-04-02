import React, { useEffect, useState } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const GraphView = () => {
  const [data, setData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const response = await fetch('http://localhost:8000/graph');
        const json = await response.json();
        setData(json);
      } catch (err) {
        console.error("failed to fetch graph:", err);
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    
      <ForceGraph2D
        graphData={data}
        nodeLabel="id"
        nodeAutoColorBy="label"
        linkDirectionalArrowLength={3.5}
      />
    
  );
};

export default GraphView;