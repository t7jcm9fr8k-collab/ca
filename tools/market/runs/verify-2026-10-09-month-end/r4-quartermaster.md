# R4 · Quartermaster: is the month-end result a data artefact?

**CLEAN.** I found no data artefact, and no plausible data correction would flip a passing gate or rescue G5′. (1) The run read exactly the frozen inputs. (2) The five top cycles contain no defective bar; their big days are real crisis moves. (3) The add-backs removed the price-only bias, in the right direction and at the expected size. (4) The QQQ no-veto does not depend on the 1999-11-16 hole or the 2001-09 closures.

**Method.** I rebuilt the primary cell (2 bp, cash 1.5%, spread 1.5%) with edgelab's own functions; it reproduces the run exactly (Σd 0.70647, top-5 0.42062, z_boot 1.8116, z_used 1.6879, QQQ z_used +0.018). Outputs are in `S/edge/quartermaster/r4/` (verify.txt, verify2.txt, verify3.txt, split.txt, checks.txt), from r4_verify*.py and r4_split.py.

## 1 · Inputs are the frozen files (run l.4–31; checks.txt)
- **Hashes.** G0 passes on both files, and every file on disk hashes to the printed sha256: SPY-1d.csv 52a006de… and QQQ-1d-long.csv 4433bdbc… (both also frozen in the PREREG and invocation.sh); windows-S1-SPY.csv 56de9701… (257 windows reproduced); windows-G7-QQQ.csv 9babdf50… (71); distributions 780a360f…; PREREG 85dede81…; invocation 0ec3dde1….
- **Unchanged since the freeze.** `git diff 3201ce4 HEAD` is empty for the prereg folder, the PREREG and both bar files, and commit 1d9608d adds only the run output. Both window lists and the distributions file are byte-identical to my r2 files.
- **Add-backs placed as frozen.** The run used the five dates and amounts of PREREG l.90–94, with r_t = (close_t + D)/close(t−1) − 1 (PREREG l.96 = the run's PRICES line, l.36). 2025-03-21 is rightly left out: it is stooq's last adjustment step (+30.08 bp), with a median gap to official of 0.00 bp after it (`basis/basis-events.txt`). 2026-09-18 falls after the span.

## 2 · Top-5 positive cycles (59.5% of Σd): no defective bar
- **The cycles (Σd):** #1 2008-10-28..11-21 +0.1506; #2 2008-12-26..2009-01-26 +0.0858; #3 2020-02-25..03-25 +0.0698; #4 2008-11-24..12-24 +0.0585; #5 2008-09-25..10-27 +0.0560.
- **Bar checks.** From each cycle's entry close to its end, no bar has broken OHLC ordering, zero volume, a flat bar, H = L, or a repeated close or volume, and no leg spans a closure or a hole.
- **Cycle #3 against official closes** (the only cycle after 2016-10). The stooq/official ratio steps once, by +58.27 bp on 2020-03-20: SPY's ex-date, outside the 2× window 02-25..03-04, and the same step r1 recorded in basis-events.csv. Every other step is ≤ 1.02 bp. File-wide after 2016-10, the one close spike over 10 bp (2026-04-20) is a nasdaq placeholder; stooq's 708.72 agrees with alpaca's 708.79 (`bars/SPY-1d-agg.csv`).
- **The 2008 cycles** have no official file. They rest on barqc PASS (`barqc/barqc-onDisk-2026-10-09.txt`) and a peer test: SPY regressed on DIA, IWM and QQQ over S1 (residual SD 0.21%), where a bad close shows as a residual that reverses the next day. At these cycles' ten entry and exit closes the largest such reversal is 0.558% (2008-11-05).
- **Only trade closes matter.** Raising one close by 1% in memory moves Σd −0.0098 at an entry close and +0.0092 at an exit close, but exactly 0.000000 at an inside or outside close, because positions are held between trades.
- **Would removing a defective bar change a gate? No.** None was found. The only imperfect bars in S1 (stooq 2018-02-20 with O = L = C, whose close matches official; the 2011-02-17 hole) sit at non-trade closes, where they have no effect. Even treating every peer reversal at all 513 trade closes as a bad close, removing them all moves Σd by +0.013 (second half +0.019), i.e. upward. The margins to beat are Σd +0.183 in the weaker half (G2), +0.706 overall (G1) and +0.286 for the G6 residual. G3's +0.19 drawdown margin also dwarfs the largest reversal anywhere in S1 (1.46%, 2008-10-10).
- **Closure and hole legs.** S1's five such legs carry Σd +0.00085; without them z_used is +1.6860, against +1.6879 with them.
- **Not a data issue, but worth knowing.** Of these cycles' +0.421, +0.319 comes from 1× sessions: crash days outside the window, while (A) held 1.33× (e.g. 2020-03-16, −10.95%, d +0.0518; 2008-11-20, −7.42%, d +0.0342). Over the whole span the 1× sessions net +0.006 and the 2× sessions +0.700 (split.txt).

## 3 · The price-only stretch and the add-backs (verify.txt, checks.txt)
- **Contribution.** 2025-03-24..2026-08-25 (358 sessions) contributes Σd +0.02272 of +0.70647 (3.2%). The five ex-dates themselves contribute −0.00208 with the add-backs and +0.00264 without.
- **The bias is removed.** All five ex-dates fall at e = 1 while (A) holds about 1.33×, so without the add-back each price-only drop charges (A) more and inflates S1 − A. The add-backs lower Σd by 0.00468 (about −2.3 bp/yr of the CAGR gap); by date −0.00099, −0.00089, −0.00098, −0.00099 and −0.00086, each within 10% of the first-order −p̂·D/P. No payout inside the span is left out, and at 0.7% of Σd the verdict does not depend on it.

## 4 · The QQQ veto span (verify2.txt, verify3.txt)
- **Reproduced.** z_used +0.018 holds at all six 2 bp pairs (+0.0178 to +0.0184). All three gap legs fall at e = 1: 1999-11-15→17, the data hole (d −0.00342); 2001-09-10→17, the closures (d +0.03166); 2004-06-10→14, a closure (d +0.00473).
- **Removing the legs.** Dropping the hole leg alone gives z = +0.025; dropping the 9/11 leg alone gives −0.049. The lowest z over all 8 subsets of the legs at all 6 pairs is −0.0573. The veto needs z < −1, so neither the hole nor the closures drive the no-veto.

## Not verified
- **Closes before 2016-10** have no official reference, only barqc, internal checks and the peer test. These bound an isolated bad close but cannot detect a close convention shared by the whole vendor file (the 16:00 auction versus a later print); such an error would enter only at trade closes, at about its own size.
- **The add-back amounts** are graded V-sec (PREREG l.338).
