import React, { useEffect, useCallback } from "react";
import ReactFlow, { Background, Controls, MiniMap, useNodesState, useEdgesState } from "reactflow";
import "reactflow/dist/style.css";
import { getKnowledgeGraph, recalculateDecay, deleteTopic } from "../api/client";
import { useTheme } from "../theme";

function decayColor(score) {
  if (score >= 0.8) return "#ef4444";
  if (score >= 0.5) return "#f97316";
  if (score >= 0.25) return "#eab308";
  return "#22c55e";
}

const LEGEND = [
  ["#22c55e", "Low (<25%)"],
  ["#eab308", "Medium (25–50%)"],
  ["#f97316", "High (50–80%)"],
  ["#ef4444", "Critical (>80%)"],
];

export default function KnowledgeGraph({ userId }) {
  const { theme, isDark } = useTheme();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = React.useState(false);
  const [selectedNode, setSelectedNode] = React.useState(null);
  const [deleting, setDeleting] = React.useState(false);

  const loadGraph = useCallback(async () => {
    setLoading(true);
    try {
      await recalculateDecay(userId);
      const { data } = await getKnowledgeGraph(userId);

      setNodes(data.nodes.map((n, i) => ({
        id: n.id,
        data: { label: `${n.label}\n${(n.decay_score * 100).toFixed(0)}% decay` },
        position: { x: (i % 4) * 230 + 40, y: Math.floor(i / 4) * 170 + 40 },
        style: {
          background: theme.surfaceAlt,
          border: `2px solid ${decayColor(n.decay_score)}`,
          borderRadius: 10,
          color: theme.text,
          fontSize: 13,
          padding: "10px 14px",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
          width: 180,
          boxSizing: "border-box",
          overflow: "hidden",
          cursor: "pointer",
        },
      })));

      setEdges(data.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.type,
        style: { stroke: theme.border, strokeWidth: 1.5 },
        labelStyle: { fill: theme.textMuted, fontSize: 10 },
        type: "smoothstep",
      })));
    } catch (err) {
      console.error("Graph load failed", err);
    } finally {
      setLoading(false);
    }
  }, [userId, theme]);

  const handleNodeClick = useCallback((_, node) => {
    setSelectedNode((prev) => prev?.id === node.id ? null : node);
  }, []);

  const handleDeleteSelected = useCallback(async () => {
    if (!selectedNode) return;
    setDeleting(true);
    try {
      await deleteTopic(selectedNode.id);
      setNodes((ns) => ns.filter((n) => n.id !== selectedNode.id));
      setEdges((es) => es.filter((e) => e.source !== selectedNode.id && e.target !== selectedNode.id));
      setSelectedNode(null);
    } catch (err) {
      console.error("Delete failed", err);
    } finally {
      setDeleting(false);
    }
  }, [selectedNode, setNodes, setEdges]);

  useEffect(() => {
    loadGraph();
    const id = setInterval(loadGraph, 30000);
    return () => clearInterval(id);
  }, [loadGraph]);

  return (
    <div style={{ width: "100%", height: "100%", position: "relative", background: theme.bg }}>
      {loading && (
        <div style={{ position: "absolute", top: 16, left: 16, zIndex: 10, color: theme.textMuted, fontSize: 13 }}>
          Recalculating decay…
        </div>
      )}
      <div style={{ position: "absolute", top: 12, right: 12, zIndex: 10, display: "flex", gap: 8 }}>
        {selectedNode && (
          <button
            onClick={handleDeleteSelected}
            disabled={deleting}
            style={{ background: theme.danger, border: "none", color: "#fff", padding: "6px 14px", borderRadius: 6, cursor: deleting ? "not-allowed" : "pointer", fontSize: 13, opacity: deleting ? 0.7 : 1 }}
          >
            {deleting ? "Deleting…" : `Delete "${selectedNode.data.label.split("\n")[0]}"`}
          </button>
        )}
      </div>

      <div style={{ position: "absolute", bottom: 80, left: 12, zIndex: 10, background: theme.surface, border: `1px solid ${theme.border}`, borderRadius: 8, padding: 10, fontSize: 12 }}>
        <div style={{ marginBottom: 4, color: theme.textMuted }}>Decay</div>
        {LEGEND.map(([c, l]) => (
          <div key={c} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: c }} />
            <span style={{ color: theme.textMuted }}>{l}</span>
          </div>
        ))}
      </div>

      <ReactFlow
        nodes={nodes.map((n) => ({
          ...n,
          style: {
            ...n.style,
            outline: selectedNode?.id === n.id ? `2px solid ${theme.accent}` : "none",
            outlineOffset: 2,
          },
        }))}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        fitView
      >
        <Background color={theme.border} gap={24} />
        <Controls style={{ background: theme.surfaceAlt, border: `1px solid ${theme.border}` }} />
        <MiniMap
          style={{ background: theme.surface }}
          nodeColor={(n) => n.style?.borderColor || theme.border}
          maskColor={isDark ? "rgba(0,0,0,0.4)" : "rgba(255,255,255,0.6)"}
        />
      </ReactFlow>
    </div>
  );
}
