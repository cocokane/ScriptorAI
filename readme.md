# Scriptor.ai Roadmap

## Phase 1: Interactive Semantic Exploration
**Core Features**  
- **Smart Heatmaps**:  
  Highlight sections by topic using preset color palettes (e.g., blues, reds, greens). Relevance intensity scales from light (low) to dark (high).  
- **Instant Summaries**:  
  For sections with >90% relevance score, display AI-generated summaries in 4-5 words (e.g., *"Proposes AlphaFold model for protein folding"*).  
- **DOI-to-Paper**:  
  Enter a DOI to auto-fetch open-access PDFs with preserved formatting.  

**Example Workflow**  
1. Upload a CRISPR research paper.  
2. Search for `off-target effects` (assigned to **blue** palette).  
3. Dark blue highlights appear on pages discussing error rates.  
4. Hover over a dense section: *"CRISPR-Cas9 reduces errors by 62% (vs. prior 40%)"*.  

---

## Phase 2: Structured Knowledge Assembly  
**Core Features**  
- **Drag-and-Drop Guides**:  
  Organize highlights/images into study guides. Rearrange blocks to match your narrative flow.  
- **Auto-Citation**:  
  Exported sections include original paper citations. For a particular section snippet, if there is a citation, it will be picked up and added automatically (e.g., *"Source: Zhang et al. 2023, p.12"*).  
- **Multi-Format Export**:  
  Save as Markdown (for notes) or LaTeX-ready PDF (for academic reuse).  

**Example Workflow**  
1. Select 5 highlights from a quantum computing paper.  
2. Drag a qubit diagram into position 3.  
3. Export as PDF with headings: *"Problem → Methods → Results"*.  

---

## Phase 3: Review Paper Synthesis  
**Core Features**  
- **Multi-Paper Compilation**:  
  Select 10-50 papers from your library. Extract key claims/figures by theme (e.g., *"error correction methods"*).  
- **AI-Powered Narrative**:  
  Auto-generate a review paper with logical flow. Original text is preserved; AI adds transitions like *"Building on X, Y demonstrates..."*.  
- **Conflict Detection**:  
  Flag contradictory findings (e.g., *"Paper A claims 95% accuracy vs Paper B's 82%"*).  

**Example Workflow**  
1. Choose 20 papers on *"mRNA vaccine stability"*.  
2. Compile sections tagged `lyophilization` and `temperature response`.  
3. Generate PDF with:  
   - Section 1: *"Lyophilization Advances (2020-2023)"*  
   - Section 2: *"Contested Optimal Storage Temperatures"*  

---
