import pandas as pd
import pytest

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


# --- population coverage (plan 2.6, 4.5) ------------------------------------

def _popcov():
    from airlume.pipeline.registry import Registry
    from airlume.viz import coverage as c
    return c, c.population_coverage(Registry.load())


def test_population_grid_is_extracted_and_plausible():
    c, pc = _popcov()
    assert not pc.empty, "run scripts/extract_population.py"
    total = pc["pop"].sum()
    # Lahore district was ~13 million at the 2023 census and the box is a little
    # wider than the district, so anything far outside this range is a unit error.
    assert 8e6 < total < 25e6, f"implausible total population {total:,.0f}"
    assert (pc["pop"] >= 1).all()
    lat_min, lat_max, lon_min, lon_max = c.LAHORE_BBOX
    assert pc["lat"].between(lat_min, lat_max).all()
    assert pc["lon"].between(lon_min, lon_max).all()


def test_population_shares_are_consistent():
    c, pc = _popcov()
    s = c.population_stats(pc)
    assert s["share_within_5km"] + s["share_beyond_5km"] == pytest.approx(1.0)
    assert s["share_within_3km"] <= s["share_within_5km"]
    assert 0 < s["mean_km_pop_weighted"] < 30
    assert s["people_beyond_5km"] == pytest.approx(
        s["total_population"] * s["share_beyond_5km"], rel=1e-6)


def test_population_weighted_mean_differs_from_area_mean():
    """People are not spread evenly over the box, so the two must not coincide.

    If they did, the population layer would be adding nothing and something has
    gone wrong in the weighting.
    """
    from airlume.pipeline.registry import Registry
    c, pc = _popcov()
    area = c.coverage_stats(c.coverage(Registry.load()))
    pop = c.population_stats(pc)
    assert pop["mean_km_pop_weighted"] != pytest.approx(area["mean_km_urban"], abs=0.05)


def test_population_ranked_sites_bring_people_inside_five_km():
    c, pc = _popcov()
    r = c.recommend_stations_by_population(pc, n=3, candidates=120)
    assert list(r["rank"]) == [1, 2, 3]
    assert (r["people_brought_within_5km"] > 0).all()
    # each site helps less than the one before, and the backlog keeps shrinking
    assert r["people_brought_within_5km"].is_monotonic_decreasing
    assert r["people_beyond_5km_after"].is_monotonic_decreasing
    assert r["mean_km_after"].is_monotonic_decreasing
    assert r["mean_km_before"].iloc[1] == r["mean_km_after"].iloc[0]


def test_population_sites_are_placed_where_people_live():
    """A site chosen for population must not land on an empty cell."""
    c, pc = _popcov()
    r = c.recommend_stations_by_population(pc, n=2, candidates=120)
    for row in r.itertuples():
        match = pc[(pc["lat"] == row.lat) & (pc["lon"] == row.lon)]
        assert len(match) == 1 and match["pop"].iloc[0] >= 1


def test_population_functions_are_safe_without_the_csv():
    from airlume.viz import coverage as c
    empty = pd.DataFrame(columns=["lat", "lon", "pop"])
    assert c.population_stats(empty) == {}
    assert c.recommend_stations_by_population(empty).empty


def test_exclusions_keep_sites_off_the_airport_and_military_land():
    c, pc = _popcov()
    lu = c.landuse_grid()
    if lu.empty or not lu["excluded"].any():
        pytest.skip("run scripts/extract_landuse.py")
    r = c.recommend_stations_by_population(pc, n=3, candidates=120, apply_exclusions=True)
    blocked = {(round(x.lat, 6), round(x.lon, 6)) for x in lu[lu["excluded"]].itertuples()}
    for row in r.itertuples():
        assert (round(row.lat, 6), round(row.lon, 6)) not in blocked


def test_combined_score_moves_sites_towards_sources():
    """Weighting by source proximity must actually change where sites land, and
    put them closer to major roads than the population-only ranking does."""
    c, pc = _popcov()
    if c.landuse_grid().empty:
        pytest.skip("run scripts/extract_landuse.py")
    pop_only = c.recommend_stations_by_population(pc, n=3, candidates=120, apply_exclusions=True)
    combined = c.recommend_stations_by_population(pc, n=3, candidates=120,
                                                  apply_exclusions=True, source_weight=0.3)
    assert "km_major_road" in combined.columns
    assert set(zip(pop_only["lat"], pop_only["lon"])) != set(zip(combined["lat"], combined["lon"]))
    lu = c.landuse_grid().set_index(["lat", "lon"])
    pop_road = [lu.loc[(r.lat, r.lon), "km_major_road"] for r in pop_only.itertuples()]
    assert combined["km_major_road"].mean() < pd.Series(pop_road).mean()


def test_combined_ranking_covers_fewer_people_and_says_so():
    """The trade-off is the point: source weighting buys relevance with coverage."""
    c, pc = _popcov()
    if c.landuse_grid().empty:
        pytest.skip("run scripts/extract_landuse.py")
    pop_only = c.recommend_stations_by_population(pc, n=3, candidates=120, apply_exclusions=True)
    combined = c.recommend_stations_by_population(pc, n=3, candidates=120,
                                                  apply_exclusions=True, source_weight=0.3)
    assert (combined["people_brought_within_5km"].sum()
            < pop_only["people_brought_within_5km"].sum())


def test_landuse_join_is_safe_when_not_extracted():
    from airlume.viz import coverage as c
    df = pd.DataFrame([{"lat": 31.5, "lon": 74.3, "pop": 100.0, "km": 7.0}])
    out = c.with_landuse(df, landuse=pd.DataFrame())
    assert out["excluded"].tolist() == [False]
