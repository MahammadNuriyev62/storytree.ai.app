import { useEffect, useMemo, useState, useCallback } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";
import "reactflow/dist/style.css";

import { api } from "../api.js";
import { moodFor } from "../theme.js";
import { loadProgress } from "../progress.js";

// Layout knobs — generous gaps so edge labels never crash into neighbouring
// nodes and dense branches still breathe. Tuned by eye against story 2
// (17 scenes, mix of explored + unexplored).
const NODE_W = 230;
const NODE_H = 120;
const X_GAP = 320;
const Y_GAP = 260;

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

// Hex string for the pacing colour, with an alpha modifier — used both
// for the node border and the soft inner glow.
function tintFromMood(mood, alpha = "ff") {
  // mood.accent is already a hex like "#a78bfa"
  return (mood?.accent || "#a78bfa") + alpha;
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

      // Stack of border + glow choices, most-specific first.
      let border, boxShadow;
      if (isCurrent) {
        border = "2px solid #f5d568";
        boxShadow = "0 0 0 3px rgba(245, 213, 104, 0.18), 0 12px 26px rgba(245, 213, 104, 0.20)";
      } else if (n.has_terminal_choice) {
        border = "2px solid #ec4899";
        boxShadow = "0 0 0 2px rgba(236, 72, 153, 0.12), 0 10px 22px rgba(0,0,0,0.45)";
      } else if (n.is_generated) {
        border = `1.5px solid ${tintFromMood(mood)}`;
        boxShadow = "0 10px 22px rgba(0,0,0,0.45)";
      } else {
        border = "1px dashed rgba(255,255,255,0.22)";
        boxShadow = "none";
      }

      // Subtle pacing-tinted gradient inside generated nodes; flat-and-dim
      // for placeholders so the eye skips past them.
      const bg = n.is_generated
        ? `linear-gradient(180deg, rgba(28, 20, 48, 0.96) 0%, rgba(28, 20, 48, 0.92) 100%)`
        : "rgba(28, 20, 48, 0.4)";

      return {
        id: String(n.id),
        type: "default",
        position: positions.get(n.id) || { x: 0, y: 0 },
        data: {
          ...n,
          label: (
            <div className="text-left" style={{ fontFamily: "ui-sans-serif" }}>
              <div className="flex items-center justify-between gap-2 mb-2">
                <span
                  className="text-[10px] font-mono"
                  style={{ opacity: n.is_generated ? 0.65 : 0.45 }}
                >
                  #{n.id}{isRoot ? " · root" : ""}
                </span>
                {n.pacing && (
                  <span
                    className="text-[9px] uppercase tracking-wider font-semibold px-1.5 py-0.5 rounded"
                    style={{
                      background: tintFromMood(mood, "22"),
                      color: tintFromMood(mood),
                    }}
                  >
                    {n.pacing}
                  </span>
                )}
              </div>
              <div
                className="text-[11.5px]"
                style={{
                  lineHeight: 1.4,
                  opacity: n.is_generated ? 0.92 : 0.55,
                  fontStyle: n.is_generated ? "normal" : "italic",
                }}
              >
                {n.is_generated ? (n.text_preview || "…") : "unexplored"}
              </div>
            </div>
          ),
        },
        style: {
          background: bg,
          color: "#f5f3ff",
          border,
          borderRadius: 12,
          padding: "12px 14px",
          width: NODE_W,
          minHeight: NODE_H,
          cursor: n.is_generated ? "pointer" : "not-allowed",
          boxShadow,
          transition: "transform 0.15s ease, box-shadow 0.2s ease",
        },
      };
    });

    const rfEdges = tree.edges.map((e) => {
      const stroke = e.is_pre_final
        ? "#ec4899"
        : e.is_wrong
        ? "#ff7575"
        : "rgba(190, 178, 230, 0.65)";
      return {
        id: `e${e.choice_id}`,
        source: String(e.from),
        target: String(e.to),
        type: "smoothstep",
        label: (e.text || "").slice(0, 28) + ((e.text || "").length > 28 ? "…" : ""),
        labelStyle: {
          fill: e.is_wrong ? "#ffb0b0" : "#e7ddff",
          fontSize: 10.5,
          fontFamily: "ui-sans-serif",
          fontWeight: 500,
        },
        labelBgPadding: [6, 4],
        labelBgBorderRadius: 6,
        labelBgStyle: { fill: "rgba(10, 6, 20, 0.92)", stroke, strokeWidth: 0.5 },
        animated: e.is_pre_final,
        style: { stroke, strokeWidth: 1.5 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 14,
          height: 14,
        },
      };
    });
    return { nodes: rfNodes, edges: rfEdges };
  }, [tree, lastSceneId]);

  if (err) return <p className="text-red-300 text-center mt-10">{err}</p>;
  if (!tree) return <p className="text-center text-white/50 mt-10">Loading map…</p>;

  const generatedCount = tree.nodes.filter((n) => n.is_generated).length;

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-5 gap-4 flex-wrap">
        <div>
          <Link to={`/story/${id}`} className="text-sm text-white/70 hover:text-white">
            ← {tree.title}
          </Link>
          <h1 className="text-3xl font-bold mt-1 tracking-tight">Story map</h1>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="dark-glass rounded-full px-3 py-1.5 text-white/75">
            <span className="font-semibold text-white">{generatedCount}</span>
            <span className="text-white/55"> / {tree.nodes.length} scenes explored</span>
          </span>
          <span className="dark-glass rounded-full px-3 py-1.5 text-white/75">
            <span className="font-semibold text-white">{tree.edges.length}</span>
            <span className="text-white/55"> choices made</span>
          </span>
        </div>
      </div>

      <div
        className="glass rounded-2xl overflow-hidden"
        style={{ height: "78vh", boxShadow: "0 18px 48px rgba(0,0,0,0.35)" }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodeClick={onNodeClick}
          fitView
          fitViewOptions={{ padding: 0.22 }}
          nodesDraggable={false}
          nodesConnectable={false}
          minZoom={0.12}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background gap={36} size={1.4} color="rgba(255,255,255,0.05)" />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-[11px] text-white/55">
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded"
            style={{ border: "2px solid #f5d568", background: "rgba(245,213,104,0.1)" }}
          />
          last visited
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded"
            style={{ border: "2px solid #ec4899", background: "rgba(236,72,153,0.1)" }}
          />
          has a "The End" choice
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded"
            style={{ border: "1px dashed rgba(255,255,255,0.5)" }}
          />
          unexplored placeholder
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5" style={{ background: "#ff7575" }} />
          costly choice
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-0.5" style={{ background: "#ec4899" }} />
          pre-final choice
        </span>
        <span className="ml-auto italic">Click any explored scene to jump there.</span>
      </div>
    </div>
  );
}
