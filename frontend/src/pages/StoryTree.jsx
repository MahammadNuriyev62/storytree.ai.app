import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";

import { api } from "../api.js";
import { moodFor } from "../theme.js";
import { loadProgress } from "../progress.js";

// Layout knobs.
const X_GAP = 220;   // horizontal distance between siblings
const Y_GAP = 140;   // vertical distance between levels

// Walk the tree breadth-first from the root and assign each node an (x, y).
// Width-aware: leaves are placed first (one column each), parents are then
// centered above their children. This handles both wide-shallow and
// narrow-deep stories cleanly without external layout libs.
function layoutTree(nodes, edges, rootId) {
  if (!rootId) return new Map();

  const childrenOf = new Map();
  for (const e of edges) {
    if (!childrenOf.has(e.from)) childrenOf.set(e.from, []);
    childrenOf.get(e.from).push(e.to);
  }

  // Depth of each node from root (for y).
  const depth = new Map([[rootId, 0]]);
  const order = [rootId];
  let head = 0;
  while (head < order.length) {
    const n = order[head++];
    for (const c of childrenOf.get(n) || []) {
      if (!depth.has(c)) {
        depth.set(c, depth.get(n) + 1);
        order.push(c);
      }
    }
  }

  // x by post-order leaf counting: each leaf consumes 1 column; parents
  // get centered over their children's column span.
  let nextLeafX = 0;
  const x = new Map();
  function visit(id) {
    const kids = childrenOf.get(id) || [];
    if (kids.length === 0) {
      x.set(id, nextLeafX++);
      return;
    }
    for (const k of kids) visit(k);
    const xs = kids.map((k) => x.get(k));
    x.set(id, (Math.min(...xs) + Math.max(...xs)) / 2);
  }
  visit(rootId);

  // Catch orphans (placeholder children whose parent edge got deleted etc.) —
  // park them in a column past the rightmost leaf.
  for (const n of nodes) {
    if (!x.has(n.id)) {
      x.set(n.id, nextLeafX++);
      depth.set(n.id, 0);
    }
  }

  const positions = new Map();
  for (const n of nodes) {
    positions.set(n.id, {
      x: x.get(n.id) * X_GAP,
      y: (depth.get(n.id) ?? 0) * Y_GAP,
    });
  }
  return positions;
}

export default function StoryTree() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [tree, setTree] = useState(null);
  const [err, setErr] = useState(null);
  const progress = useMemo(() => loadProgress(id), [id]);
  const lastSceneId = progress?.sceneId ?? null;

  useEffect(() => {
    api.getStoryTree(id).then(setTree).catch((e) => setErr(String(e)));
  }, [id]);

  // Click a scene node → deep-link into the play screen at that scene.
  const onNodeClick = useCallback(
    (_, node) => {
      if (!node?.data?.is_generated) return; // can't jump to placeholders
      navigate(`/play/${id}?scene=${node.id}&page=1`);
    },
    [id, navigate],
  );

  const { nodes, edges } = useMemo(() => {
    if (!tree) return { nodes: [], edges: [] };
    const positions = layoutTree(tree.nodes, tree.edges, tree.root_scene_id);
    const rfNodes = tree.nodes.map((n) => {
      const mood = moodFor(n.pacing);
      const isCurrent = String(n.id) === String(lastSceneId);
      const isRoot = n.id === tree.root_scene_id;
      const border = isCurrent
        ? "3px solid #f5d568"
        : n.has_terminal_choice
        ? "2px solid #ec4899"
        : n.is_generated
        ? `2px solid ${mood.accent}`
        : "1px dashed rgba(255,255,255,0.3)";
      return {
        id: String(n.id),
        type: "default",
        position: positions.get(n.id) || { x: 0, y: 0 },
        data: {
          ...n,
          label: (
            <div className="text-left" style={{ fontFamily: "ui-sans-serif" }}>
              <div className="text-[10px] font-mono opacity-70">
                #{n.id}
                {isRoot ? " · root" : ""}
                {n.pacing ? ` · ${n.pacing}` : ""}
              </div>
              <div
                className="text-xs mt-1"
                style={{
                  maxWidth: 180,
                  lineHeight: 1.25,
                  opacity: n.is_generated ? 1 : 0.55,
                }}
              >
                {n.is_generated ? (n.text_preview || "…") : "unexplored"}
              </div>
            </div>
          ),
        },
        style: {
          background: n.is_generated ? "rgba(28, 20, 48, 0.92)" : "rgba(28, 20, 48, 0.5)",
          color: "#f5f3ff",
          border,
          borderRadius: 10,
          padding: 8,
          minWidth: 160,
          maxWidth: 220,
          cursor: n.is_generated ? "pointer" : "not-allowed",
        },
      };
    });
    const rfEdges = tree.edges.map((e) => ({
      id: `e${e.choice_id}`,
      source: String(e.from),
      target: String(e.to),
      label: (e.text || "").slice(0, 36) + ((e.text || "").length > 36 ? "…" : ""),
      labelStyle: {
        fill: e.is_wrong ? "#ff7575" : "#cfc6ff",
        fontSize: 10,
        fontFamily: "ui-monospace, monospace",
      },
      labelBgPadding: [3, 2],
      labelBgBorderRadius: 4,
      labelBgStyle: { fill: "rgba(10, 6, 20, 0.85)" },
      animated: e.is_pre_final,
      style: {
        stroke: e.is_pre_final ? "#ec4899" : e.is_wrong ? "#ff7575" : "rgba(180, 170, 220, 0.7)",
        strokeWidth: 1.6,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: e.is_pre_final ? "#ec4899" : "#cfc6ff" },
    }));
    return { nodes: rfNodes, edges: rfEdges };
  }, [tree, lastSceneId]);

  if (err) return <p className="text-red-300 text-center mt-10">{err}</p>;
  if (!tree) return <p className="text-center text-white/50 mt-10">Loading map…</p>;

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <Link to={`/story/${id}`} className="text-sm text-white/70 hover:text-white">
            ← {tree.title}
          </Link>
          <h1 className="text-2xl font-bold mt-1">Story map</h1>
        </div>
        <div className="text-xs text-white/60 dark-glass rounded-full px-3 py-1.5">
          {tree.nodes.filter((n) => n.is_generated).length}/{tree.nodes.length} scenes explored
        </div>
      </div>

      <div className="glass rounded-2xl overflow-hidden" style={{ height: "78vh" }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          nodesDraggable={false}
          nodesConnectable={false}
          minZoom={0.15}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={28} color="rgba(255,255,255,0.06)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-white/60">
        <span><span className="inline-block w-3 h-3 align-middle mr-1" style={{ border: "3px solid #f5d568", borderRadius: 4 }} /> last visited</span>
        <span><span className="inline-block w-3 h-3 align-middle mr-1" style={{ border: "2px solid #ec4899", borderRadius: 4 }} /> has a "The End" choice</span>
        <span><span className="inline-block w-3 h-3 align-middle mr-1" style={{ border: "1px dashed rgba(255,255,255,0.5)", borderRadius: 4 }} /> unexplored placeholder</span>
        <span><span className="inline-block w-3 h-3 align-middle mr-1" style={{ background: "#ff7575", borderRadius: 2 }} /> costly choice</span>
        <span>Click any explored scene to jump there.</span>
      </div>
    </div>
  );
}
