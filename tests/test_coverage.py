from airlume.viz.coverage import coverage, coverage_stats, recommend_station


def test_coverage_and_recommendation(registry):
    cov = coverage(registry, step_deg=0.02)
    assert len(cov) > 200 and cov["km"].min() < 1.5
    st = coverage_stats(cov)
    assert 0 < st["mean_km_urban"] < 10 and 0 <= st["share_beyond_5km"] <= 1
    rec = recommend_station(cov, registry.stations_in("PB-LHE"), candidates=100)
    assert rec["gain_km"] > 0 and 31.3 < rec["lat"] < 31.72
