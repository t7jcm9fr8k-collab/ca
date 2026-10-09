**SIGN** — Archivist, 2026-10-09.
- The six corrections below are precision fixes, not conditions.
- Grades follow `D/r1-archivist.md` §6: V-text = read in full; V-abs = abstract or snippet; V-sec = secondary source.

1. **L16 — the T+1 shift was measured in momentum-loser stocks, not the index.** Replace with: "the selling trough of momentum-loser stocks moved one session later after T+1 (2024-05-28); 19 post-reform months, data through 2025-12". Cite `D/r1-archivist.md` §3.1 (README V-text, snippet V-abs). My own §0 wording was loose.
2. **L12–15 — Etula et al.'s mechanism is *proposed*, not established.**
   - McConnell & Xu (FAJ 2008) found volume and net equity-fund flows no higher at turns of the month [V-abs].
   - Kayacetin (JIFMIM 2026) attributes the revival to infrequent rebalancing and risk deferral — a "relief rally" after volatile, weak spells — not to payment deadlines. He measures [T−3, T+4] across 30 indices: 10 bp/day in the window vs 0 outside [V-abs].
   - So Kayacetin is evidence that the month-end effect lives, not that this mechanism drives it. Say so.
3. **L248 and L289 — two out-of-sample labels need tightening.**
   - "After publication" should read "after the 2014–15 working papers (RFS 2020)". Etula's 2013 sample end comes from a slide axis [V-sec]; the RFS version's end is unverified.
   - "Outside every published sample" should read "outside every academic sample found". Practitioner posts on recent SPY or E-mini data (ATB Research 2026; Quantseeker) may cover 2024–26 (`D/r1-archivist.md` §3.1).
4. **L272 — my 0.05–0.09 is in the wrong column.** They are upper bounds: P(G5) alone at N = 40. They are prior-weighted with intact gaps of 12.2 bp/day (my weights) and up to 14 bp/day (Red Team weights), so they fit neither "10 bp/day" column. Print "≤ 0.05 / ≤ 0.09 (intact 12.2 / 14 bp/day)" (`D/archivist/estimates_r2.txt` §1–2).
5. **L282 — the "half size reads null" claim needs a stated size and word fix.**
   - It holds at half of 10 bp/day: G4 timing z = 1.43, fails 58% of the time.
   - It does not hold at half of 14: z = 2.01, passes 64% (`D/archivist/estimates_r3.txt`).
   - A G4 failure with G1–G3 passing prints PARTIAL, not NULL. Write "fails G4", and state which size.
6. **L263 — "+ 1 × c" is an unlabelled assumption.** It sets the fund's swap financing at c with zero spread. The spread was not retrieved; my §2.4 assumed about 0.6%. Label it, or the SSO line looks cheaper than margin only because a cost was left out.
