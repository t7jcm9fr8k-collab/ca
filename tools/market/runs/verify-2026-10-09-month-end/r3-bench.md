# Bench, after the freeze: the rule registered, read() built, the invocation checked

*`S` = `/tmp/claude-0/-home-user-ca/2758dbcb-e96c-587b-81c2-e59b0c402304/scratchpad`. Outputs are in `S/edge/bench/r3/` and `S/edge/bench/mut/`. No real bar file was read or run, and nothing is committed.*

## What changed

The diff is uncommitted, against HEAD 3201ce4 (the same as e898022 for these files): `tools/market/edgelab.py` and `tools/market/test_edgelab.py`, 2 files, +587 / −20. The SHA-256s are in `bench/r3/build-hashes.txt`.

1. **The registered rule.** `month_end_overlay` sits under PRE-REGISTERED RULES.
   - It is `month_window_rule(-3, 3, inside=2.0, outside=1.0, model="margin")`, named month_end_overlay.
   - Its doc string cites `PREREG-2026-10-09-month-end.md`, SHA-256 85dede81…943fa1f, and commit 3201ce4.
   - The only other change to `month_window_rule` is an optional `doc` argument.
2. **The frozen reading rule.** `FROZEN["month_end_overlay"]` holds every number of the reading rule, copied from the prereg.
3. **`read(r, v, spec)`.** It applies the frozen reading rule exactly:
   - Gates G1–G7′ are read at the six gated pairs at 2 bp; G1 is also read at 5 bp, and G7′ on the replication file.
   - G5′ is computed from z_used as Φ(z − E[max Z_N]) at N = 40, with the flip checked at N = 100.
   - The verdict is VOID, WORKS, PARTIAL — DO NOT TRADE, or NULL. Every failed gate is printed with its reason, verbatim from the prereg's table.
   - `render_verdict` prints the verdict after the gates and before the descriptives.
   - The JSON output carries the verdict.
4. **G0 now enforces "run verbatim".** `frozen_conformance` is computed from the integrity-only runs, so a failure means nothing price-based is computed or printed. It requires:
   - the command line equals `prereg-2026-10-09/invocation.sh`, token for token;
   - that file's SHA-256 is 0ec3dde1…;
   - `--prereg`'s SHA-256 is 85dede81…;
   - the frozen window facts hold:
     - S1: 5,387 sessions, 257 cycles, 1,796 at 2×, halves cut after session 2,694 (2015-12-07);
     - QQQ: 1,485 sessions, 71 cycles.
5. **Self-check 7.** `--selfcheck` now also runs harness check 7, the placebo identity, inline.

## Tests and mutation score

- **`test_edgelab.py`: 282 checks, all pass** (`bench/r3/test-run.txt`). 31 of them are new; `test_tools.py` also passes. The new checks cover:
  - every verdict branch;
  - each PARTIAL reason singly and several together, in the table's order;
  - the G4-fail PARTIAL and NULL;
  - the boundaries:
    - z_used 3.0310 fails and 3.0312 passes;
    - the N = 100 flip, and 3.3723 passes outright;
    - G3 at exactly −5 points passes and at −5.01 fails;
    - p = 0.05 fails;
    - a G4 pass on p alone that fails on a half median;
    - G1 at 5 bp: a tie passes;
    - G6 counts at 99 / 39 / 100 / 40;
    - G7′ at exactly −1;
  - ungated cells that are ignored;
  - parsing of the frozen invocation, and conformance failure on a changed or extra token;
  - an end-to-end command-line run with a synthetic frozen spec.
- **Mutation testing** (`bench/mutate3.py` → `bench/mut/round3-mutation-all.txt`):

  | round | what it covers | caught |
  |---|---|---|
  | r3 | read(), the registration and the conformance check | 33 of 33 (the first pass missed "self-check 7 always passes"; now pinned) |
  | r2 | the round-2 build | 48 of 48 |
  | r1 | the round-1 harness | 45 of 46, the known equivalent mutant |

## The invocation, checked on synthetic files carrying the real dates

The check used a mirror of `tools/market/` (`bench/r3/build_mirror.py`). Its code and frozen inputs are copies. Its `bars/SPY-1d.csv` (5,413 rows) and `bars/QQQ-1d-long.csv` (1,499 rows) are synthetic prices laid on the scheduled calendar, minus the dates the real files lack.

- **Run 1: `sh prereg-2026-10-09/invocation.sh` verbatim.** It exited 3, VOID, in 8 s.
  - Every G0 item passed except the two file SHA-256s, which fail because the files are synthetic. Nothing price-based was printed.
  - The items that passed include the frozen invocation, prereg and window facts; self-checks 1–4 and 7; all 257 and 71 windows reproduced; and the five add-backs.
  - Output: `bench/r3/run1-verbatim.stdout`.
- **Run 2: the same command, with only the two `--expect-sha256` tokens swapped for the synthetic files' hashes.** The frozen spec was pointed at that copy in-process.
  - It exited 0 in 274 s. Both G0 blocks passed, and the verdict was printed after the gates and before the descriptives.
  - On synthetic data the verdict was NULL, with all six reasons.
  - Output: `bench/r3/run2-full.stdout`.

**The command for the real run is `prereg-2026-10-09/invocation.sh`, unchanged:** `sh prereg-2026-10-09/invocation.sh`, run from `tools/market/` once this diff is committed. Any added, changed or missing argument, `--out` included, is now VOID by G0.

## Discrepancies between the frozen text and the harness

None changes a number. Five are worth stating:

1. **Cycles.** The harness cuts cycles at *scheduled* T−4 closes; the frozen text says *executed* entry closes. These are identical here: all 257 and 71 complete entries execute on schedule (`bench/r3/entries-on-schedule.txt`). Only November 2018's exit moves.
2. **G6 halves.** "The half that holds its entry close" is ambiguous only for a cycle entered at the split close itself, 2015-12-07. There is none.
3. **Harness check 1.** It is implemented as |Δ mean d| ≤ the two pairs' residuals + 0.1 bp/yr. On the mirror, d moves at most 3.07 bp/yr, against residuals of up to 3.84 bp/yr, so it passes under any reading of the frozen wording.
4. **The (0%, 7.75%) line.** It prints as a full stress-grid row with every book. read() never reads it.
5. **"Run verbatim" is now literal.** It holds only with the committed `invocation.sh` (SHA-256 0ec3dde1…) and this diff committed.
