def test_lahore_has_11_stations(registry):
    assert len(registry.stations_in("PB-LHE")) == 11


def test_all_cities_have_coordinates(registry):
    for c in registry.cities:
        assert 23 < c.lat < 37 and 60 < c.lon < 78, c


def test_city_matching(registry):
    assert registry.match_city("lahore").city_id == "PB-LHE"
    assert registry.match_city("DG Khan").name == "Dera Ghazi Khan"
    assert registry.match_city("Faisalabd").name == "Faisalabad"  # typo tolerated
    assert registry.match_city("Paris") is None


def test_station_matching_direct(registry):
    sid, note = registry.match_station("gulberg", "PB-LHE")
    assert sid == "LHR-GB3" and note is None


def test_nearest_station_rule(registry):
    sid, note = registry.match_station("Model Town", "PB-LHE")
    assert sid in {"LHR-GB3", "LHR-PU", "LHR-KN"}
    assert note and "nearest" in note and "km" in note


def test_unknown_area(registry):
    assert registry.match_station("Narnia", "PB-LHE") is None
