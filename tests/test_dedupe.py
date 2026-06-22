from tcg_monitor.dedupe import DedupeStore


def test_seen_after_mark(tmp_path):
    store = DedupeStore(tmp_path / "d.json", ttl_hours=6)
    assert store.seen("p1", "bestbuy", 59.99) is False
    store.mark("p1", "bestbuy", 59.99)
    assert store.seen("p1", "bestbuy", 59.99) is True


def test_different_price_not_deduped(tmp_path):
    store = DedupeStore(tmp_path / "d.json", ttl_hours=6)
    store.mark("p1", "bestbuy", 59.99)
    assert store.seen("p1", "bestbuy", 49.99) is False


def test_ttl_expiry(tmp_path):
    clock = {"t": 1000.0}
    store = DedupeStore(tmp_path / "d.json", ttl_hours=1, now=lambda: clock["t"])
    store.mark("p1", "bestbuy", 59.99)
    assert store.seen("p1", "bestbuy", 59.99) is True
    clock["t"] += 3601  # > 1h
    assert store.seen("p1", "bestbuy", 59.99) is False


def test_persists_across_instances(tmp_path):
    path = tmp_path / "d.json"
    DedupeStore(path, ttl_hours=6).mark("p1", "target", 26.99)
    assert DedupeStore(path, ttl_hours=6).seen("p1", "target", 26.99) is True
