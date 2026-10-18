# Where the data comes from

## Chip times

The splits are the race's official chip results: for each runner, the time
of day at every timing mat they crossed. The marathon and relay share nine
mats (chip start, 3.1, 7.2, 10.7, 12.7, 13.1, 17.3, 21.7, 26 miles, finish);
the half has five (chip start, 3.1, 7.2, 10.7, 12.9, finish). Projected
times for mats a runner hadn't crossed yet are skipped. They aren't kept in
this repo.

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
(metres along course, seconds of day) pairs. The viewer interpolates
linearly between the two mats that bracket the clock, so between mats
everyone runs at their average pace for that segment. Placings shown in
the viewer are computed from the runners loaded, by elapsed chip time,
overall and within division.

## Bad chip reads

A handful of runners, nearly all relay teams, have one mat read that is
plainly wrong: a 26-mile read at 8:46 for a team that finished at noon, a
12.7-mile read two hours after the 13.1-mile one. Left in, the dot either
runs backwards or covers five miles in three minutes. The builder finds
these by the segment they create: a segment is impossible when its time
goes backwards, its pace is under 3 min/mile, or its pace is under 0.3 of
the runner's own median segment pace (real fields bottom out near 0.4, and
relay legs with a walker and a runner stay above that). For an impossible
segment the builder drops whichever of its two reads leaves fewer
impossible segments, then repeats. A runner needing more than two drops,
or whose finish read is the inconsistent one, is left out, as is anyone
listed with a reason in `data/exclude.json` (one marathoner whose reads
cannot be one run of the full course). `--report` writes every decision
to `data/cleaning.json`; the 2026 field needed nine reads dropped and
three runners left out.
