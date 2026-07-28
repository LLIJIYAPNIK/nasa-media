from datetime import date
from unittest.mock import patch

from application.web.homepage_query import HomepageSnapshot
from infrastructure.web.snapshot_cache import SnapshotCache

DAY = date(2024, 1, 1)
OTHER_DAY = date(2024, 1, 2)
SNAPSHOT = HomepageSnapshot(apod_day_number=1)


def test_miss_when_nothing_cached():
    cache = SnapshotCache()

    assert cache.get(DAY) is None


def test_hit_returns_the_same_snapshot():
    cache = SnapshotCache()
    cache.set(DAY, SNAPSHOT)

    assert cache.get(DAY) is SNAPSHOT


def test_miss_for_a_different_date():
    cache = SnapshotCache()
    cache.set(DAY, SNAPSHOT)

    assert cache.get(OTHER_DAY) is None


def test_miss_once_ttl_expires():
    cache = SnapshotCache(ttl_seconds=300)

    with patch("infrastructure.web.snapshot_cache.time.monotonic", return_value=1000.0):
        cache.set(DAY, SNAPSHOT)

    with patch("infrastructure.web.snapshot_cache.time.monotonic", return_value=1000.0 + 301):
        assert cache.get(DAY) is None


def test_hit_just_before_ttl_expires():
    cache = SnapshotCache(ttl_seconds=300)

    with patch("infrastructure.web.snapshot_cache.time.monotonic", return_value=1000.0):
        cache.set(DAY, SNAPSHOT)

    with patch("infrastructure.web.snapshot_cache.time.monotonic", return_value=1000.0 + 299):
        assert cache.get(DAY) is SNAPSHOT
