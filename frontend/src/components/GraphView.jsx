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
  const [searchQuery, setSearchQuery] = useState('');
  const [isDarkMode, setIsDarkMode] = useState(true);
  
  const fgRef = useRef();
  const hasInitialZoom = useRef(false);

  const BASE_RADIUS = 22; 
  const CURATED_COLORS = [
    '#6366f1', '#8b5cf6', '#ec4899', '#f43f5e', '#f59e0b', '#10b981', '#06b6d4', '#3b82f6',
  ];

  const getContrastColor = (hex) => {
    if (!hex) return '#ffffff';
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const brightness = (r * 299 + g * 587 + b * 114) / 1000;
    return brightness >= 180 ? '#1e1b4b' : '#ffffff';
  };

  const normalize = (str) => (str || '').toLowerCase().replace(/_/g, ' ').trim();

  useEffect(() => {
    const handleResize = () => setDimensions({ width: window.innerWidth, height: window.innerHeight });
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const response = await fetch('http://localhost:8000/graph');
        const json = await response.json();
        
        setData(prev => {
          const isFirstLoad = prev.nodes.length === 0 && json.nodes.length > 0;
          if (prev.nodes.length === json.nodes.length && prev.links.length === json.links.length) return prev;
          
          const mergedNodes = json.nodes.map(newNode => {
            const oldNode = prev.nodes.find(n => n.id === newNode.id);
            const color = CURATED_COLORS[Math.abs(newNode.id.split('').reduce((a, b) => ((a << 5) - a) + b.charCodeAt(0), 0)) % CURATED_COLORS.length];
            if (oldNode) return { ...newNode, color, x: oldNode.x, y: oldNode.y, fx: oldNode.fx, fy: oldNode.fy, isPinned: oldNode.isPinned };
            return { ...newNode, color }; // Reverting to (0,0) default
          });

          if (isFirstLoad) {
            // Revert reveal logic to be slightly more patient to avoid "dot" zoom
            setTimeout(() => {
                if (fgRef.current) {
                    fgRef.current.zoomToFit(600, 100);
                    setTimeout(() => setIsReady(true), 300);
                }
            }, 600); // Wait longer for nodes to spread before zooming
          }
          
          return { nodes: mergedNodes, links: json.links };
        });
      } catch (err) {}
    };
    fetchGraph();
    const interval = setInterval(fetchGraph, 5000);
    return () => clearInterval(interval);
  }, []);

  const wrapText = (text, maxWidth, ctx) => {
    const words = text.split(' ');
    const lines = [];
    let currentLine = words[0];
    for (let i = 1; i < words.length; i++) {
        const width = ctx.measureText(currentLine + " " + words[i]).width;
        if (width < maxWidth) currentLine += " " + words[i];
        else { lines.push(currentLine); currentLine = words[i]; }
    }
    lines.push(currentLine);
    return lines;
  };

  const paintNode = useCallback((node, ctx, globalScale) => {
    const rawLabel = (node.id || '').replace(/_/g, ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join(' ');
    const r = BASE_RADIUS;
    node.__r = r; 

    const isMatched = searchQuery && normalize(node.id).includes(normalize(searchQuery));
    
    if (isMatched) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 5, 0, 2 * Math.PI, false);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
        ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fillStyle = node.color;
    if (searchQuery && !isMatched) ctx.globalAlpha = 0.25;
    ctx.fill();
    ctx.globalAlpha = 1.0;

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 1;
    ctx.stroke();

    if (node.isPinned || isMatched) {
      ctx.strokeStyle = isMatched ? '#fff' : 'rgba(255, 255, 255, 0.5)';
      ctx.lineWidth = isMatched ? 3 : 1.5;
      ctx.stroke();
    }

    let baseFontSize = 8;
    if (rawLabel.length > 15) baseFontSize = 7;
    if (rawLabel.length > 25) baseFontSize = 6;
    const fontSize = baseFontSize; 
    ctx.font = `600 ${fontSize}px var(--sans)`;
    ctx.fillStyle = getContrastColor(node.color);
    if (searchQuery && !isMatched) ctx.globalAlpha = 0.5;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    const wrapBound = (r * 2) * 0.85;
    const lines = wrapText(rawLabel, wrapBound, ctx);
    const lineHeight = fontSize * 1.1;
    const totalHeight = lines.length * lineHeight;
    const startY = node.y - (totalHeight / 2) + (lineHeight / 2);
    lines.forEach((line, index) => ctx.fillText(line, node.x, startY + (index * lineHeight)));
    ctx.globalAlpha = 1.0;
  }, [searchQuery]);

  const paintPointerArea = useCallback((node, color, ctx) => {
    const r = node.__r || BASE_RADIUS;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
    ctx.fill();
  }, []);

  useEffect(() => {
    if (fgRef.current) {
      // Powerful repulsion
      fgRef.current.d3Force('charge').strength(-400);
      fgRef.current.d3Force('link').distance(150).strength(0.5);
      fgRef.current.d3Force('collide', forceCollide(BASE_RADIUS + 8).iterations(3));
      
      // Keep everything centered at the local (0,0) coordinate
      fgRef.current.d3Force('center', forceCenter(0, 0));
      fgRef.current.d3Force('center').strength(0.005); 
    }
  }, [data, dimensions]);

  const handleZoomIn = () => fgRef.current?.zoom(fgRef.current.zoom() * 1.5, 400);
  const handleZoomOut = () => fgRef.current?.zoom(fgRef.current.zoom() * 0.7, 400);
  const handleRecenter = () => fgRef.current?.zoomToFit(800, 150);
  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    document.body.style.backgroundColor = isDarkMode ? '#f8fafc' : '#16171d';
    document.body.style.color = isDarkMode ? '#1e293b' : '#f3f4f6';
  };

  const toolbarButtonStyle = {
    background: isDarkMode ? '#1f2028' : '#fff',
    border: isDarkMode ? '1px solid #2e303a' : '1px solid #e2e8f0',
    color: isDarkMode ? '#f3f4f6' : '#1e1b4b',
    padding: '10px 14px',
    borderRadius: '4px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'var(--sans)',
    transition: 'all 0.1s ease',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    boxShadow: '2px 2px 0px rgba(0,0,0,0.1)'
  };

  return (
    <div style={{ width: '100vw', height: '100vh', background: isDarkMode ? '#16171d' : '#f8fafc', position: 'relative', overflow: 'hidden', transition: 'background 0.5s ease' }}>
      
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
        zIndex: 50,
        opacity: isReady ? 0 : 1,
        transition: 'opacity 0.6s ease-out',
        pointerEvents: isReady ? 'none' : 'auto'
      }}>
        <h1 style={{ margin: 0, fontSize: '64px', letterSpacing: '-2px', color: 'var(--accent)', fontWeight: 400, fontFamily: 'var(--heading)' }}>Locus</h1>
        <div style={{ opacity: 0.6, fontSize: '20px', fontWeight: 400, color: isDarkMode ? '#9ca3af' : '#64748b', letterSpacing: '3px', marginTop: '32px', fontFamily: 'var(--sans)' }}>Built by Rishi Thakkar</div>
      </div>

      <div style={{ 
        width: '100%', 
        height: '100%', 
        opacity: isReady ? 1 : 0, 
        transition: 'opacity 0.8s ease-in',
        position: 'absolute',
        top: 0,
        left: 0
      }}>
        <div style={{ position: 'absolute', top: '30px', left: '30px', zIndex: 10, pointerEvents: 'none', fontFamily: 'var(--sans)' }}>
          <h1 style={{ margin: 0, fontSize: '32px', letterSpacing: '-1px', color: 'var(--accent)', fontWeight: 400, fontFamily: 'var(--heading)' }}>
            Locus
            <div style={{ opacity: 0.5, fontSize: '12px', fontWeight: 500, color: isDarkMode ? '#9ca3af' : '#64748b', letterSpacing: '1px', marginTop: '4px', fontFamily: 'var(--sans)' }}>Built by Rishi Thakkar</div>
          </h1>
        </div>
        <div style={{ position: 'absolute', bottom: '40px', left: '50%', transform: 'translateX(-50%)', zIndex: 100, display: 'flex', alignItems: 'center', gap: '8px', background: isDarkMode ? '#16171d' : '#f1f5f9', padding: '8px', border: isDarkMode ? '1px solid #2e303a' : '1px solid #cbd5e1', boxShadow: '4px 4px 0px rgba(0,0,0,0.2)' }}>
          <input type="text" placeholder="SEARCH..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} style={{ background: isDarkMode ? '#1f2028' : '#fff', border: isDarkMode ? '1px solid #2e303a' : '1px solid #cbd5e1', padding: '10px 16px', color: isDarkMode ? '#fff' : '#1e1b4b', fontFamily: 'var(--sans)', fontSize: '12px', fontWeight: 600, letterSpacing: '1px', outline: 'none', width: '180px', transition: 'width 0.2s ease' }} onFocus={(e) => e.target.style.width = '240px'} onBlur={(e) => e.target.style.width = '180px'} />
          <div style={{ width: '1px', height: '18px', background: isDarkMode ? '#2e303a' : '#cbd5e1', margin: '0 4px' }} />
          <button onClick={handleZoomIn} style={toolbarButtonStyle}>＋</button>
          <button onClick={handleZoomOut} style={toolbarButtonStyle}>－</button>
          <button onClick={handleRecenter} style={toolbarButtonStyle}>回</button>
          <div style={{ width: '1px', height: '18px', background: isDarkMode ? '#2e303a' : '#cbd5e1', margin: '0 4px' }} />
          <button onClick={toggleTheme} style={toolbarButtonStyle}>{isDarkMode ? '☼' : '☾'}</button>
        </div>
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          width={dimensions.width}
          height={dimensions.height}
          centerAt={[0, 0]} // Keep camera centered on coordinate origin
          backgroundColor={isDarkMode ? '#16171d' : '#f8fafc'}
          nodeLabel="id"
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkCurvature={0.25}
          linkColor={(link) => {
            if (!searchQuery) return isDarkMode ? 'rgba(170, 59, 255, 0.2)' : 'rgba(170, 59, 255, 0.4)';
            const q = normalize(searchQuery);
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            const sourceMatch = normalize(sourceId).includes(q);
            const targetMatch = normalize(targetId).includes(q);
            if (sourceMatch && !targetMatch) return isDarkMode ? 'rgba(99, 102, 241, 0.8)' : 'rgba(79, 70, 229, 0.9)';
            if (targetMatch && !sourceMatch) return isDarkMode ? 'rgba(244, 63, 94, 0.8)' : 'rgba(225, 29, 72, 0.9)';
            if (sourceMatch && targetMatch) return isDarkMode ? 'rgba(255, 255, 255, 0.8)' : 'rgba(170, 59, 255, 0.9)';
            return isDarkMode ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)';
          }}
          linkWidth={(link) => {
            if (!searchQuery) return 1.5;
            const q = normalize(searchQuery);
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            return (normalize(sourceId).includes(q) || normalize(targetId).includes(q)) ? 4 : 1;
          }}
          nodeCanvasObject={paintNode}
          nodeCanvasObjectMode={() => 'after'}
          nodePointerAreaPaint={paintPointerArea}
          onNodeDragEnd={node => { node.isPinned = false; }}
          onNodeClick={node => {
            if (node.isPinned) { delete node.fx; delete node.fy; node.isPinned = false; } 
            else { node.fx = node.x; node.fy = node.y; node.isPinned = true; }
            fgRef.current?.centerAt(node.x, node.y, 1000);
            fgRef.current?.zoom(2.5, 1000);
          }}
          cooldownTicks={300}
          d3VelocityDecay={0.6}
        />
      </div>
    </div>
  );
};

export default GraphView;