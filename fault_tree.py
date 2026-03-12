"""
Fault Tree Analysis Tool v2 — Streamlit
=========================================
Rebuilt to match real FTA diagrams:
- Proper node ID system (SF-01, FF-42, IF-100)
- Multiple hazards per project (tabs)
- Calculation audit trail / formula box
- Node annotations & status flags
- Equal / weighted SF distribution
- Full save/load JSON
- CSV export with audit trail
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
    page_title="FTA Tool",
    page_icon="⚠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"]  { font-family: 'IBM Plex Sans', sans-serif; background:#08080f; color:#c8c8d8; }

/* ── cards ── */
.hazard-card { background:#110820; border:2px solid #7c3aed; border-radius:14px; padding:18px 20px; margin-bottom:18px; box-shadow:0 0 28px #7c3aed30; }
.sf-card     { background:#071220; border:1.5px solid #0ea5e9; border-radius:11px; padding:14px 16px; margin-bottom:14px; box-shadow:0 0 14px #0ea5e922; }
.ff-card     { background:#081a0e; border:1px solid #16a34a; border-radius:9px; padding:10px 12px; margin-bottom:10px; box-shadow:0 0 10px #16a34a18; }
.if-card     { background:#1c1000; border:1px solid #d97706; border-radius:7px; padding:8px 10px; margin-bottom:6px; box-shadow:0 0 7px #d9770618; }
.audit-card  { background:#0a0a18; border:1px solid #334155; border-radius:10px; padding:14px 18px; font-family:'IBM Plex Mono',monospace; font-size:12px; line-height:1.8; }
.note-tbc    { background:#1a1200; border:1px solid #ca8a04; border-radius:6px; padding:3px 8px; font-size:11px; color:#fde68a; display:inline-block; }
.note-reword { background:#1a0800; border:1px solid #ea580c; border-radius:6px; padding:3px 8px; font-size:11px; color:#fed7aa; display:inline-block; }
.note-ok     { background:#052e16; border:1px solid #16a34a; border-radius:6px; padding:3px 8px; font-size:11px; color:#86efac; display:inline-block; }

/* ── badges ── */
.badge-ok    { background:#052e16; color:#4ade80; border:1px solid #16a34a; border-radius:10px; padding:1px 9px; font-size:11px; font-weight:700; }
.badge-over  { background:#2d0707; color:#f87171; border:1px solid #dc2626; border-radius:10px; padding:1px 9px; font-size:11px; font-weight:700; }
.badge-sf    { background:#0a1628; color:#38bdf8; border:1px solid #0ea5e9; border-radius:5px; padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }
.badge-ff    { background:#081a0e; color:#4ade80; border:1px solid #16a34a; border-radius:5px; padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }
.badge-if    { background:#1c1000; color:#fbbf24; border:1px solid #d97706; border-radius:5px; padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1px; }
.badge-gate-or  { background:#2d0a0a; color:#f87171; border:1px solid #f87171; border-radius:4px; padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1.5px; }
.badge-gate-and { background:#0a1a2d; color:#60a5fa; border:1px solid #60a5fa; border-radius:4px; padding:1px 7px; font-size:10px; font-weight:800; letter-spacing:1.5px; }

/* ── typography ── */
.node-id     { font-family:'IBM Plex Mono',monospace; font-size:11px; font-weight:700; color:#94a3b8; letter-spacing:1px; }
.node-label  { font-size:13px; font-weight:600; color:#e2e8f0; }
.prob-value  { font-family:'IBM Plex Mono',monospace; font-size:13px; font-weight:700; }
.prob-target { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#64748b; }
.section-title { font-size:11px; font-weight:800; letter-spacing:2px; color:#475569; margin-bottom:8px; }
.mono        { font-family:'IBM Plex Mono',monospace; }

/* ── metrics ── */
.big-metric  { font-family:'IBM Plex Mono',monospace; font-size:22px; font-weight:800; }
.ok-color    { color:#4ade80; }
.over-color  { color:#f87171; }
.muted-color { color:#64748b; }

/* ── streamlit overrides ── */
.stApp { background:#08080f; }
[data-testid="stSidebar"] { background:#0d0d1a; border-right:1px solid #1e1e3a; }
div[data-testid="stExpander"] { border:1px solid #1e1e3a !important; border-radius:10px !important; background:#0d0d1a !important; }
.stButton>button { border-radius:7px; font-weight:600; font-size:12px; }
.stTextInput>div>div>input { background:#0a0a18 !important; color:#e2e8f0 !important; border-color:#1e1e3a !important; }
.stNumberInput>div>div>input { background:#0a0a18 !important; color:#e2e8f0 !important; font-family:'IBM Plex Mono',monospace !important; }
.stSelectbox>div>div { background:#0a0a18 !important; color:#e2e8f0 !important; }
.stTextArea>div>div>textarea { background:#0a0a18 !important; color:#e2e8f0 !important; }
.stTabs [data-baseweb="tab-list"] { background:#0d0d1a; border-bottom:1px solid #1e1e3a; }
.stTabs [data-baseweb="tab"] { color:#64748b; font-weight:600; }
.stTabs [aria-selected="true"] { color:#e2e8f0 !important; border-bottom:2px solid #7c3aed !important; }
#MainMenu {visibility:hidden;} footer {visibility:hidden;}
hr { border-color:#1e1e3a !important; }
</style>
""", unsafe_allow_html=True)

# ─── engine ───────────────────────────────────────────────────────────────────
def new_id(): return str(uuid.uuid4())[:8]

def fmt(v, digits=2):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))): return "–"
    if v == 0: return "0"
    return f"{v:.{digits}e}"

def calc_node(node):
    children = node.get("children", [])
    if not children:
        return node.get("value")
    vals = [calc_node(c) for c in children]
    vals = [v for v in vals if v is not None and math.isfinite(v)]
    if not vals: return node.get("value")
    if node.get("gate", "OR") == "OR":
        return sum(vals)
    else:
        r = 1.0
        for v in vals: r *= v
        return r

def propagate_targets(node, target):
    node = copy.deepcopy(node)
    node["_target"] = target
    children = node.get("children", [])
    if not children: return node
    gate = node.get("gate", "OR")
    n = len(children)
    if gate == "OR":
        child_t = target / n
    else:
        child_t = max(target, 1e-300) ** (1.0 / n)
    node["children"] = [propagate_targets(c, child_t) for c in children]
    return node

def redistribute(tree, mode="equal"):
    sfs = tree.get("children", [])
    if not sfs: return tree
    hazard_t = tree.get("value", 1e-7)
    tree = copy.deepcopy(tree)
    if mode == "equal":
        sf_t = hazard_t / len(sfs)
        for sf in tree["children"]:
            sf["weight"] = 1
            sf["_target"] = sf_t
            ffs = sf.get("children", [])
            ff_t = sf_t / max(len(ffs), 1)
            sf["children"] = [propagate_targets(ff, ff_t) for ff in ffs]
    else:
        total_w = sum(sf.get("weight", 1) for sf in sfs) or 1
        for sf in tree["children"]:
            sf_t = hazard_t * (sf.get("weight", 1) / total_w)
            sf["_target"] = sf_t
            ffs = sf.get("children", [])
            ff_t = sf_t / max(len(ffs), 1)
            sf["children"] = [propagate_targets(ff, ff_t) for ff in ffs]
    return tree

def build_audit_trail(tree):
    """Build step-by-step calculation text matching the blue box in your diagram."""
    lines = []
    hazard_calc = calc_node(tree)
    lines.append(f"{'─'*52}")
    lines.append(f"HAZARD: {tree.get('label','Hazard')}  [gate: {tree.get('gate','OR')}]")
    lines.append(f"Target  : {fmt(tree.get('value'))}")
    lines.append(f"{'─'*52}")
    for sf in tree.get("children", []):
        sf_calc = calc_node(sf)
        sf_ok = "✓" if sf_calc is not None and sf.get("_target") and sf_calc <= sf["_target"]*1.001 else "✗"
        lines.append(f"\n{sf.get('node_id','SF-??')}  {sf.get('label','')}")
        lines.append(f"  gate   : {sf.get('gate','OR')}")
        lines.append(f"  calc   : {fmt(sf_calc)}   target: {fmt(sf.get('_target'))}  {sf_ok}")
        for ff in sf.get("children", []):
            ff_calc = calc_node(ff)
            ff_ok = "✓" if ff_calc is not None and ff.get("_target") and ff_calc <= ff["_target"]*1.001 else "✗"
            lines.append(f"  ├─ {ff.get('node_id','FF-??')}  {ff.get('label','')}")
            lines.append(f"  │   gate: {ff.get('gate','OR')}  calc: {fmt(ff_calc)}  tgt: {fmt(ff.get('_target'))}  {ff_ok}")
            for ifn in ff.get("children", []):
                lines.append(f"  │   └─ {ifn.get('node_id','IF-??')}  {ifn.get('label','')}  P={fmt(ifn.get('value'))}")
    lines.append(f"\n{'─'*52}")
    lines.append(f"TOTAL CALCULATED : {fmt(hazard_calc)}")
    lines.append(f"HAZARD TARGET    : {fmt(tree.get('value'))}")
    if hazard_calc is not None and tree.get("value"):
        pct = hazard_calc / tree["value"] * 100
        lines.append(f"BUDGET USED      : {pct:.1f}%  {'✓ WITHIN TARGET' if pct<=100 else '✗ EXCEEDS TARGET'}")
    return "\n".join(lines)

# ─── factories ────────────────────────────────────────────────────────────────
_sf_counter = [0]
_ff_counter = [0]
_if_counter = [0]

def make_if(node_id=None, label="Initial Failure", value=1e-5):
    _if_counter[0] += 1
    nid = node_id or f"IF-{_if_counter[0]:03d}"
    return {"id": new_id(), "type": "IF", "node_id": nid, "label": label,
            "value": value, "children": [], "gate": "OR", "note": "", "flag": "none"}

def make_ff(node_id=None, label="Following Failure"):
    _ff_counter[0] += 1
    nid = node_id or f"FF-{_ff_counter[0]:02d}"
    return {"id": new_id(), "type": "FF", "node_id": nid, "label": label,
            "gate": "OR", "children": [make_if(), make_if()], "value": None,
            "note": "", "flag": "none"}

def make_sf(node_id=None, label="System Failure"):
    _sf_counter[0] += 1
    nid = node_id or f"SF-{_sf_counter[0]:02d}"
    return {"id": new_id(), "type": "SF", "node_id": nid, "label": label,
            "gate": "OR", "weight": 1,
            "children": [make_ff(), make_ff(), make_ff()],
            "value": None, "note": "", "flag": "none"}

def build_default_tree(hazard_id="H-01", hazard_label="Toxic Hazard"):
    _sf_counter[0] = 0; _ff_counter[0] = 0; _if_counter[0] = 0
    tree = {
        "id": new_id(), "type": "HAZARD",
        "node_id": hazard_id, "label": hazard_label,
        "value": 1e-7, "gate": "OR",
        "children": [make_sf(), make_sf(), make_sf()],
        "note": "", "flag": "none"
    }
    return redistribute(tree, "equal")

# ─── session state ────────────────────────────────────────────────────────────
if "project_name" not in st.session_state:
    st.session_state.project_name = "My FTA Project"
if "hazards" not in st.session_state:
    st.session_state.hazards = [build_default_tree("H-01", "Toxic Hazard")]
if "dist_mode" not in st.session_state:
    st.session_state.dist_mode = "equal"
if "active_hazard" not in st.session_state:
    st.session_state.active_hazard = 0

def get_hazards(): return st.session_state.hazards
def set_hazards(h): st.session_state.hazards = h

# ─── helpers ──────────────────────────────────────────────────────────────────
def status_html(calc, target):
    if calc is None or target is None: return ""
    ok = calc <= target * 1.001
    return f'<span class="badge-{"ok" if ok else "over"}">{"✓ OK" if ok else "✗ OVER"}</span>'

def gate_html(gate):
    cls = "badge-gate-or" if gate == "OR" else "badge-gate-and"
    return f'<span class="{cls}">{gate}</span>'

def flag_html(flag):
    if flag == "tbc":    return '<span class="note-tbc">TBC</span>'
    if flag == "reword": return '<span class="note-reword">REWORD</span>'
    if flag == "ok":     return '<span class="note-ok">CONFIRMED</span>'
    return ""

FLAG_OPTIONS = {"none": "—", "ok": "✓ Confirmed", "tbc": "TBC", "reword": "Reword Required"}

# ─── sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚠ FTA Tool v2")
    st.divider()

    st.session_state.project_name = st.text_input("Project Name", value=st.session_state.project_name)

    st.markdown("**Distribution Mode**")
    new_mode = st.radio("", ["equal", "weighted"],
                         index=0 if st.session_state.dist_mode == "equal" else 1,
                         horizontal=True, key="sidebar_dist")
    if new_mode != st.session_state.dist_mode:
        st.session_state.dist_mode = new_mode
        hazards = get_hazards()
        for i, h in enumerate(hazards):
            hazards[i] = redistribute(h, new_mode)
        set_hazards(hazards)
        st.rerun()

    if st.session_state.dist_mode == "equal":
        st.caption("Each SF gets equal share of hazard budget")
    else:
        st.caption("Budget split by SF weight")

    st.divider()

    # ── Add hazard ──
    st.markdown("**Hazards in Project**")
    hazards = get_hazards()
    for i, h in enumerate(hazards):
        hcalc = calc_node(h)
        hok = hcalc is not None and hcalc <= h["value"] * 1.001
        indicator = "🟢" if hok else "🔴"
        if st.button(f"{indicator} {h['node_id']} — {h['label']}", key=f"nav_{i}",
                     use_container_width=True):
            st.session_state.active_hazard = i
            st.rerun()

    if st.button("➕ Add New Hazard", use_container_width=True):
        n = len(hazards) + 1
        _sf_counter[0] = 0; _ff_counter[0] = 0; _if_counter[0] = 0
        new_h = build_default_tree(f"H-{n:02d}", f"Hazard {n}")
        hazards.append(new_h)
        set_hazards(hazards)
        st.session_state.active_hazard = len(hazards) - 1
        st.rerun()

    st.divider()

    # ── Save / Load ──
    st.markdown("**Save / Load**")
    save_data = json.dumps({
        "project": st.session_state.project_name,
        "saved_at": datetime.now().isoformat(),
        "dist_mode": st.session_state.dist_mode,
        "hazards": get_hazards(),
    }, indent=2)
    st.download_button("💾 Save Project (JSON)", data=save_data,
                       file_name=f"{st.session_state.project_name.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                       mime="application/json", use_container_width=True)

    uploaded = st.file_uploader("📂 Load Project", type="json", label_visibility="collapsed")
    if uploaded:
        try:
            data = json.load(uploaded)
            set_hazards(data["hazards"])
            st.session_state.dist_mode = data.get("dist_mode", "equal")
            st.session_state.project_name = data.get("project", "Loaded Project")
            st.session_state.active_hazard = 0
            st.success("Loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    st.divider()

    # ── Export CSV ──
    if st.button("📊 Export All to CSV", use_container_width=True):
        rows = []
        for h in get_hazards():
            h_calc = calc_node(h)
            for sf in h.get("children", []):
                sf_calc = calc_node(sf)
                for ff in sf.get("children", []):
                    ff_calc = calc_node(ff)
                    for ifn in ff.get("children", []):
                        rows.append({
                            "Hazard_ID": h["node_id"], "Hazard": h["label"],
                            "Hazard_Target": h["value"], "Hazard_Calc": h_calc,
                            "SF_ID": sf["node_id"], "SF_Label": sf["label"],
                            "SF_Gate": sf["gate"], "SF_Calc": sf_calc, "SF_Target": sf.get("_target"),
                            "FF_ID": ff["node_id"], "FF_Label": ff["label"],
                            "FF_Gate": ff["gate"], "FF_Calc": ff_calc, "FF_Target": ff.get("_target"),
                            "IF_ID": ifn["node_id"], "IF_Label": ifn["label"],
                            "IF_Value": ifn.get("value"), "IF_Target": ifn.get("_target"),
                            "IF_Flag": ifn.get("flag", ""), "IF_Note": ifn.get("note", ""),
                        })
        if rows:
            df = pd.DataFrame(rows)
            st.download_button("⬇ Download CSV", df.to_csv(index=False),
                               file_name=f"{st.session_state.project_name}_export.csv",
                               mime="text/csv", use_container_width=True)

    st.divider()
    with st.expander("ℹ️ Help"):
        st.markdown("""
**Node IDs**: Edit inline (SF-01, FF-42, IF-100)
**Gates**: OR = sum · AND = product
**Flags**: Mark nodes as TBC / Reword / Confirmed
**Targets**: Flow top-down from hazard target
**Calc**: Bottom-up from IF values you enter
**Green ✓** = within budget · **Red ✗** = over
        """)

# ─── main area ────────────────────────────────────────────────────────────────
hazards = get_hazards()
if not hazards:
    st.warning("No hazards yet. Add one from the sidebar.")
    st.stop()

idx = min(st.session_state.active_hazard, len(hazards) - 1)
tree = hazards[idx]

st.markdown(f"## ⚠ {st.session_state.project_name}")

# ── tabs: Editor / Audit Trail ──
tab_editor, tab_audit = st.tabs(["🌲 Tree Editor", "🧮 Calculation Audit"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: EDITOR
# ═══════════════════════════════════════════════════════════════════════════════
with tab_editor:
    tree_changed = False

    # ── HAZARD CARD ────────────────────────────────────────────────────────────
    hazard_calc = calc_node(tree)
    hazard_ok = hazard_calc is not None and hazard_calc <= tree["value"] * 1.001

    st.markdown('<div class="hazard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">HAZARD</div>', unsafe_allow_html=True)

    hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([1, 2, 1.5, 1.2, 1.5, 1])
    with hc1:
        new_nid = st.text_input("ID", value=tree.get("node_id","H-01"), key="h_nid", label_visibility="visible")
        if new_nid != tree.get("node_id"):
            tree["node_id"] = new_nid; tree_changed = True
    with hc2:
        new_lbl = st.text_input("Hazard Label", value=tree.get("label",""), key="h_lbl", label_visibility="visible")
        if new_lbl != tree.get("label"):
            tree["label"] = new_lbl; tree_changed = True
    with hc3:
        new_val = st.number_input("Target P", value=float(tree.get("value",1e-7)), format="%.2e", step=1e-8, key="h_val", label_visibility="visible")
        if abs(new_val - tree.get("value",1e-7)) > 1e-20:
            tree["value"] = new_val; tree_changed = True
    with hc4:
        gate_opts = ["OR","AND"]
        hgate = st.selectbox("Gate", gate_opts, index=gate_opts.index(tree.get("gate","OR")), key="h_gate", label_visibility="visible")
        if hgate != tree.get("gate"):
            tree["gate"] = hgate; tree_changed = True
    with hc5:
        color = "ok-color" if hazard_ok else "over-color"
        badge = status_html(hazard_calc, tree["value"])
        st.markdown(f'<div style="margin-top:24px"><span class="big-metric {color}">{fmt(hazard_calc)}</span> {badge}</div>', unsafe_allow_html=True)
        if hazard_calc and tree["value"]:
            pct = hazard_calc/tree["value"]*100
            pc = "ok-color" if pct<=100 else "over-color"
            st.markdown(f'<span class="mono muted-color" style="font-size:11px">budget: <span class="{pc}">{pct:.1f}%</span></span>', unsafe_allow_html=True)
    with hc6:
        new_flag = st.selectbox("Flag", list(FLAG_OPTIONS.keys()),
                                format_func=lambda x: FLAG_OPTIONS[x],
                                index=list(FLAG_OPTIONS.keys()).index(tree.get("flag","none")),
                                key="h_flag", label_visibility="visible")
        if new_flag != tree.get("flag"):
            tree["flag"] = new_flag; tree_changed = True

    h_note = st.text_input("Notes", value=tree.get("note",""), key="h_note", placeholder="Optional notes...", label_visibility="visible")
    if h_note != tree.get("note"):
        tree["note"] = h_note; tree_changed = True

    # stats row
    sfs = tree.get("children",[])
    ff_total = sum(len(sf.get("children",[])) for sf in sfs)
    if_total = sum(len(ff.get("children",[])) for sf in sfs for ff in sf.get("children",[]))
    st.markdown(f"""
    <div style="display:flex;gap:24px;margin-top:10px;padding-top:10px;border-top:1px solid #1e1e3a">
      <span class="mono" style="font-size:11px;color:#475569">SFs: <strong style="color:#38bdf8">{len(sfs)}</strong></span>
      <span class="mono" style="font-size:11px;color:#475569">FFs: <strong style="color:#4ade80">{ff_total}</strong></span>
      <span class="mono" style="font-size:11px;color:#475569">IFs: <strong style="color:#fbbf24">{if_total}</strong></span>
      <span class="mono" style="font-size:11px;color:#475569">Mode: <strong style="color:#a78bfa">{st.session_state.dist_mode.upper()}</strong></span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── action buttons ─────────────────────────────────────────────────────────
    ba1, ba2, ba3, ba4 = st.columns([2,2,2,2])
    with ba1:
        if st.button("➕ Add System Failure", type="primary", use_container_width=True):
            _sf_counter[0] = max(int(sf.get("node_id","SF-00").split("-")[-1]) for sf in sfs) if sfs else 0
            tree["children"].append(make_sf())
            st.session_state.dist_mode = "equal"
            tree = redistribute(tree, "equal")
            hazards[idx] = tree; set_hazards(hazards)
            st.rerun()
    with ba2:
        if st.button("🔄 Recalculate Targets", use_container_width=True):
            tree = redistribute(tree, st.session_state.dist_mode)
            hazards[idx] = tree; set_hazards(hazards)
            st.rerun()
    with ba3:
        if st.button("🗑 Delete This Hazard", use_container_width=True):
            if len(hazards) > 1:
                hazards.pop(idx)
                st.session_state.active_hazard = max(0, idx-1)
                set_hazards(hazards)
                st.rerun()
            else:
                st.warning("Cannot delete the last hazard.")
    with ba4:
        if st.button("↔ Switch to Weighted" if st.session_state.dist_mode=="equal" else "↔ Switch to Equal",
                     use_container_width=True):
            new_m = "weighted" if st.session_state.dist_mode=="equal" else "equal"
            st.session_state.dist_mode = new_m
            tree = redistribute(tree, new_m)
            hazards[idx] = tree; set_hazards(hazards)
            st.rerun()

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # SF LOOP
    # ══════════════════════════════════════════════════════════════════════════
    sfs = tree.get("children", [])
    for sf_idx, sf in enumerate(sfs):
        sf_calc = calc_node(sf)
        sf_ok = sf_calc is not None and sf.get("_target") and sf_calc <= sf["_target"]*1.001
        sf_pct = f"{sf_calc/sf['_target']*100:.0f}%" if sf_calc and sf.get("_target") else ""

        with st.expander(
            f"{'🟢' if sf_ok else '🔴'}  {sf.get('node_id','SF-??')}  ·  {sf.get('label','')}  "
            f"·  calc: {fmt(sf_calc)}  ·  target: {fmt(sf.get('_target'))}  {sf_pct}",
            expanded=True
        ):
            st.markdown('<div class="sf-card">', unsafe_allow_html=True)

            # SF header
            sfc1,sfc2,sfc3,sfc4,sfc5,sfc6,sfc7 = st.columns([1,2.5,1.2,1.2,1.2,1.5,0.6])
            with sfc1:
                new_sf_nid = st.text_input("ID", value=sf.get("node_id",""), key=f"sf_nid_{sf['id']}", label_visibility="visible")
                if new_sf_nid != sf.get("node_id"): sfs[sf_idx]["node_id"]=new_sf_nid; tree_changed=True
            with sfc2:
                new_sf_lbl = st.text_input("Label", value=sf.get("label",""), key=f"sf_lbl_{sf['id']}", label_visibility="visible")
                if new_sf_lbl != sf.get("label"): sfs[sf_idx]["label"]=new_sf_lbl; tree_changed=True
            with sfc3:
                sf_gate = st.selectbox("Gate", ["OR","AND"], index=0 if sf.get("gate","OR")=="OR" else 1, key=f"sf_gate_{sf['id']}", label_visibility="visible")
                if sf_gate != sf.get("gate"): sfs[sf_idx]["gate"]=sf_gate; tree_changed=True
            with sfc4:
                if st.session_state.dist_mode == "weighted":
                    new_w = st.number_input("Weight", value=float(sf.get("weight",1)), min_value=0.01, step=0.1, key=f"sf_w_{sf['id']}", label_visibility="visible")
                    if new_w != sf.get("weight"): sfs[sf_idx]["weight"]=new_w; tree_changed=True
                else:
                    st.markdown('<div style="margin-top:24px"><span class="mono muted-color" style="font-size:11px">weight: 1</span></div>', unsafe_allow_html=True)
            with sfc5:
                sf_flag = st.selectbox("Flag", list(FLAG_OPTIONS.keys()), format_func=lambda x:FLAG_OPTIONS[x],
                                       index=list(FLAG_OPTIONS.keys()).index(sf.get("flag","none")),
                                       key=f"sf_flag_{sf['id']}", label_visibility="visible")
                if sf_flag != sf.get("flag"): sfs[sf_idx]["flag"]=sf_flag; tree_changed=True
            with sfc6:
                color = "ok-color" if sf_ok else "over-color"
                st.markdown(f'<div style="margin-top:24px"><span class="prob-value {color}">{fmt(sf_calc)}</span><br><span class="prob-target">tgt: {fmt(sf.get("_target"))}</span></div>', unsafe_allow_html=True)
            with sfc7:
                st.markdown('<div style="margin-top:24px">', unsafe_allow_html=True)
                if st.button("🗑", key=f"del_sf_{sf['id']}", help="Delete SF"):
                    tree["children"] = [s for s in sfs if s["id"]!=sf["id"]]
                    tree = redistribute(tree, st.session_state.dist_mode)
                    hazards[idx]=tree; set_hazards(hazards); st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            sf_note = st.text_input("SF Note", value=sf.get("note",""), key=f"sf_note_{sf['id']}", placeholder="Notes...", label_visibility="collapsed")
            if sf_note != sf.get("note"): sfs[sf_idx]["note"]=sf_note; tree_changed=True

            st.markdown("---")

            # ══════════════════════════════════════════════════════════════════
            # FF LOOP
            # ══════════════════════════════════════════════════════════════════
            ffs = sf.get("children", [])
            for ff_idx, ff in enumerate(ffs):
                ff_calc = calc_node(ff)
                ff_ok = ff_calc is not None and ff.get("_target") and ff_calc <= ff["_target"]*1.001

                st.markdown('<div class="ff-card">', unsafe_allow_html=True)
                ffc1,ffc2,ffc3,ffc4,ffc5,ffc6,ffc7 = st.columns([1,2.5,1.2,1.2,1.5,1.5,0.6])
                with ffc1:
                    new_ff_nid = st.text_input("ID", value=ff.get("node_id",""), key=f"ff_nid_{ff['id']}", label_visibility="visible")
                    if new_ff_nid != ff.get("node_id"): sfs[sf_idx]["children"][ff_idx]["node_id"]=new_ff_nid; tree_changed=True
                with ffc2:
                    new_ff_lbl = st.text_input("Label", value=ff.get("label",""), key=f"ff_lbl_{ff['id']}", label_visibility="visible")
                    if new_ff_lbl != ff.get("label"): sfs[sf_idx]["children"][ff_idx]["label"]=new_ff_lbl; tree_changed=True
                with ffc3:
                    ff_gate = st.selectbox("Gate", ["OR","AND"], index=0 if ff.get("gate","OR")=="OR" else 1, key=f"ff_gate_{ff['id']}", label_visibility="visible")
                    if ff_gate != ff.get("gate"): sfs[sf_idx]["children"][ff_idx]["gate"]=ff_gate; tree_changed=True
                with ffc4:
                    ff_flag = st.selectbox("Flag", list(FLAG_OPTIONS.keys()), format_func=lambda x:FLAG_OPTIONS[x],
                                           index=list(FLAG_OPTIONS.keys()).index(ff.get("flag","none")),
                                           key=f"ff_flag_{ff['id']}", label_visibility="visible")
                    if ff_flag != ff.get("flag"): sfs[sf_idx]["children"][ff_idx]["flag"]=ff_flag; tree_changed=True
                with ffc5:
                    color = "ok-color" if ff_ok else "over-color"
                    st.markdown(f'<span class="badge-ff">FF</span> <span class="prob-value {color}">{fmt(ff_calc)}</span><br><span class="prob-target">tgt: {fmt(ff.get("_target"))}</span>', unsafe_allow_html=True)
                with ffc6:
                    if st.button(f"➕ Add IF", key=f"add_if_{ff['id']}", use_container_width=True):
                        n = len(ff.get("children",[]))
                        sfs[sf_idx]["children"][ff_idx]["children"].append(make_if(label=f"Initial Failure {n+1}"))
                        tree_changed = True
                with ffc7:
                    if st.button("🗑", key=f"del_ff_{ff['id']}", help="Delete FF"):
                        sfs[sf_idx]["children"] = [f for f in ffs if f["id"]!=ff["id"]]
                        tree_changed = True

                ff_note = st.text_input("FF Note", value=ff.get("note",""), key=f"ff_note_{ff['id']}", placeholder="Notes...", label_visibility="collapsed")
                if ff_note != ff.get("note"): sfs[sf_idx]["children"][ff_idx]["note"]=ff_note; tree_changed=True

                # ══════════════════════════════════════════════════════════════
                # IF LOOP
                # ══════════════════════════════════════════════════════════════
                ifs = ff.get("children", [])
                if ifs:
                    n_cols = min(len(ifs), 3)
                    if_cols = st.columns(n_cols)
                    for if_idx, ifn in enumerate(ifs):
                        with if_cols[if_idx % n_cols]:
                            st.markdown('<div class="if-card">', unsafe_allow_html=True)

                            ifc1, ifc2 = st.columns([1,0.3])
                            with ifc1:
                                new_if_nid = st.text_input("ID", value=ifn.get("node_id",""), key=f"if_nid_{ifn['id']}", label_visibility="visible")
                                if new_if_nid != ifn.get("node_id"):
                                    sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["node_id"]=new_if_nid; tree_changed=True
                            with ifc2:
                                st.markdown('<div style="margin-top:24px">', unsafe_allow_html=True)
                                if st.button("✕", key=f"del_if_{ifn['id']}", help="Delete IF"):
                                    sfs[sf_idx]["children"][ff_idx]["children"] = [i for i in ifs if i["id"]!=ifn["id"]]
                                    tree_changed = True
                                st.markdown('</div>', unsafe_allow_html=True)

                            new_if_lbl = st.text_input("Label", value=ifn.get("label",""), key=f"if_lbl_{ifn['id']}", label_visibility="visible")
                            if new_if_lbl != ifn.get("label"):
                                sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["label"]=new_if_lbl; tree_changed=True

                            new_if_val = st.number_input("P =", value=float(ifn.get("value") or 1e-5),
                                                          format="%.2e", step=1e-6,
                                                          key=f"if_val_{ifn['id']}", label_visibility="visible")
                            if new_if_val != ifn.get("value"):
                                sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["value"]=new_if_val; tree_changed=True

                            if_flag = st.selectbox("Flag", list(FLAG_OPTIONS.keys()), format_func=lambda x:FLAG_OPTIONS[x],
                                                    index=list(FLAG_OPTIONS.keys()).index(ifn.get("flag","none")),
                                                    key=f"if_flag_{ifn['id']}", label_visibility="collapsed")
                            if if_flag != ifn.get("flag"):
                                sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["flag"]=if_flag; tree_changed=True

                            if ifn.get("_target"):
                                if_ok = new_if_val <= ifn["_target"]*1.001
                                c = "ok-color" if if_ok else "over-color"
                                st.markdown(f'<span class="prob-target">tgt: <span class="{c}">{fmt(ifn["_target"])}</span></span>', unsafe_allow_html=True)

                            if_note = st.text_input("Note", value=ifn.get("note",""), key=f"if_note_{ifn['id']}", placeholder="Notes...", label_visibility="collapsed")
                            if if_note != ifn.get("note"):
                                sfs[sf_idx]["children"][ff_idx]["children"][if_idx]["note"]=if_note; tree_changed=True

                            st.markdown('</div>', unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)  # ff-card

            # add FF button
            aff1, aff2 = st.columns([2,4])
            with aff1:
                if st.button(f"➕ Add Following Failure", key=f"add_ff_{sf['id']}", use_container_width=True):
                    n = len(ffs)
                    _ff_counter[0] = max(int(f.get("node_id","FF-00").split("-")[-1]) for f in ffs) if ffs else 0
                    sfs[sf_idx]["children"].append(make_ff(label=f"Following Failure {n+1}"))
                    tree_changed = True

            st.markdown('</div>', unsafe_allow_html=True)  # sf-card

    # ── apply changes ──────────────────────────────────────────────────────────
    if tree_changed:
        tree["children"] = sfs
        tree = redistribute(tree, st.session_state.dist_mode)
        hazards[idx] = tree
        set_hazards(hazards)
        st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: AUDIT TRAIL
# ═══════════════════════════════════════════════════════════════════════════════
with tab_audit:
    tree = hazards[idx]
    st.markdown("### 🧮 Calculation Audit Trail")
    st.caption("This mirrors the blue calculation box in your FTA diagrams — full step-by-step formula.")

    audit_text = build_audit_trail(tree)
    st.markdown('<div class="audit-card">', unsafe_allow_html=True)
    st.code(audit_text, language=None)
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.markdown("### 📋 Node Summary Table")

    rows = []
    for sf in tree.get("children",[]):
        sf_calc = calc_node(sf)
        for ff in sf.get("children",[]):
            ff_calc = calc_node(ff)
            for ifn in ff.get("children",[]):
                if_val = ifn.get("value")
                if_tgt = ifn.get("_target")
                rows.append({
                    "SF ID": sf.get("node_id",""), "SF Label": sf.get("label",""),
                    "SF Calc": fmt(sf_calc), "SF Target": fmt(sf.get("_target")),
                    "SF OK": "✓" if sf_calc and sf.get("_target") and sf_calc<=sf["_target"]*1.001 else "✗",
                    "FF ID": ff.get("node_id",""), "FF Label": ff.get("label",""),
                    "FF Calc": fmt(ff_calc), "FF Target": fmt(ff.get("_target")),
                    "FF Gate": ff.get("gate","OR"),
                    "IF ID": ifn.get("node_id",""), "IF Label": ifn.get("label",""),
                    "IF Value": fmt(if_val), "IF Target": fmt(if_tgt),
                    "IF OK": "✓" if if_val and if_tgt and if_val<=if_tgt*1.001 else "✗",
                    "Flag": FLAG_OPTIONS.get(ifn.get("flag","none"),""),
                    "Note": ifn.get("note",""),
                })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=400)
        st.download_button("⬇ Download This Hazard CSV",
                           data=df.to_csv(index=False),
                           file_name=f"{tree.get('node_id','hazard')}_audit.csv",
                           mime="text/csv")
    else:
        st.info("No IF nodes yet — add some in the Tree Editor tab.")
