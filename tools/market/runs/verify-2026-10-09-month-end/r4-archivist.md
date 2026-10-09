**MATCHES** — every requested number, to at least 8 significant figures; all differences are below 1e-8.

**Method.** `S/edge/archivist/recompute.py` → `recompute.txt`.
- Stdlib only (csv, datetime, json, math). It imports no repo module. I did not read edgelab's code.
- Inputs: SPY-1d.csv rows through 2026-08-25 (SHA-256 52a006de…, as frozen); the 257 `complete=True` rows of windows-S1-SPY.csv; the five frozen add-backs.
- The run's values are read from the JSON in runs/edgelab-2026-10-09-month-end.txt: cell 0, 2 bp, c 1.5%, s 1.5%.
- Structure check: 5,387 sessions, 1,796 at 2×, p̂ = 1 + 1796/5387 = 1.3333952107, 513 change closes plus the start. Session 2,694 = 2015-12-07.

| quantity | mine | run | within tolerance |
|---|---|---|---|
| CAGR S1 / (A) / B&H | 16.133494 / 12.365862 / 10.561689 % | identical | yes (1 bp) |
| maxDD S1 / (A) / B&H | −54.660177 / −69.048644 / −56.473288 % | identical | yes (0.1 pt) |
| half 1 (→ 2015-12-07) S1 / (A) / B&H | 12.103806 / 6.755205 / 6.479957 % | identical | yes |
| half 2 (2015-12-07 →) S1 / (A) / B&H | 20.303692 / 18.265203 / 14.795475 % | identical | yes |
| d mean (×252) / tracking error (×√252) | +3.304799 %/yr / 9.044028 % | identical | yes |
| d analytic z | 1.687874 | 1.687874 | yes (0.02) |

**Also identical:**
- final equities 24.62923071 / 12.15168168 / 8.59118583;
- cost paid S1 0.60599317, (A) 0.00360888;
- financing paid S1 1.27055582, (A) 0.66888947;
- d's skew 0.032484, kurtosis 19.725430, sum 0.70646641;
- CAGR(S1) − CAGR(A) = 3.76763%.

**Conventions the round-4 brief left open.** I found each one from the run's own diagnostics and flipped each alone (`recompute.txt`, SENSITIVITY):
1. **Opening purchase.** Capital is 1.0 before the opening buy, which pays 2 bp on its notional (B&H's printed cost_paid of 0.0002 shows this). Without that cost, CAGRs rise by 0.1–0.2 bp/yr and z by 0.0003.
2. **Cost timing.** A change-close's cost is booked after that close's mark, so it lands in the next leg. Booking it into the mark moves S1's maxDD to −54.669% (0.009 pt; the trough, 2008-10-27, is an entry close), the tracking error to 9.0466% and z to 1.6874.
3. **(A)'s target.** The run uses the unrounded p̂. The brief's 1.333395 changes (A)'s final equity by 2.7e-6, which is invisible at printed precision.
4. **Year length.** CAGR uses calendar days/365.25: the run's 21.4209446 years = 7,824/365.25. Days/365 would lower every CAGR by about 1.2 bp/yr, the only flip that would break the 1 bp tolerance.
5. **Annualising d.** d's mean and tracking error use ×252 and ×√252. Dividing the sum by calendar years instead gives 3.298%/yr. This is labelling, not substance.

**What this establishes.**
- Given the frozen inputs, the run's three books, its halves, its drawdowns and the timing book's mean, tracking error and analytic z are arithmetically right.
- G1–G3 and the analytic leg of G5′ therefore rest on correct numbers.
- G5′ fails on z_used = 1.688 (the analytic z, the smaller of the two) against the 3.03 bar.

**What it does not establish.**
- Not recomputed (not asked): the bootstrap z (1.812), the placebo p (0.0112), G6, G7′ and the descriptive spans. The check also shares its inputs with the run (bar file, window list, add-back amounts), so an error in those would be reproduced here, not caught.

**Side note.** The realised tracking error of d (9.04%) matches the round-2 prediction σ√(p(1−p)) = 9.05% (`archivist/estimates_r2.txt` §2). The outcome — G4 passes and G5′ fails, giving PARTIAL — is the one `r2-archivist.md` §3.5 named as most likely if G4 passed.
