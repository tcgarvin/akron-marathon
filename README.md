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
4. **Viewer** — a static web page: map (Leaflet or plain canvas over an
   image of the course), one dot per bib, a slider for race clock, play /
   pause / speed, a bib search that highlights one runner and shows their
   splits. Everything is client-side; data ships as one compact JSON.

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

    python tools/fetch_results.py [--limit N] [--cached-only]   # -> data/splits-20551.json (raw pages cached in data/raw/)
    python tools/build_course.py                                # -> web/course.json
    python tools/build_runners.py                               # -> web/runners.json
    (cd web && python -m http.server 8787)                      # http://localhost:8787/?bib=2&t=30600

`t` in the URL is seconds of day. Stdlib only, no dependencies.

## Status

2026-09-26: built during the race with a 58-runner sample; the full pull
(`fetch_results.py` with no flags, ~300 finishers at 0.4 s each) should wait
until results are final.
