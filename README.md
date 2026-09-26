# Akron Marathon replay

Interactive animation of the Akron Marathon: every bib moving around the
course, driven by chip split times, with a time slider and a "find my bib"
highlight.

## How it works (plan)

1. **Course line** — a GPX/GeoJSON of the route, resampled to a polyline with
   cumulative distance so any distance-along-course maps to a lat/lon.
2. **Timing mats** — each mat is a known distance along the course
   (start, 5K, 10K, half, 30K, 35K, finish or whatever Akron publishes).
3. **Chip splits** — per bib, the clock time at each mat. Position at time
   `t` is the linear interpolation of distance between the two mats that
   bracket `t`. Missing splits are skipped (interpolate across the gap).
   Before the start mat and after the finish mat the runner is parked.
4. **Viewer** — a static page: the two course lines on a canvas, one dot
   per bib coloured by race, a race-clock slider, play / pause / speed, race
   filter chips, and a bib search that highlights one runner and shows their
   splits. Drag to pan, wheel to zoom, double-click to refit.

## Layout

    data/       raw results as downloaded, course GPX
    tools/      Python: scrape/parse results, build the compact JSON
    web/        the static viewer

## Data sources

- **Splits**: MTEC Results, race 20551 (2026 marathon). `/race/rankedResults`
  (XHR, 50 per page) lists finishers; `/runner/show?rid=&race=` gives each
  runner's cumulative table with time of day at ChipStart, 3.1, 7.2, 10.7,
  12.7, 13.1, 17.3, 21.7, 26M and Finish. Red times are projections and are
  skipped. Half marathon is race 20552, relay 20554.
- **Course**: the organiser's Google My Maps, exported as KML
  (`data/15Dqm...kml`, marathon; `data/1rTa...kml`, half). One line plus
  Start, Finish, mile and 5k marker points.

## Pipeline

    python tools/fetch_results.py --race 20551 --race 20552 --race 20554 [--delay 1.0] [--workers 1]
                                  [--limit N | --top-per-division N] [--rid RID] [--cached-only]
                                                  # -> data/splits-<race>.json (raw pages cached in data/raw/)
                                                  # be a good citizen: one worker, a second between requests
    python tools/build_course.py                  # -> web/courses.json (marathon and half)
    python tools/build_runners.py                 # -> web/runners.json (all races, tagged)
    (cd web && python -m http.server 8787)        # http://localhost:8787/?bib=2&t=30600

`t` in the URL is seconds of day. Stdlib only, no dependencies. The viewer is
a single canvas page with no map tiles, so it runs anywhere static files do,
including as a claude.ai artifact (`web/` published as page plus two files).

## Status

2026-09-26: built during the race. v2 has race, sex and division filters,
search by bib, name or team, overall and division placings computed from the
loaded field, a linear course strip, and a phone layout. Full-field pull of
all three races started 12:30 on race day at one request a second.
