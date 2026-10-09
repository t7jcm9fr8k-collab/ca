# Event-calendar retrieval log (Quartermaster, round 1)

Method. WebFetch could not be used: every call failed with `getaddrinfo ENOTFOUND`
(federalreserve.gov, www.federalreserve.gov, www.bls.gov, en.wikipedia.org and even
example.com), i.e. it has no DNS in this environment. The proxy refuses
federalreserve.gov and bls.gov to curl/python (403, per the lead). The only working
route was the WebSearch tool with `allowed_domains` restricted to the official domain.
Each entry below records the query, the UTC time window, every URL the search returned,
and the dates as the search tool's summary stated them. A date is marked
URL-CORROBORATED when an official URL in the result encodes it (FOMC minutes/transcript
filenames carry YYYYMMDD; BLS archive filenames carry MMDDYYYY). The summaries are
second-hand: they were written by the search tool from the official page, not read by
me directly. Nothing here is filled from memory.

## Q1 — FOMC 2025/2026 (no domain restriction) — 2026-10-09 ~04:44Z
Query: "FOMC meeting calendars 2025 2026 federalreserve.gov fomccalendars"
URLs: https://federalreserve.gov/monetarypolicy/fomccalendars.htm ; https://www.texasbankers.com/?p=3645 ;
https://www.5paisa.com/blog/us-fed-fomc-meeting-calendar-schedule ; https://www.texasbankers.com/fomc-releases-meeting-schedule-for-2025/ ;
https://mnimarkets.com/calendars/fomc-meeting-calendar ; https://blogapi.youngplatform.com/blog/news/fed-schedule-meeting-when-next/ (and two others)
Summary dates — 2026: Jan 27-28; Mar 17-18*; Apr 28-29; Jun 16-17*; Jul 28-29; Sep 15-16*; Oct 27-28; Dec 8-9* (*=SEP).
2025 (from a Texas Bankers Association summary of the Fed's tentative schedule; the tool said the Fed page's Jan/Mar/May 2025 match):
Jan 28-29; Mar 18-19*; May 6-7; Jun 17-18*; Jul 29-30; Sep 16-17*; Oct 28-29; Dec 9-10*.
Status: SUPERSEDED by the domain-restricted queries below where they exist.

## Q2 — FOMC 2005 (allowed_domains federalreserve.gov) — 2026-10-09 ~04:45Z
Query: "FOMC 2005 meetings statement dates fomchistorical2005"
URLs: https://www.federalreserve.gov/monetarypolicy/fomchistorical2005.htm ; .../files/FOMC20050630meeting.pdf ;
.../fomc/minutes/20050503.htm ; .../fomc/minutes/20051213.htm ; .../fomc/minutes/20050809.htm ; .../files/FOMC20050202meeting.pdf ;
.../files/FOMC20050322meeting.pdf ; .../files/FOMC20051213meeting.pdf ; .../files/FOMC20051213material.htm ; .../fomc/minutes/20050322.htm
Summary (from fomchistorical2005.htm): eight meetings, each with a statement: Feb 1-2; Mar 22; May 3; Jun 29-30; Aug 9; Sep 20; Nov 1; Dec 13.
URL-corroborated last days: 20050202, 20050322, 20050503, 20050630, 20050809, 20051213. Not URL-corroborated: Sep 20, Nov 1.
No unscheduled meeting or conference call was mentioned (not asked; absence is NOT verified).

## Q3 — CPI 2005 (allowed_domains bls.gov) — 2026-10-09 ~04:46Z
Query: "BLS Consumer Price Index news release schedule 2005 release dates"
URLs: https://www.bls.gov/schedule/news_release/cpi.htm ; https://www.bls.gov/bls/news-release/cpi.htm ;
https://www.bls.gov/news.release/archives/cpi_09152005.pdf ; https://blsmon1.bls.gov/bls/news-release/cpi.htm ;
https://www.bls.gov/bls/bls2005sched.pdf ; .../archives/cpi_05182005.pdf ; .../archives/cpi_08162005.pdf ; .../archives/cpi_11162005.pdf ;
https://www.bls.gov/news.release/pdf/cpi.pdf ; https://www.bls.gov/bls/bls2006sched.pdf
Summary dates (release date <- reference month), from bls2005sched.pdf and archived releases:
2005-01-19 <- Dec 2004; 2005-02-23 <- Jan; 2005-03-23 <- Feb; 2005-04-20 <- Mar; 2005-05-18 <- Apr (URL); 2005-06-15 <- May;
Jun 2005 data: UNVERIFIED ("schedule text garbled"); 2005-08-16 <- Jul (URL); 2005-09-15 <- Aug (URL); 2005-10-14 <- Sep;
2005-11-16 <- Oct (URL); 2005-12-15 <- Nov; 2006-01-18 <- Dec 2005.

## Q4 — FOMC 2006 (allowed_domains federalreserve.gov) — 2026-10-09 ~04:47Z
URLs: .../monetarypolicy/fomchistorical2006.htm ; .../boarddocs/press/monetary/2005/20050909/default.htm ; .../2005/20050629/default.htm ;
.../fomc/minutes/20060629.htm ; .../files/FOMC20060328meeting.pdf ; .../fomc/minutes/20060808.htm ; .../fomc/minutes/20060328.htm ;
.../files/FOMC20060510meeting.pdf ; .../fomc/minutes/20061025.htm ; (a FEDS note)
Summary (fomchistorical2006.htm): Jan 31; Mar 27-28; May 10; Jun 28-29; Aug 8; Sep 20; Oct 24-25; Dec 12 (each with statement).
URL-corroborated: 20060328, 20060510, 20060629, 20060808, 20061025. Not URL-corroborated: Jan 31, Sep 20, Dec 12.
Unscheduled 2006: none found (absence NOT verified).

## Q5 — FOMC 2007 — 2026-10-09 ~04:47Z
URLs: .../files/FOMC20070807meeting.pdf ; .../fomcminutes20071211.htm ; .../fomcminutes20071031.htm ; .../fomc/minutes/20070807.htm ;
.../newsevents/pressreleases/monetary20080102a.htm ; .../files/FOMC20071031meeting.pdf ; .../annual07/sec1/c3.htm ;
.../fomc/minutes/20070918.htm ; .../files/FOMC20070810confcall.pdf ; .../files/fomc20070918meeting.pdf
fomchistorical2007.htm NOT returned. Scheduled found: Jun 27-28 (from Aug minutes); Aug 7 (URL); Sep 18 (URL); Oct 30-31 (URL 20071031); Dec 11 (URL).
Conference calls found: Aug 10 (URL confcall), Aug 16, Dec 6. GAP: Jan-May 2007 scheduled meetings — see gap-fill query.

## Q6 — FOMC 2008 — 2026-10-09 ~04:47Z
URLs: .../fomcminutes20080130.htm ; .../fomc20080625.htm ; .../fomcminutes20081029.htm ; .../fomcminutes20080430.htm ;
.../files/FOMC20081007confcall.pdf ; .../fomcminutes20080805.htm ; .../fomcminutes20080318.htm ; .../files/FOMC20080916meeting.pdf ;
.../files/FOMC20081029meeting.pdf ; .../files/FOMC20081216meeting.pdf
fomchistorical2008.htm NOT returned. Scheduled (minutes "next meeting" notes + URLs): Jan 29-30 (URL); Mar 18 (URL); Apr 29-30 (URL);
Jun 24-25 (URL); Aug 5 (URL); Sep 16 (URL); Oct 28-29 (URL); Dec 15-16 (URL). All eight URL-corroborated.
Conference calls found: Jan 9; Jan 21 ("statement text to be released the next morning" => statement 2008-01-22);
Mar 10; Jul 24; Sep 29; Oct 7 (URL) — the minutes tie the 2008-10-08 coordinated 50 bp cut to it. Completeness NOT verified.

## Q7 — FOMC 2009 — 2026-10-09 ~04:47Z
URLs: .../fomcminutes20091104.htm ; .../fomcminutes20090923.htm ; .../fomcminutes20090624.htm ; .../fomcminutes20090128.htm ;
.../files/FOMC20090812material.htm ; .../fomcminutes20090318.htm ; .../fomcminutes20090429.htm ; .../files/FOMC20090603confcall.pdf ;
.../files/FOMC20090318material.htm ; .../files/FOMC20090318meeting.pdf
Scheduled: Jan 27-28 (URL); Mar 17-18 (URL); Apr 28-29 (URL); Jun 23-24 (URL); Aug 11-12 (URL 20090812); Sep 22-23 (URL);
Nov 3-4 (URL); Dec 15-16 (from Nov minutes' next-meeting note only — not URL-corroborated).
Conference calls: Jan 16; Feb 7; Jun 3 (URL). Completeness NOT verified.

## Q8 — FOMC 2010 — 2026-10-09 ~04:47Z
URLs: .../fomchistorical2010.htm ; .../files/FOMC20101103meeting.pdf ; .../files/FOMC20101015material.htm ; .../files/FOMC20101015confcall.pdf ;
.../faqs/about_12844.htm ; .../annual-report/2010-minutes-fomc-meetings.htm ; .../fomcminutes20101103.htm ; .../fomcminutes20101214.htm ;
.../newsevents/pressreleases/monetary20090604a.htm (tentative 2010 schedule) ; .../fomcminutes20100921.htm
Scheduled: Jan 26-27; Mar 16; Apr 27-28; Jun 22-23; Aug 10; Sep 21 (URL); Nov 2-3 (URL); Dec 14 (URL).
Unscheduled: May 9 conference call WITH a statement (historical page); Oct 15 videoconference, no decision.

## Q9 — FOMC 2007 gap-fill — 2026-10-09 ~04:46Z
Query: "FOMC minutes 2007 January 30-31 March 20-21 May 9 meeting statement"
URLs: .../fomc/minutes/20070131.htm ; .../files/FOMC20070131meeting.pdf ; .../fomchistorical2007.htm ; .../pressreleases/monetary20070131a.htm (FOMC statement) ;
.../pressreleases/monetary20060720b.htm (tentative 2007 schedule) ; .../fomc/minutes/20070321.htm ; .../pressreleases/monetary20070411a.htm ;
.../files/fomc20070321meeting.pdf ; .../pressreleases/monetary20070509a.htm (FOMC statement) ; .../fomc/minutes/20070509.htm ; .../2007all.htm
Confirmed with URLs: Jan 30-31 (statement 2007-01-31), Mar 20-21 (statement 2007-03-21), May 9 (statement 2007-05-09).
2007 scheduled list now: Jan 31; Mar 21; May 9; Jun 28; Aug 7; Sep 18; Oct 31; Dec 11 (Jun 27-28 from Aug minutes only).

## Q10 — FOMC 2011 — 2026-10-09 ~04:46Z
URLs: .../fomchistorical2011.htm ; .../fomcpresconf20110622.htm ; .../fomcminutes20110622.htm ; .../fomcminutes20110427.htm ;
.../fomcpresconf20110427.htm ; .../fomcpresconf20111102.htm ; .../fomcminutes20111213.htm ; .../fomcminutes20110921.htm ; .../fomcminutes20110315.htm ;
.../files/FOMC20110921material.htm
Scheduled: Jan 25-26 (archive page, no URL); Mar 15 (URL); Apr 26-27 (URL; statement 12:30 p.m.); Jun 21-22 (URL; 12:30 p.m.);
Aug 9 (archive page); Sep 20-21 (URL); Nov 1-2 (URL; 12:30 p.m.); Dec 13 (URL; statement 2:15 p.m.).
Statement release times are given only where quoted; press-conference meetings in 2011 released at 12:30 p.m.

## Q11 — FOMC 2012 — 2026-10-09 ~04:46Z
URLs: .../fomcpresconf20120913.htm ; .../fomcpresconf20121212.htm ; .../fomcpresconf20120125.htm ; .../fomc_historical.htm ;
.../fomcpresconf20120620.htm ; .../fomcpresconf20120425.htm ; .../files/fomcminutes20121212.pdf ; .../files/fomcminutes20120913.pdf ;
.../files/FOMC20120801material.htm ; .../pressreleases/monetary20120822a.htm
Scheduled: Jan 24-25 (URL; 12:20 p.m. per tool); Apr 24-25 (URL; 12:35 p.m.); Jun 19-20 (URL); Jul 31-Aug 1 (URL 20120801);
Sep 12-13 (URL); Oct 23-24 (from Sep minutes' next-meeting note only); Dec 11-12 (URL).
GAP: March 2012 — the tool said "from general knowledge ... March 13" — NOT ACCEPTED; see gap-fill.

## Q12 — FOMC 2013 — 2026-10-09 ~04:46Z
URLs: .../fomchistorical2013.htm ; .../fomcpresconf20130619.htm ; .../A4110FBE934A4A278474425B2BA9A0D8.htm ; .../fomcpresconf20131218.htm ;
.../files/fomcminutes20130619.pdf ; .../fomcpresconf20130918.htm ; .../files/fomcminutes20131218.pdf ; .../fomcpresconf20130320.htm ;
.../files/fomcminutes20130918.pdf ; .../files/fomcminutes20130320.pdf
Summary (fomchistorical2013.htm): Jan 29-30; Mar 19-20 (URL); Apr 30-May 1; Jun 18-19 (URL); Jul 30-31; Sep 17-18 (URL); Oct 29-30; Dec 17-18 (URL).
Statements at 2:00 p.m. on the four press-conference dates quoted.

## Q13 — FOMC 2012 gap-fill (March, October) — 2026-10-09 ~04:46Z
URLs: .../fomcminutes20120313.htm ; .../files/FOMC20120313material.htm ; .../pressreleases/monetary20120313a.htm (FOMC statement) ;
.../files/FOMC20120313meeting.pdf ; .../pressreleases/monetary20120403a.htm ; .../files/FOMC20120313Agenda.pdf ; .../fomchistorical2012.htm ;
.../fomcminutes20121024.htm ; .../pressreleases/monetary20121114a.htm ; .../files/fomcminutes20121023.pdf ; .../files/fomc20121024meeting.pdf ;
.../pressreleases/monetary20120516b.htm (revised tentative 2012 schedule)
Confirmed with URLs: Mar 13, 2012 (statement press release 20120313a); Oct 23-24, 2012 (minutes 20121024).
2012 scheduled list now: Jan 25; Mar 13; Apr 25; Jun 20; Aug 1; Sep 13; Oct 24; Dec 12 (statement days).

## Q14 — FOMC 2014 — 2026-10-09 ~04:46Z
URLs: .../fomcpresconf20141217.htm ; .../fomcpresconf20140917.htm ; .../fomcpresconf20140319.htm ; .../fomcpresconf20140618.htm ;
.../files/FOMC20140618meeting.pdf ; .../files/FOMC20141029meeting.pdf ; .../files/fomcminutes20140129.pdf ; .../files/fomcminutes20140917.pdf ;
.../files/FOMC20141217meeting.pdf ; .../files/FOMC20140730meeting.pdf
Scheduled: Jan 28-29 (URL); Mar 18-19 (URL; 2:00 p.m.); Jun 17-18 (URL; 2:00 p.m.); Jul 29-30 (URL); Sep 16-17 (URL; 2:00 p.m.);
Oct 28-29 (URL); Dec 16-17 (URL; 2:00 p.m.). GAP: April 29-30 not returned — see gap-fill.

## Q15 — FOMC 2015 — 2026-10-09 ~04:46Z
URLs: .../fomchistorical2015.htm ; .../fomcpresconf20150318.htm ; .../fomcminutes20151216.htm ; .../fomcpresconf20150617.htm ;
.../fomcpresconf20150917.htm ; .../fomcpresconf20151216.htm ; .../files/fomcminutes20151028.pdf ; .../fomcminutes20150318.htm ;
.../policy-normalization-discussions-communications-history.htm ; .../fomcminutes20150729.htm
Summary (fomchistorical2015.htm): Jan 27-28; Mar 17-18 (URL); Apr 28-29; Jun 16-17 (URL); Jul 28-29 (URL); Sep 16-17 (URL);
Oct 27-28 (URL); Dec 15-16 (URL). Statements 2:00 p.m. where quoted.

## Q16 — FOMC 2016 — 2026-10-09 ~04:46Z
URLs: .../fomcpresconf20160921.htm ; .../fomcpresconf20161214.htm ; .../fomcpresconf20160316.htm ; .../fomcpresconf20160615.htm ;
.../files/FOMC20160921meeting.pdf ; .../files/fomcminutes20161214.pdf ; .../pressreleases/monetary20161012a.htm ; .../fomcminutes20160727.htm ;
.../files/FOMC20161102meeting.pdf ; .../fomcminutes20160316.htm
Scheduled: Jan 26-27 (referenced in March minutes only); Mar 15-16 (URL); Apr 26-27 (March minutes' next-meeting note only);
Jun 14-15 (URL); Jul 26-27 (URL); Sep 20-21 (URL); Nov 1-2 (URL); Dec 13-14 (URL).

## STOP — 2026-10-09 ~04:47Z
The next five queries (FOMC 2014 April gap-fill; FOMC 2017, 2018, 2019, 2020) were refused by the tool:
"this turn's web search budget is used up (limit: 200 WebSearch calls per turn, shared by every agent in it)".
Per the tool's instruction no workaround was attempted (no curl/wget to search engines, no reader/proxy/archive services).
NOT RETRIEVED, therefore UNVERIFIED: FOMC 2017-2024 (all), FOMC 2014-04 meeting, FOMC unscheduled actions 2011-2026;
CPI release dates 2006-2026 and the 2005 release of June-2005 data; Employment Situation release dates 2005-2026 (all).
A follow-up turn with fresh search budget (or the owner raising CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION) can complete them
with the same per-year queries; BLS's yearly "release schedule for major economic indicators" PDFs (e.g. bls2005sched.pdf)
carry both CPI and Employment Situation dates, but schedules show PLANNED dates — shutdown years (2013, 2025) need the
archived-release filenames for ACTUAL dates.
