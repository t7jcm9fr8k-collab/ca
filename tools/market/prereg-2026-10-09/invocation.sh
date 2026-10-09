#!/bin/sh
# The single invocation frozen by PREREG-2026-10-09-month-end.md. Run from tools/market/, verbatim, once.
# Exit codes: 0 ran; 2 refused; 3 VOID (G0 failed: nothing price-based computed or printed).
python3 -B edgelab.py --rule month_end_overlay \
  --csv bars/SPY-1d.csv --source stooq --adjusted yes --total-return-through 2025-03-21 \
  --expect-sha256 52a006deec221ab41c869bd25b279203d3f8d9dedad0bb99ea481164a2cd45a0 \
  --start-close 2005-03-24 --end 2026-08-25 --closes-only --accrual calendar \
  --cost-bps-per-side 2 5 1 --cash-yield 0.015 0 0.03 --spread 0.015 0.04 --cell 2:0:0.0775 \
  --trials 40 --trials-sensitivity 100 --seed 20261009 \
  --placebo within_cycle_circular --placebo-draws 10000 \
  --dsr-draws 5000 --dsr-block 10 --dsr-benchmark constant --halves session --marks close \
  --distributions prereg-2026-10-09/spy-distributions-2025-2026.csv \
  --expect-addbacks 2025-06-20 2025-09-19 2025-12-19 2026-03-20 2026-06-18 \
  --window-list prereg-2026-10-09/windows-S1-SPY.csv --prereg PREREG-2026-10-09-month-end.md \
  --selfcheck --leak-samples all \
  --sso-expense 0.0148 --sso-cost-bps-per-side 3 \
  --veto-csv bars/QQQ-1d-long.csv --veto-source stooq --veto-adjusted yes \
  --veto-total-return-through 2025-03-24 \
  --veto-expect-sha256 4433bdbc019328196c84e610fe5f834aa72097de70a9d3bc2d499a6dfeae790e \
  --veto-start-close 1999-03-25 --veto-end 2005-02-22 --veto-window-list prereg-2026-10-09/windows-G7-QQQ.csv \
  --span 2005-03-01:2013-12-31 --span 2014-01-01:2023-12-31 --span 2024-01-01:2026-07-31 \
  --overlap-strategy rsi_dip:14,30,5 \
  --event-dates prereg-2026-10-09/deliberation/data/events/fomc-statements-2005-2026.csv --event-where kind=scheduled \
  --event-coverage 2005-01-01:2016-12-31 --event-coverage 2025-01-01:2026-12-31 \
  --event-name "scheduled FOMC statement" \
  --offset-profile --offsets=-8:3 --group-labels 3 2 1 --group-breaks 2017-09-05 2024-05-28 \
  --exclude-dates addbacks --contrast=-3:2,1:3 \
  --out runs/edgelab-2026-10-09-month-end.txt
