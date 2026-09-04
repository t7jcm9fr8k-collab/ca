# Start here — 2026-09-01, 06:00

Everything below is on branch `claude/10k-revenue-slack-agents-iu8xu0`.
Clone it: `cd ~/Desktop && git clone https://github.com/t7jcm9fr8k-collab/ca.git`

---

## The one thing blocking everything

**No source plates.** Every archive is unreachable from a cloud session — the
proxy refuses the connection to `commons.wikimedia.org`, `metmuseum.org` and the
rest before any request is made, and a browser goes through that same proxy, so
Playwright and Claude-in-Chrome hit the identical wall. Nothing landed in Drive
overnight either.

So the eight real designs have **no mockups**. What exists instead is the whole
machine, proven end to end on the low-resolution plate screenshots already in
`Etsy-Art/candidates/` — wrong subjects, too soft to print, but real output you
can judge the pipeline by.

**Download ~5 files and the four designs you picked become real.** `SOURCING.md`
says exactly which files, from where, and what to check on each page. Drop them
in `tools/etsy/sources/` and run `./demo.sh`.

---

## What to look at, in order

**1. The change history — [published as an artifact](https://claude.ai/code/artifact/36fd3eb1-fe8e-4da7-8a02-9fabb058f7d8).**
This is what "see the change history" turned into. One design, two versions, the
inspection between them. v1 was blocked at **2.69:1 contrast on black** — under
the 3:1 WCAG floor for graphical objects — the inks were lightened, and v2 passes
at **4.71:1**. The red panel shows exactly where the file changed.

**2. `out/listings.txt`** — all ten listings with their SEO checks. Zero errors.

**3. `out/calendar-14day.md`** — 14 days, 12 posting slots with paste-ready copy.
Twelve, not fourteen, because 09-13 and 09-14 fall in your school wall.

**4. `.claude/agents/`** — six recorded agents. Read `print-inspector.md` first;
it is the one that says no, and it runs at high effort deliberately.

---

## The gate, which is the point

```
v1  →  inspect  →  v2
```

`mockup.py --version 2` refuses without a recorded inspection of v1, and refuses
again if you give no `--change`. A second mockup exists to answer findings from
the first; without them it is a second guess, and a version with no recorded
change cannot be read as a revision later.

Run `./demo.sh` to watch the whole loop, refusal included.

---

## Nine checks, and what each one prevents

| check | prevents |
|---|---|
| file spec | Printify silently rescaling or rejecting |
| ink coverage | a design that vanishes across a room, or a slab that cracks at the fold |
| stroke width | hairlines DTG cannot hold |
| contrast on white / black | washing out, or disappearing |
| edge halo | a grey ghost outline *(reported, never blocks — see below)* |
| edge bleed | ink clipped by the platen |
| palette | the collage tell |
| provenance | an untraced source reaching a shirt |

Every check reports a **number**, never a bare verdict: "coverage 6.2%, floor 8%"
tells you what to change; "fails coverage" does not. A check that cannot run
reports **UNRUN**, never a pass.

---

## Two things deliberately not blocking

**Edge halo.** Its annulus test cleanly separates a fringe from artwork on
isolated shapes — a clean disc reads 0%, the same disc feathered reads 100% —
but not on dense linework, where the ring fills with neighbouring lines. A
blocking check that fires on every good file trains you to ignore the gate, which
costs more than the defect it was meant to catch. So it reports and you look.

**Mid-tone garments.** Sport Grey and Navy are measured but not enforced, because
you have not decided whether you stock them. The numbers are already earning
their place: on the v2 proof, navy reads 3.57:1 (fine) and sport grey 1.41:1
(will not read).

---

## Two things only you can settle

**Printify's real print area.** `render_shirt.py:54` says 4500×5400 is *"the
common tee front, not a universal"* — unverified. If the Gildan 5000 blueprint
differs, every file is silently the wrong size. Two minutes in the Product
Creator; tell me the number and it changes in one place.

**A real garment blank.** Mockups use a procedurally generated tee. Honest about
scale, crude about everything else. Export a white and a black Printify blank and
they become genuinely convincing.

---

## Still outstanding from earlier, in your tree not mine

- `Prompts/etsy-listing.md:12` still carries the refuted **$13.55** cost. Real
  figure is **$9.79**, break-even **$11.81**. It is an *active prompt template*,
  and four other files carry it too — `CONTRACTS.md:3-7` wants them changed in
  one sitting.
- **Doré** and **Yoshitoshi** need museum open-access copies specifically;
  circulating scans of both often carry modern reproduction claims.

---

## Four defects found by looking at output, not at code

All four are now pinned by tests, and they are the reason `--preview` and the
silhouette proof exist.

1. `render_plate.py` left paper trapped between tentacles, printing as cream
   blobs. 19% of the scan cleared before the fix, 42% after.
2. `compose.py` turned a colour lithograph into faint pencil — a litho's subject
   sits at mid luminance, so linear mapping produced weak alpha.
3. Two QC checks fired on clean files. The halo check reported 98% on a file
   where only 0.6% of pixels were near-full alpha; the palette check counted
   density blends as separate inks, reporting 8 on a two-ink file.
4. The diff heatmap reported **0.0% changed** on a version that plainly changed —
   it compared alpha only, and the change was a recolour.

Two more were caught before they could bite: `calendar.py` and `inspect.py` both
shadowed Python stdlib modules. The second one broke Playwright the first time a
browser was launched from that directory. Renamed to `schedule.py` and `qc.py`.

---

## Commands

```bash
cd tools/etsy
./demo.sh                                   # the whole loop, refusal included
python3 test_tools.py                       # 163 checks
python3 compose.py --list-recipes           # what is still BLOCKED on provenance
python3 mockup.py --design X --version 1 --print out/X-onlight.png
python3 qc.py     --design X --version 1
python3 mockup.py --design X --version 2 --print out/X2.png --change "..."
python3 history.py --report
python3 schedule.py --start 2026-09-01 --end 2026-09-14 --ics
python3 listing.py --catalogue catalogue.json --all
```
