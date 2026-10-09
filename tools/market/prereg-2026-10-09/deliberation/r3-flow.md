# Round 3 — Flow Theorist: SIGN

**SIGN.** Both of my deal-breakers are resolved: G6 is now computed on the log timing book, and G3 compares against (A). I accept the 5-point G3 tolerance and k = 1. TLT stays a recorded minority position, not a dissent. L268 (the SSO line, now with a labelled swap spread) settles my one other point.

Corrections, anchored to the current `lead/PREREG-draft.md` (325 lines), errors and ambiguities only:
1. **L230, harness check 1 — error.** Only Σd over the path is invariant across the six (c, s) pairs. Each d_t shifts by about −(1_W − p̂)·f_t: ≈ −1.9 bp on a window session at f = 7%/yr, far above the residual at L137. As written, the check either fails (VOID) or is loosened at run time. Replace "d" with "Σ d over the path".
2. **L92 vs L75 — conflict.** L92's r_on = (open + D)/close(t−1) − 1 reads the open, and L75 says no gate reads opens. L94 shows those opens are official, so this is wording only. Either amend L75 to "opens are read only for the five add-backs (L92–94)", or credit D at the close: r_t = (close_t + D)/close_{t−1} − 1.
3. **L22 — "exactly" is wrong as written.** Under L50 and L110, shares are held between changes and (A) is reset only when S1 changes, so neither book holds constant exposure; (1_W − p)(r − f) holds to first order, not exactly. The gates are unaffected, because they use the realised d_t (L117).
4. **L282 — my ≈ 0.05 assumed z ≥ 3.05 and no N = 100 rule** (r2-flow §2.6). Under the frozen rule (no flip at N = 100, so z ≥ 3.37), the same method gives ≈ 0.03. Print 0.03, or add "before the N = 100 rule".
5. **L147 — ambiguity in "the block's length in scheduled sessions".** November 2018's executed 2× block covers 8 scheduled sessions (7 held, L45). December 2006's and October 2012's cover 7 scheduled sessions but hold 6 and 5 bars (L44). Say whether a draw keeps the scheduled length of W (7), the executed scheduled span, or the held-bar count.
