"""
Fault Tree Analysis Tool — Streamlit
=====================================
Hazard → System Failures (SF) → Following Failures (FF) → Initial Failures (IF)
Supports OR / AND gates, equal / weighted budget distribution, and JSON save/load.
"""

import streamlit as st
import json
import uuid
import math
import copy
from datetime import datetime
import pandas as pd

# ─── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fault Tree Analyser",
    page_icon="⚠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;600;700&display=swap');

  html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
  code, .mono { font-family: 'IBM Plex Mono', monospace; }

  .stApp { background: #08080f; color: #c8c8d8; }

  /* cards */
  .hazard-card  { background:#110820; border:1.5px solid #7c3aed; border-radius:12px; padding:16px; margin-bottom:16px; box-shadow:0 0 20px #7c3aed33; }
  .sf-card      { background:#071220; border:1.5px solid #0ea5e9; border-radius:11px; padding:14px; margin-bottom:12px; box-shadow:0 0 14px #0ea5e933; }
  .ff-card      { background:#081a0e; border:1px solid #16a34a;   border-radius:9px;  padding:10px; margin-bottom:8px;  box-shadow:0 0 10px #16a34a22; }
  .if-card      { background:#1c1000; border:1px solid #d97706;   border-radius:7px;  padding:8px;  margin-bottom:6px;  box-shadow:0 0 8px #d9770622; }

  .badge-ok   { background:#052e16; color:#4ade80; border:1px solid #16a34a; border-radius:10px; padding:1px 8px; font-size:11px; font-weight:700; }
  .badge-over { background:#2d0707; color:#f87171; border:1px solid #dc2626; border-radius:10px; padding:1px 8px; font-size:11px; font-weight:700; }
  .badge-sf   { background:#0a1628; color:#38bdf8; border:1px solid #0ea5e9; border-radius:6px;  padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }
  .badge-ff   { background:#081a0e; color:#4ade80; border:1px solid #16a34a; border-radius:6px;  padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }
  .badge-if   { background:#1c1000; color:#fbbf24; border:1px solid #d97706; border-radius:6px;  padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }

  .metric-label { font-size:10px; color:#555; letter-spacing:2px; font-weight:800; }
  .metric-value { font-size:18px; font-weight:800; font-family:'IBM Plex Mono',monospace; }
  .ok-color   { color:#4ade80; }
  .over-color { color:#f87171; }
  .muted      { color:#888; font-size:11px; font-family:'IBM Plex Mono',monospace; }

  div[data-testid="stHorizontalBlock"] { gap:4px; }
  div[data-testid="column"] { padding: 0 4px; }

  /* sidebar */
  [data-testid="stSidebar"] { background:#0d0d1a; border-right:1px solid #1f1f3a; }

  /* inputs */
  input[type="number"], input[type="text"] { background:#0a0a18 !important; color:#e2e8f0 !important; }

  /* expander */
  details { border:1px solid #1f1f3a !important; border-radius:8px !important; }

  /* hide streamlit branding */
  #MainMenu {visibility:hidden;} footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ─── core engine ──────────────────────────────────────────────────────────────
def new_id():
    return str(uuid.uuid4())[:8]

def fmt(v):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return "–"
    if v == 0:
        return "0"
    return f"{v:.2e}"

def calc_node(node):
    """Bottom-up probability calculation."""
    children = node.get("children", [])
    if not children:
        return node.get("value")
    vals = [calc_node(c) for c in children]
    vals = [v for v in vals if v is not None]
    if not vals:
        return node.get("value")
    if node.get("gate", "OR") == "OR":
        return sum(vals)
    else:  # AND
        result = 1.0
        for v in vals:
            result *= v
        return result

def propagate_targets(node, target):
    """Top-down target propagation."""
    node = copy.deepcopy(node)
    node["_target"] = target
    children = node.get("children", [])
    if not children:
        return node
    gate = node.get("gate", "OR")
    if gate == "OR":
        child_target = target / len(children)
        node["children"] = [propagate_targets(c, child_target) for c in children]
    else:  # AND: nth root
        root = 1 / len(children)
        child_target = max(target, 1e-300) ** root
        node["children"] = [propagate_targets(c, child_target) for c in children]
    return node

def redistribute(tree, mode="equal"):
    """Distribute hazard budget across SFs then propagate down."""
    sfs = tree.get("children", [])
    if not sfs:
        return tree
    hazard_target = tree.get("value", 1e-7)

    if mode == "equal":
        sf_target = hazard_target / len(sfs)
        new_sfs = []
        for sf in sfs:
            sf = copy.deepcopy(sf)
            sf["weight"] = 1
            sf["_target"] = sf_target
            sf["children"] = [propagate_targets(ff, sf_target / max(len(sf.get("children", [])), 1))
                               for ff in sf.get("children", [])]
            new_sfs.append(sf)
    else:  # weighted
        total_w = sum(sf.get("weight", 1) for sf in sfs)
        new_sfs = []
        for sf in sfs:
            sf = copy.deepcopy(sf)
            sf_target = hazard_target * (sf.get("weight", 1) / total_w)
            sf["_target"] = sf_target
            sf["children"] = [propagate_targets(ff, sf_target / max(len(sf.get("children", [])), 1))
                               for ff in sf.get("children", [])]
            new_sfs.append(sf)

    tree = copy.deepcopy(tree)
    tree["children"] = new_sfs
    return tree

def status_badge(calc, target):
    if calc is None or target is None:
        return ""
    ok = calc <= target * 1.001
    cls = "badge-ok" if ok else "badge-over"
    txt = "✓ OK" if ok else "✗ OVER"
    return f'<span class="{cls}">{txt}</span>'

# ─── node factories ───────────────────────────────────────────────────────────
def make_if(label="IF-A", value=1e-5):
    return {"id": new_id(), "type": "IF", "label": label, "value": value, "children": [], "gate": "OR"}

def make_ff(label="FF-1"):
    return {"id": new_id(), "type": "FF", "label": label, "gate": "OR",
            "children": [make_if("IF-A"), make_if("IF-B")], "value": None}

def make_sf(label="SF-1"):
    return {"id": new_id(), "type": "SF", "label": label, "gate": "OR", "weight": 1,
            "children": [make_ff("FF-1"), make_ff("FF-2"), make_ff("FF-3")], "value": None}

def build_default_tree():
    tree = {
        "id": new_id(), "type": "HAZARD", "label": "Hazard",
        "value": 1e-7, "gate": "OR",
        "children": [make_sf("SF-1"), make_sf("SF-2"), make_sf("SF-3")]
    }
    return redistribute(tree, "equal")

# ─── session state init ───────────────────────────────────────────────────────
if "tree" not in st.session_state:
    st.session_state.tree = build_default_tree()
if "dist_mode" not in st.session_state:
    st.session_state.dist_mode = "equal"
if "project_name" not in st.session_state:
    st.session_state.project_name = "My FTA Project"

def get_tree():
    return st.session_state.tree

def set_tree(t):
    st.session_state.tree = t

# ─── sidebar: project management ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚠ Fault Tree Analyser")
    st.divider()

    st.markdown("**📁 Project**")
    project_name = st.text_input("Project name", value=st.session_state.project_name, label_visibility="collapsed")
    st.session_state.project_name = project_name

    # Save to JSON
    tree_json = json.dumps({
        "project": project_name,
        "saved_at": datetime.now().isoformat(),
        "dist_mode": st.session_state.dist_mode,
        "tree": get_tree()
    }, indent=2)
    st.download_button(
        label="💾 Save / Download JSON",
        data=tree_json,
        file_name=f"{project_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True,
    )

    # Load from JSON
    uploaded = st.file_uploader("📂 Load JSON", type="json", label_visibility="collapsed")
    if uploaded:
        try:
            data = json.load(uploaded)
            set_tree(data["tree"])
            st.session_state.dist_mode = data.get("dist_mode", "equal")
            st.session_state.project_name = data.get("project", "Loaded Project")
            st.success("Loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Error loading file: {e}")

    st.divider()

    # Export summary table
    st.markdown("**📊 Export Summary**")
    if st.button("Export to CSV", use_container_width=True):
        rows = []
        for sf in get_tree().get("children", []):
            sf_calc = calc_node(sf)
            for ff in sf.get("children", []):
                ff_calc = calc_node(ff)
                for ifn in ff.get("children", []):
                    rows.append({
                        "SF": sf["label"], "SF_gate": sf["gate"],
                        "SF_calc": sf_calc, "SF_target": sf.get("_target"),
                        "FF": ff["label"], "FF_gate": ff["gate"],
                        "FF_calc": ff_calc, "FF_target": ff.get("_target"),
                        "IF": ifn["label"], "IF_value": ifn.get("value"),
                        "IF_target": ifn.get("_target"),
                    })
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False)
        st.download_button("⬇ Download CSV", csv,
                           file_name=f"{project_name}_summary.csv",
                           mime="text/csv", use_container_width=True)

    st.divider()
    st.markdown("**ℹ️ Help**")
    with st.expander("How to use"):
        st.markdown("""
- Set your **Hazard target** probability
- Choose **Equal** or **Weighted** distribution
- Add/remove SF, FF, IF nodes
- Set **IF values** — calculated probabilities flow upward
- Green ✓ = within budget · Red ✗ = over budget
- **Save** to JSON to preserve your work
- **Load** any saved JSON to continue later
        """)
    with st.expander("Gate logic"):
        st.markdown("""
- **OR gate**: P = sum of children (conservative)
- **AND gate**: P = product of children (concurrent failures)
- Target propagation uses the inverse logic top-down
        """)

# ─── header ───────────────────────────────────────────────────────────────────
st.markdown(f"## ⚠ {st.session_state.project_name}")
st.caption("HAZARD → SYSTEM FAILURES → FOLLOWING FAILURES → INITIAL FAILURES")

# ─── hazard config row ────────────────────────────────────────────────────────
tree = get_tree()
hazard_calc = calc_node(tree)
hazard_ok = hazard_calc is not None and hazard_calc <= tree["value"] * 1.001

st.markdown('<div class="hazard-card">', unsafe_allow_html=True)
hcol1, hcol2, hcol3, hcol4 = st.columns([2, 1.5, 2, 2])

with hcol1:
    st.markdown('<div class="metric-label">HAZARD TARGET</div>', unsafe_allow_html=True)
    new_hazard = st.number_input("Hazard target", value=tree["value"], format="%.2e",
                                  step=1e-8, label_visibility="collapsed", key="hazard_val")
    if new_hazard != tree["value"]:
        tree["value"] = new_hazard
        tree = redistribute(tree, st.session_state.dist_mode)
        set_tree(tree)
        st.rerun()

with hcol2:
    st.markdown('<div class="metric-label">HAZARD GATE</div>', unsafe_allow_html=True)
    hgate = st.selectbox("Gate", ["OR", "AND"], index=0 if tree.get("gate", "OR") == "OR" else 1,
                          label_visibility="collapsed", key="hazard_gate")
    if hgate != tree.get("gate"):
        tree["gate"] = hgate
        tree = redistribute(tree, st.session_state.dist_mode)
        set_tree(tree)
        st.rerun()

with hcol3:
    st.markdown('<div class="metric-label">CALCULATED</div>', unsafe_allow_html=True)
    color = "ok-color" if hazard_ok else "over-color"
    badge = status_badge(hazard_calc, tree["value"])
    st.markdown(f'<div class="metric-value {color}">{fmt(hazard_calc)} {badge}</div>', unsafe_allow_html=True)
    if hazard_calc and tree["value"]:
        pct = (hazard_calc / tree["value"]) * 100
        pct_color = "ok-color" if pct <= 100 else "over-color"
        st.markdown(f'<div class="muted">Budget used: <span class="{pct_color}">{pct:.1f}%</span></div>',
                    unsafe_allow_html=True)

with hcol4:
    st.markdown('<div class="metric-label">DISTRIBUTION MODE</div>', unsafe_allow_html=True)
    new_mode = st.radio("Mode", ["equal", "weighted"],
                         index=0 if st.session_state.dist_mode == "equal" else 1,
                         horizontal=True, label_visibility="collapsed", key="dist_mode_radio")
    if new_mode != st.session_state.dist_mode:
        st.session_state.dist_mode = new_mode
        tree = redistribute(tree, new_mode)
        set_tree(tree)
        st.rerun()
    if st.session_state.dist_mode == "equal":
        st.caption("Each SF gets equal share of hazard budget")
    else:
        st.caption("Budget split by SF weight — adjust per SF below")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# ─── summary stats row ────────────────────────────────────────────────────────
sfs = tree.get("children", [])
ff_count = sum(len(sf.get("children", [])) for sf in sfs)
if_count = sum(len(ff.get("children", [])) for sf in sfs for ff in sf.get("children", []))
sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("System Failures", len(sfs))
sc2.metric("Following Failures", ff_count)
sc3.metric("Initial Failures", if_count)
sc4.metric("Hazard Budget Used", f"{(hazard_calc / tree['value'] * 100):.1f}%" if hazard_calc and tree["value"] else "–")

st.divider()

# ─── add SF button ────────────────────────────────────────────────────────────
col_add, col_redist = st.columns([2, 2])
with col_add:
    if st.button("➕ Add System Failure", type="primary", use_container_width=True):
        n = len(sfs) + 1
        tree["children"].append(make_sf(f"SF-{n}"))
        # always equal on add
        st.session_state.dist_mode = "equal"
        tree = redistribute(tree, "equal")
        set_tree(tree)
        st.rerun()
with col_redist:
    if st.button("🔄 Recalculate All Targets", use_container_width=True):
        tree = redistribute(tree, st.session_state.dist_mode)
        set_tree(tree)
        st.rerun()

st.divider()

# ─── SF loop ──────────────────────────────────────────────────────────────────
tree_changed = False
sfs = tree.get("children", [])

for sf_idx, sf in enumerate(sfs):
    sf_calc = calc_node(sf)
    sf_ok = sf_calc is not None and sf.get("_target") and sf_calc <= sf.get("_target", 0) * 1.001
    sf_badge = status_badge(sf_calc, sf.get("_target"))

    with st.expander(
        f"🔷 {sf['label']}  |  calc: {fmt(sf_calc)}  |  target: {fmt(sf.get('_target'))}  {'✓' if sf_ok else '✗'}",
        expanded=True
    ):
        st.markdown('<div class="sf-card">', unsafe_allow_html=True)

        # SF header row
        sfc1, sfc2, sfc3, sfc4, sfc5 = st.columns([2, 1.5, 1.5, 1.5, 1])

        with sfc1:
            new_label = st.text_input("SF Label", value=sf["label"], key=f"sf_label_{sf['id']}", label_visibility="collapsed")
            if new_label != sf["label"]:
                sfs[sf_idx]["label"] = new_label
                tree_changed = True

        with sfc2:
            st.markdown(f'<div class="muted">calc: <strong>{fmt(sf_calc)}</strong></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="muted">target: {fmt(sf.get("_target"))}</div>', unsafe_allow_html=True)
            st.markdown(sf_badge, unsafe_allow_html=True)

        with sfc3:
            gate_opts = ["OR", "AND"]
            sf_gate = st.selectbox("Gate", gate_opts,
                                    index=gate_opts.index(sf.get("gate", "OR")),
                                    key=f"sf_gate_{sf['id']}", label_visibility="collapsed")
            if sf_gate != sf.get("gate"):
                sfs[sf_idx]["gate"] = sf_gate
                tree_changed = True

        with sfc4:
            if st.session_state.dist_mode == "weighted":
                new_w = st.number_input("Weight", value=float(sf.get("weight", 1)),
                                         min_value=0.01, step=0.1,
                                         key=f"sf_w_{sf['id']}", label_visibility="collapsed")
                if new_w != sf.get("weight"):
                    sfs[sf_idx]["weight"] = new_w
                    tree_changed = True
            else:
                st.caption("weight: 1 (equal)")

        with sfc5:
            if st.button("🗑", key=f"del_sf_{sf['id']}", help="Delete this SF"):
                tree["children"] = [s for s in sfs if s["id"] != sf["id"]]
                tree = redistribute(tree, st.session_state.dist_mode)
                set_tree(tree)
                st.rerun()

        st.markdown("---")

        # ── FF loop ───────────────────────────────────────────────────────────
        ffs = sf.get("children", [])
        for ff_idx, ff in enumerate(ffs):
            ff_calc = calc_node(ff)
            ff_ok = ff_calc is not None and ff.get("_target") and ff_calc <= ff.get("_target", 0) * 1.001
            ff_badge = status_badge(ff_calc, ff.get("_target"))

            st.markdown('<div class="ff-card">', unsafe_allow_html=True)
            ffc1, ffc2, ffc3, ffc4, ffc5 = st.columns([2, 1.5, 1.5, 2, 0.5])

            with ffc1:
                st.markdown('<span class="badge-ff">FF</span>', unsafe_allow_html=True)
                new_ff_label = st.text_input("FF", value=ff["label"], key=f"ff_label_{ff['id']}", label_visibility="collapsed")
                if new_ff_label != ff["label"]:
                    sfs[sf_idx]["children"][ff_idx]["label"] = new_ff_label
                    tree_changed = True

            with ffc2:
                st.markdown(f'<div class="muted">calc: {fmt(ff_calc)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="muted">tgt: {fmt(ff.get("_target"))}</div>', unsafe_allow_html=True)
                st.markdown(ff_badge, unsafe_allow_html=True)

            with ffc3:
                ff_gate = st.selectbox("Gate", ["OR", "AND"],
                                        index=0 if ff.get("gate", "OR") == "OR" else 1,
                                        key=f"ff_gate_{ff['id']}", label_visibility="collapsed")
                if ff_gate != ff.get("gate"):
                    sfs[sf_idx]["children"][ff_idx]["gate"] = ff_gate
                    tree_changed = True

            with ffc4:
                if st.button("➕ Add IF", key=f"add_if_{ff['id']}", use_container_width=True):
                    n = len(ff.get("children", [])) + 1
                    sfs[sf_idx]["children"][ff_idx]["children"].append(make_if(f"IF-{n}"))
                    tree_changed = True

            with ffc5:
                if st.button("🗑", key=f"del_ff_{ff['id']}", help="Delete FF"):
                    sfs[sf_idx]["children"] = [f for f in ffs if f["id"] != ff["id"]]
                    tree_changed = True

            # ── IF loop ───────────────────────────────────────────────────────
            ifs = ff.get("children", [])
            if_cols = st.columns(min(len(ifs), 4)) if ifs else []

            for if_idx, ifn in enumerate(ifs):
                col = if_cols[if_idx % 4] if if_cols else st.container()
                with col:
                    st.markdown('<div class="if-card">', unsafe_allow_html=True)
                    st.markdown('<span class="badge-if">IF</span>', unsafe_allow_html=True)

                    new_if_label = st.text_input("IF label", value=ifn["label"],
                                                  key=f"if_label_{ifn['id']}", label_visibility="collapsed")
                    if new_if_label != ifn["label"]:
                        sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["label"] = new_if_label
                        tree_changed = True

                    new_val = st.number_input("P =", value=float(ifn.get("value") or 1e-5),
                                               format="%.2e", step=1e-6,
                                               key=f"if_val_{ifn['id']}", label_visibility="collapsed")
                    if new_val != ifn.get("value"):
                        sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["value"] = new_val
                        tree_changed = True

                    if ifn.get("_target"):
                        if_ok = new_val <= ifn["_target"] * 1.001
                        tgt_color = "ok-color" if if_ok else "over-color"
                        st.markdown(
                            f'<div class="muted">tgt: <span class="{tgt_color}">{fmt(ifn["_target"])}</span></div>',
                            unsafe_allow_html=True
                        )

                    if st.button("✕", key=f"del_if_{ifn['id']}", help="Delete IF"):
                        sfs[sf_idx]["children"][ff_idx]["children"] = [
                            i for i in ifs if i["id"] != ifn["id"]
                        ]
                        tree_changed = True

                    st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)  # ff-card

        # add FF button
        if st.button(f"➕ Add Following Failure to {sf['label']}", key=f"add_ff_{sf['id']}"):
            n = len(ffs) + 1
            sfs[sf_idx]["children"].append(make_ff(f"FF-{n}"))
            tree_changed = True

        st.markdown('</div>', unsafe_allow_html=True)  # sf-card

# ─── apply changes & rerun ────────────────────────────────────────────────────
if tree_changed:
    tree["children"] = sfs
    tree = redistribute(tree, st.session_state.dist_mode)
    set_tree(tree)
    st.rerun()
