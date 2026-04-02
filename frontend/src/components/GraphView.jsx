import React, { useEffect, useState, useCallback, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { forceCenter, forceCollide } from 'd3-force';

const GraphView = () => {
  const [data, setData] = useState({ nodes: [], links: [] });
  const [dimensions, setDimensions] = useState({ 
    width: window.innerWidth, 
    height: window.innerHeight 
  });
  const [isReady, setIsReady] = useState(false);
  const fgRef = useRef();
  const hasInitialZoom = useRef(false);

  useEffect(() => {
    const handleResize = () => {
      setDimensions({
        width: window.innerWidth,
        height: window.innerHeight
      });
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const response = await fetch('http://localhost:8000/graph');
        if (!response.ok) throw new Error('Network response was not ok');
        const json = await response.json();
        
        setData(prev => {
          if (prev.nodes.length === json.nodes.length && prev.links.length === json.links.length) {
            return prev;
          }
          
          const mergedNodes = json.nodes.map(newNode => {
            const oldNode = prev.nodes.find(n => n.id === newNode.id);
            if (oldNode) {
              return { 
                ...newNode, 
                x: oldNode.x, 
                y: oldNode.y, 
                fx: oldNode.fx, 
                fy: oldNode.fy, 
                vx: oldNode.vx, 
                vy: oldNode.vy,
                isPinned: oldNode.isPinned
              };
            }
            return newNode;
          });
          
          return { nodes: mergedNodes, links: json.links };
        });
      } catch (err) {
        // Silent error
      }
    };

    fetchGraph();
    const interval = setInterval(fetchGraph, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleEngineStop = useCallback(() => {
    if (!hasInitialZoom.current && data.nodes.length > 0 && fgRef.current) {
      fgRef.current.zoomToFit(0, 150);
      hasInitialZoom.current = true;
      // Slight delay for smooth transition after zoom
      setTimeout(() => setIsReady(true), 100);
    }
  }, [data]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    // Replace underscores with spaces and Title Case each word
    const label = (node.id || '')
      .replace(/_/g, ' ')
      .split(' ')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
      
    const fontSize = Math.max(10 / globalScale, 5); 
    ctx.font = `600 ${fontSize}px var(--sans)`;
    
    const textWidth = ctx.measureText(label).width;
    const padding = 6 / globalScale;
    
    const r = Math.max(textWidth / 2 + padding, 12 / globalScale);
    node.__r = r; // Store for hit detection

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.color || 'var(--accent)';
    ctx.fill();

    if (node.isPinned) {
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      ctx.lineWidth = 2 / globalScale;
      ctx.stroke();
    }

    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = '#fff';
    ctx.fillText(label, node.x, node.y);
  }, []);

  const paintPointerArea = useCallback((node, color, ctx) => {
    const r = node.__r || 10;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fill();
  }, []);

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge').strength(-40);
      fgRef.current.d3Force('link').distance(60).strength(2.0);
      fgRef.current.d3Force('collide', forceCollide(15));
      fgRef.current.d3Force('center', forceCenter(dimensions.width / 2, dimensions.height / 2));
      fgRef.current.d3Force('center').strength(0.01); 
    }
  }, [data, dimensions]);

  const loadingTitleStyle = {
    margin: 0,
    fontSize: '64px',
    letterSpacing: '-2px',
    color: 'var(--accent)',
    fontWeight: 400,
    fontFamily: 'var(--heading)'
  };

  const loadingSubtitleStyle = {
    opacity: 0.6,
    fontSize: '20px',
    fontWeight: 400,
    color: 'var(--text)',
    letterSpacing: '3px',
    marginTop: '32px',
    fontFamily: 'var(--sans)'
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: 'var(--bg)', position: 'relative', overflow: 'hidden' }}>
      
      {/* Loading Splash */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
        zIndex: 50,
        opacity: isReady ? 0 : 1,
        transition: 'opacity 1.2s ease-in-out',
        pointerEvents: isReady ? 'none' : 'auto'
      }}>
        <h1 style={loadingTitleStyle}>Locus</h1>
        <div style={loadingSubtitleStyle}>Built by Rishi Thakkar</div>
      </div>

      {/* Main Viewport */}
      <div style={{ 
        width: '100%', 
        height: '100%', 
        opacity: isReady ? 1 : 0, 
        transition: 'opacity 1s ease-in-out',
        position: 'absolute',
        top: 0,
        left: 0
      }}>
        {/* Floating Header */}
        <div 
          style={{ 
            position: 'absolute', 
            top: '30px', 
            left: '30px', 
            zIndex: 10, 
            pointerEvents: 'none',
            fontFamily: 'var(--sans)'
          }}
        >
          <h1 style={{ 
            margin: 0, 
            fontSize: '32px', 
            letterSpacing: '-1px', 
            color: 'var(--accent)', 
            fontWeight: 400,
            fontFamily: 'var(--heading)'
          }}>
            Locus
            <div style={{ 
              opacity: 0.5, 
              fontSize: '12px', 
              fontWeight: 500, 
              color: 'var(--text)', 
              letterSpacing: '1px', 
              marginTop: '4px',
              fontFamily: 'var(--sans)'
            }}>
              Built by Rishi Thakkar
            </div>
          </h1>
        </div>
        
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor="var(--bg)"
          nodeLabel="id"
          nodeAutoColorBy="label"
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          linkColor={() => 'rgba(170, 59, 255, 0.1)'}
          nodeCanvasObject={paintNode}
          nodeCanvasObjectMode={() => 'after'}
          nodePointerAreaPaint={paintPointerArea}
          onEngineStop={handleEngineStop}
          onNodeDragEnd={node => {
            node.fx = node.x;
            node.fy = node.y;
            node.isPinned = true;
          }}
          onNodeClick={node => {
            if (node.isPinned) {
              delete node.fx;
              delete node.fy;
              node.isPinned = false;
            } else {
              node.fx = node.x;
              node.fy = node.y;
              node.isPinned = true;
            }
            
            if (fgRef.current) {
              fgRef.current.centerAt(node.x, node.y, 1000);
              fgRef.current.zoom(2.5, 1000);
            }
          }}
          cooldownTicks={100}
          d3VelocityDecay={0.3}
        />
      </div>
    </div>
  );
};

export default GraphView;