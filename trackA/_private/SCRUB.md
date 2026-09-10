> **PRIVATE — NEVER PUBLISH THIS FILE.**
> It is the audit record for the extraction. It quotes no personal value, but it
> enumerates, category by category, what kinds of personal material the original
> app contained — which tells a reader what to go looking for and confirms who the
> author is. It lives in `trackA/_private/` and is excluded from the published
> package by `trackA/PUBLISHING.md`. Keep it; do not ship it.

# SCRUB — anonymity checklist for the HUDKit extraction

Every category of identifier that was searched for, where it was found in the SOURCE (file:line
of the original app; the shipped copies differ by a few lines where content was deleted), and
what was done. Nothing personal is quoted here, and this file does NOT ship with the
package — the category list alone would tell a reader what to look for. It stays in
`trackA/_private/`.

Tools: the source clone was read with file-reading tools only and never modified. The shipped
tree was then searched (case-insensitive) for every banned term and every category below.

## Categories

### Owner's name (first name; no surname existed anywhere in scope)
Found in comments only:
- Theme.swift :32, :95, :144
- Motion.swift :4
- HUDComponents.swift :39, :220, :972, :978
- BlockLetters.swift :19
- SpaceBackdrop.swift :47, :551
- ThermalWatch.swift :31 (dependency)
- graphs-textures-launch-mockup.html :353
- start-page-looks.html :81
- Two excluded HTML files (not shipped)

Done: every occurrence rewritten to "the owner" / "the owner's call" / "the owner's request" /
"owner feedback" / "the owner's pick". Pronouns referring to the owner (SpaceBackdrop.swift :552,
HUDComponents.swift :979) rewritten to "That report was right" / "the point stands". Second-person
address to the owner (Theme.swift :5) rewritten in the third person.

### Handles, email addresses, home-directory paths, Apple Team ID, bundle identifiers, "Created by" headers
- Email addresses: none anywhere in scope.
- Absolute home-directory paths: none in the six Swift files; none in the shipped HTML.
  Tilde-style personal paths existed only in two excluded HTML files.
- Apple Team ID / bundle identifiers: none in scope.
- "Created by" headers: none — every Swift file begins at its first `import`.
- Shop / social handle: one, in an excluded HTML file.

Done: nothing to rewrite in shipped files; the excluded files stay excluded.

### App names and the store type name
- App name (two spellings) in comments: Theme.swift :101, :109; BlockLetters.swift :4;
  SpaceBackdrop.swift :47.
- App name in HTML titles, eyebrows, headings and wordmarks: hud-mockups.html :2, :104, :279;
  motion-grammar-demo.html :6, :226; graphs-textures-launch-mockup.html :6, :86, :203;
  start-page-looks.html :6, :72, :101, :143, :187, :214, :257; surfaces-comparison.html :117,
  :209; locked-grid-demo.html :69; sky-radar-options.html :44; day-detail-placements.html :67.
- The assistant/character name: Theme.swift :101; otherwise only in excluded files.
- The store type name as a qualifier: HUDComponents.swift :147, :370, :476, :501, :615.
- The store name as a boot-line label: start-page-looks.html :316, :357.

Done: comments rewritten ("The mood hologram colours, verbatim from the original spec",
"the original castle build", "The wordmark, cut from stone", "the app sits behind other windows");
HTML titles and eyebrows → "HUD …"; HTML wordmarks → "WORDMARK"; the five type qualifiers deleted
in favour of package-local `DayState`, `MonthView`, `MonthDay`, `PunchState`; the boot label →
"SESSION STORE".

### Third-party marks
- A third-party brand colour constant and comment: Theme.swift :52-54.
- The same colour as a CSS variable: hud-mockups.html :7 (used at :149); start-page-looks.html :13
  (unused).
- A third-party logo imageset in the asset catalogue, and the product icon set.

Done: constant deleted from Theme.swift; CSS variable removed from both shipped files and the
one meter that used it recoloured to the palette's `earned`; no asset catalogue content copied.

### Place names
- A town name: locked-grid-demo.html :125 (and one excluded file).
- A state abbreviation and campus building names: day-detail-placements.html :96-99, :123-126,
  :188-191; hud-mockups.html :255-259; the rest in excluded files.

Done: weather line → "Clear · local"; building names and their real room numbers → synthetic
"Room 101" / "Room 202" / "Room 203" / "Room 304" / "Office".

### Personal timetable (course codes, course titles, times, term dates)
- day-detail-placements.html :70-71, :96-101, :123-128, :152-157, :184, :188-193
- hud-mockups.html :236-241, :243-245, :255-259
- motion-grammar-demo.html :344-346
- start-page-looks.html :317, :358 ("5 COURSES")

Done: course rows → "SEMINAR A" / "WORKSHOP B" / "LECTURE C" / "EVENT A…F" / "ROW A…C" with the
same times kept as layout data; "your real courses" → "placeholder events"; the missing-course
warning → "event missing" / "unknown event"; the prediction paragraph rewritten without "my" /
"your"; "5 COURSES" → "5 EVENTS". The phrase "first day of term" was kept as a generic caption.

### Personal business (shop platform, listings, punch-list task strings, commitment name, finances)
- motion-grammar-demo.html :261-262, :304
- hud-mockups.html :350-351, :355-356
- surfaces-comparison.html :121-122, :134-138, :155-159, :176-180, :197-201
- locked-grid-demo.html :123
- start-page-looks.html :119, :231
- Finances, margins, unit counts, platform names: excluded files only.

Done: platform references → "link" / "OPEN LINK"; task strings → neutral tasks ("draft the
announcement", "record the figures", "photograph the items", "write the description", "verify it
went live", "next item", "four new items"); the commitment legend label → "COMMITMENT"; the
"you logged … " sentence → an "e.g." example; "your real punch list" → "a sample punch list".

### Other people's projects / names
- surfaces-comparison.html :166 (a named treatment), :187 (two named projects).

Done: → "A frosted-glass treatment." / "A warm-paper treatment."

### Hardware identification
- ThermalWatch.swift :12 (a specific laptop model); SpaceBackdrop.swift :46 (the same model line).

Done: → "A fanless laptop".

### Owner artwork, embedded third-party code, pet names, internal codenames
- All in the five excluded HTML files and the asset catalogue.

Done: files excluded; documented generically in `mockups/INDEX.md`.

## Excluded outright
Five Design HTML files (two castle/shop simulations, one throne-room render study, one
business/finance ledger, one behavioural-copy test) and the whole asset catalogue. Reasons are
given in `mockups/INDEX.md` without personal detail.

## Kept on purpose (not identifying)
- Internal document references: the motion spec, the contracts document, the skill-tree and
  vision documents, a reference video filename.
- Host-app view and type names in comments (shell view, fight surface, dashboard, study library,
  diagnostics panel, trends view).
- Product-rule names ("Never Miss Twice", "Ten-minute floor"), panel codes ("H4", "R4",
  "FN03"), menu-item letters, dates of design decisions.
- Generic diagnostic strings (a loopback gateway address, "10 sessions", "3 armed").

## Soft identifier left in place
- BlockLetters.swift :213-230 — the glyph table covers exactly the letters of the original
  wordmark plus four others. The entries were re-sorted alphabetically (they were listed in
  wordmark order in the source, which spelled the name); the rows themselves are verbatim.
  Extending the set to A–Z is recommended but is a design change and was not made in this pass.

## Final sweep of the shipped tree
Searched every shipped file, case-insensitively, for: the owner's first name; the app's two
name spellings; the assistant/character name; the store type name; the third-party mark; the
town; the state abbreviation; the campus building names; the course codes; the shop platform and
handle; "/Users/"; "~/"; "Created by"; "@" followed by a domain; and a ten-character uppercase
Team-ID pattern. Every hit was either zero or a false positive documented in the extraction
notes.
