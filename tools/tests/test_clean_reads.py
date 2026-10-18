"""clean_reads drops the one bad chip read, not everything after it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_runners import clean_reads, violations  # noqa: E402

MILE = 1609.344


def reads_at_pace(pace_min_per_mile: float, miles: list[float], start: int = 25200):
    return [
        (f"{m}M", m * MILE, start + round(m * pace_min_per_mile * 60)) for m in miles
    ]


def test_clean_run_is_untouched():
    reads = reads_at_pace(9.0, [0, 3.1, 7.2, 10.7, 13.1, 26.2])
    assert violations(reads) == []
    assert clean_reads(reads) == (reads, [])


def test_late_read_is_dropped_rather_than_later_mats():
    # relay team LTA Airships: the 12.7M chip read came two hours late
    reads = reads_at_pace(8.0, [0, 3.1, 7.2, 10.7, 12.7, 13.1, 17.3, 26.2])
    name, arc, t = reads[4]
    reads[4] = (name, arc, t + 2 * 3600)
    kept, notes = clean_reads(reads)
    assert [r[0] for r in kept] == ["0M", "3.1M", "7.2M", "10.7M", "13.1M", "17.3M", "26.2M"]
    assert notes == [f"dropped 12.7M at {(t + 2 * 3600) // 3600}:{(t + 2 * 3600) % 3600 // 60:02d}:{(t + 2 * 3600) % 60:02d}"]


def test_early_read_that_stays_in_order_is_still_caught():
    # relay team WolfWk: 26M read three minutes after 21.7M, then an hour to the finish
    reads = reads_at_pace(10.0, [0, 3.1, 7.2, 10.7, 13.1, 17.3, 21.7, 26.0, 26.2])
    name, arc, _ = reads[7]
    reads[7] = (name, arc, reads[6][2] + 180)
    kept, notes = clean_reads(reads)
    assert "26.0M" not in [r[0] for r in kept]
    assert len(notes) == 1


def test_relay_leg_twice_as_slow_is_not_a_violation():
    reads = reads_at_pace(7.0, [0, 3.1, 7.2])
    walker_start = reads[-1][2]
    reads += [("10.7M", 10.7 * MILE, walker_start + round(3.5 * 15 * 60))]
    reads += [("13.1M", 13.1 * MILE, reads[-1][2] + round(2.4 * 7 * 60))]
    assert violations(reads) == []


def test_two_reads_left_after_dropping_is_fine():
    reads = reads_at_pace(9.0, [0, 3.1, 26.2])
    name, arc, t = reads[1]
    reads[1] = (name, arc, t - 3600)
    kept, notes = clean_reads(reads)
    assert [r[0] for r in kept] == ["0M", "26.2M"]
