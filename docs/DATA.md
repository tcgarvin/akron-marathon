# Where the data comes from

## Chip times: MTEC Results

The Akron Marathon is timed by MTEC Results (mtecresults.com). Each race has
its own id there: 20551 marathon, 20552 half, 20554 team relay. Two pages
give us everything, and neither needs a login.

**The finisher list.** The race page loads its results table from
`/race/rankedResults` as an HTML fragment, 50 rows per page, with
`rankingType=OVERALL` (or `DIV` plus a `category` such as `M2529` for one
division). It only answers when the request carries the
`X-Requested-With: XMLHttpRequest` header the page's own JavaScript sends.
Each row has the runner's MTEC id, place, bib, name, age, sex, city and
state. Relay rows carry the team name and no city.

**The runner page.** `/runner/show?race=<race>&rid=<id>` has a "Cumulative"
table: one row per timing mat with the elapsed race time and the time of
day. The marathon and relay share nine mats (chip start, 3.1, 7.2, 10.7,
12.7, 13.1, 17.3, 21.7, 26 miles, finish); the half has five (chip start,
3.1, 7.2, 10.7, 12.9, finish). Mats a runner has not crossed yet show a
projected time in red; we skip those, so a runner still on course only has
the mats they have really crossed. The same page gives the division
("out of 355 in MIXED").

`tools/fetch_results.py` fetches these. It pages through the finisher list,
then pulls each runner page once, caching the raw HTML under
`data/raw/<race>/` and the listing row in `data/raw/<race>/index.json`.
Re-running only fetches runners it has not seen, so partial pulls during the
race and the full pull afterwards accumulate into one dataset. The default is
one request at a time with a pause between them; the full field of about
3,400 runners takes over an hour, which is the point. MTEC's robots.txt
disallows search and certificate pages, not these.

## The course: the organiser's Google map

The race website embeds two Google My Maps, one for the marathon and one
for the half. Google exports a My Map as KML at
`google.com/maps/d/kml?mid=<id>&forcekml=1`. Each has the course as a
single line (286 points for the marathon, 916 for the half) plus point
markers for the start, finish and every mile.

`tools/build_course.py` measures the cumulative distance along the line,
then projects each mile marker onto it. Those projections calibrate
"nominal race mile" against "metres along the drawn line", which matters
because the drawn line runs long (26.58 miles for the marathon) from
cutting corners differently than the certified course. Each timing mat is
then placed by its nominal mile through that calibration. The relay uses
the marathon course.

## Putting them together

`tools/build_runners.py` turns each runner's mat times into a list of
(metres along course, seconds of day) pairs, dropping any read that would
send them backwards. The viewer interpolates linearly between the two mats
that bracket the clock, so between mats everyone runs at their average
pace for that segment. Placings shown in the viewer are computed from the
runners loaded, by elapsed chip time, overall and within division.
