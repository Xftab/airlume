from airlume.viz.coverage import coverage, coverage_stats, recommend_station


def test_coverage_and_recommendation(registry):
    cov = coverage(registry, step_deg=0.02)
    assert len(cov) > 200 and cov["km"].min() < 1.5
    st = coverage_stats(cov)
    assert 0 < st["mean_km_urban"] < 10 and 0 <= st["share_beyond_5km"] <= 1
    rec = recommend_station(cov, registry.stations_in("PB-LHE"), candidates=100)
    assert rec["gain_km"] > 0 and 31.3 < rec["lat"] < 31.72


def test_ranked_sites_show_diminishing_returns(_reg=None):
    """Plan 4.5 asks for five ranked sites with the coverage each adds.

    The useful output is the shape of the curve, not the coordinates: each extra
    station must help, and help less than the one before.
    """
    from airlume.pipeline.registry import Registry
    from airlume.viz import coverage as c

    reg = Registry.load()
    cov = c.coverage(reg, step_deg=0.02)      # coarse grid keeps the test quick
    r = c.recommend_stations(cov, reg.stations_in("PB-LHE"), n=3, candidates=60)

    assert list(r["rank"]) == [1, 2, 3]
    assert (r["gain_km"] > 0).all()                       # every site helps
    assert r["mean_km_after"].is_monotonic_decreasing     # coverage keeps improving
    assert (r["gain_km"].diff().dropna() <= 0).all()      # by less each time
    # each round starts where the previous one ended
    assert r["mean_km_before"].iloc[1] == r["mean_km_after"].iloc[0]
    assert r["share_beyond_5km_after"].is_monotonic_decreasing


def test_ranked_sites_land_inside_the_city_box():
    from airlume.pipeline.registry import Registry
    from airlume.viz import coverage as c

    reg = Registry.load()
    cov = c.coverage(reg, step_deg=0.02)
    r = c.recommend_stations(cov, reg.stations_in("PB-LHE"), n=2, candidates=60)
    lo_lat, hi_lat, lo_lon, hi_lon = c.LAHORE_BBOX
    assert r["lat"].between(lo_lat, hi_lat).all()
    assert r["lon"].between(lo_lon, hi_lon).all()
