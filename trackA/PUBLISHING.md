# Publishing HUDKit

Read this before the package leaves the machine. It exists because the risk at
publication is not in the code — it is in what travels alongside the code.

## What ships

```
HUDKit/                 the package: Package.swift, LICENSE, README.md, Sources/
mockups/                optional, scrubbed HTML studies (see "The mockups" below)
```

## What never ships

```
_private/               EXTRACTION.md and SCRUB.md, plus identifiers.txt
PUBLISHING.md           this file
```

`_private/SCRUB.md` and `_private/EXTRACTION.md` quote no personal value, and
that is exactly why they are dangerous. They enumerate, as headings, every
category of personal material the original app held — a timetable, a shop with
figures, other people's projects, a specific laptop. A reader learns what to
search for and that there is a specific person to find. `_private/identifiers.txt`
is worse: it holds the literal strings, so `scrub_check.py` can grep for them.

## Publish from a fresh repository, never from this one

`trackA/` is a subdirectory of a private monorepo. Only one commit in that
repo's history touches this path and it is machine-authored, so the path's own
history is clean — but the repository around it is not, and the usual mistakes
are pushing the whole thing or letting a global git identity sign the new repo.

```
python3 trackA/scrub_check.py
mkdir -p ~/HUDKit-release && cp -R trackA/HUDKit ~/HUDKit-release/
cp -R trackA/mockups ~/HUDKit-release/
cd ~/HUDKit-release && git init
git config user.name "<brand name>"
git config user.email "<brand mailbox, not a personal or relay address>"
git add -A && git commit -m "HUDKit 1.0.0"
```

The two `git config` lines are the important part. They must run **before** the
first commit and **without** `--global`, or the commit inherits the identity
already configured on the machine.

Then confirm, before adding a remote:

```
git log --format='%an <%ae>%n%cn <%ce>' | sort -u
git ls-files | grep -Ei '_private|PUBLISHING|EXTRACTION|SCRUB'
```

The first prints only the brand identity. The second prints nothing.

## The mockups

They are design studies, not documentation of shipped API. They are scrubbed and
safe to publish, but they were written as an internal design review, so decide
whether they help a buyer before including them. Dropping them costs nothing.

## Before any release

`swift build` and `swift run HUDDemo` on a Mac. Nothing in this repository can
compile Swift, so that is the only real gate.
