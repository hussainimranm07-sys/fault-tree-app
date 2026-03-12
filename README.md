# ⚠ Fault Tree Analyser — Streamlit App

A full Fault Tree Analysis (FTA) tool built with Python + Streamlit.

## Structure
```
Hazard Target
└── System Failure (SF)  [OR / AND gate]
    └── Following Failure (FF)  [OR / AND gate]
        └── Initial Failure (IF)  [probability value]
```

## Features
- Set a Hazard target probability (e.g. 1e-7)
- Auto-distributes budget top-down: Hazard → SF → FF → IF
- **Equal mode**: every SF gets equal share of hazard budget
- **Weighted mode**: SFs get budget proportional to their weight
- Adding a new SF always resets to equal distribution
- OR / AND gate logic at every level
- ✓ / ✗ status at every node vs target
- Save project to JSON, load it back anytime
- Export summary to CSV

## Run locally

```bash
pip install -r requirements.txt
streamlit run fault_tree.py
```

## Deploy to Streamlit Cloud (free)

1. Push this folder to a GitHub repo
2. Go to https://share.streamlit.io
3. Click **New app** → select your repo → set `fault_tree.py` as the main file
4. Click **Deploy** — done!

## File structure
```
fault_tree_app/
├── fault_tree.py       ← main app
├── requirements.txt    ← dependencies
└── README.md           ← this file
```

## Saving your work
- Click **💾 Save / Download JSON** in the sidebar to save your current tree
- Click **📂 Load JSON** to restore a saved project
- All saved JSONs include project name, date, and full tree structure
