from pathlib import Path

def write_svg(filename, title, subtitle, color, extra):
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <rect width="1920" height="1080" fill="#020617" />
  <rect width="1920" height="80" fill="#0f172a" stroke="#334155" stroke-width="1" />
  <circle cx="50" cy="40" r="18" fill="#38bdf8" />
  <text x="50" y="46" font-family="sans-serif" font-size="18" font-weight="900" fill="#ffffff" text-anchor="middle">L</text>
  <text x="85" y="46" font-family="sans-serif" font-size="22" font-weight="700" fill="#ffffff">Lienmark</text>
  <text x="195" y="46" font-family="sans-serif" font-size="16" fill="#94a3b8">— Clearance Change Control for E&amp;O</text>
  <rect x="1320" y="24" width="220" height="32" rx="16" fill="#1e293b" stroke="#0ea5e9" stroke-width="1.5" />
  <text x="1430" y="45" font-family="monospace" font-size="13" font-weight="600" fill="#38bdf8" text-anchor="middle">POLICY: E&amp;O-2026.1-DEVPOST</text>
  <rect x="1560" y="24" width="160" height="32" rx="16" fill="#0f172a" stroke="{color}" stroke-width="1.5" />
  <text x="1640" y="45" font-family="sans-serif" font-size="13" font-weight="600" fill="{color}" text-anchor="middle">{subtitle}</text>
  <rect x="60" y="110" width="1800" height="110" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1" />
  <text x="90" y="150" font-family="sans-serif" font-size="14" font-weight="600" fill="#38bdf8">AGENTIC CINEMA SUBMISSION EVIDENCE</text>
  <text x="90" y="190" font-family="sans-serif" font-size="28" font-weight="700" fill="#ffffff">{title}</text>
  <rect x="60" y="240" width="1800" height="780" rx="12" fill="#0f172a" stroke="#334155" stroke-width="1" />
  <text x="960" y="600" font-family="sans-serif" font-size="24" font-weight="700" fill="#94a3b8" text-anchor="middle">{extra}</text>
</svg>"""
    Path("docs/assets/screenshots/" + filename).write_text(svg, encoding="utf-8")
    print(f"Wrote {filename}")

write_svg("dashboard_v7_baseline.svg", "Shadows Over Broadway — Version 7 Baseline (12 Decisions Approved)", "BASELINE LOCKED", "#10b981", "12 / 12 Baseline Clearance Decisions Carried Forward in Locked State")
write_svg("dashboard_v8_drift.svg", "Version 7 -> Version 8 Drift Analysis (10 Carried, 2 Reopened, 83.3% Saved)", "DRIFT DETECTED", "#ef4444", "10 Carried Forward | 2 Reopened (Creative & External Evidence Drift) | 2 Parallel Calls")
write_svg("counsel_checkpoint_modal.svg", "Counsel Clearance Checkpoint — Sarah Jenkins, Esq. (California Bar #284910)", "CHECKPOINT ACTIVE", "#38bdf8", "4-Dimensional Legal Reason Matrix: Creative Context, Parallel Grounding, Contract, Statute")
write_svg("form_eo_2026_schedule.svg", "Form E&O-2026 Underwriting Exceptions Schedule (12 = 10 + 1 + 1 Conservation Law)", "SCHEDULE CERTIFIED", "#22c55e", "10 Carried Forward + 1 Re-Attested (17 U.S.C. 304) + 1 Unresolved Exception | SHA-256 Chained")
