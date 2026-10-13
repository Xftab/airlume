# Registry notes (13 Oct 2026)

`data/registry/stations.csv` and `cities.csv` are the only files the code reads. This note records where each number came from.

## Lahore stations
| id | name | lat, lon | source | confidence |
|---|---|---|---|---|
| LHR-GT | GT Road | 31.5798, 74.3550 | IQAir map link | station-level, unverified |
| LHR-SHD | Shahdara | 31.6381, 74.2852 | IQAir map link | station-level, unverified |
| LHR-MR | Multan Road (Chung) | 31.4314, 74.1736 | GeoNames centroid | neighbourhood only |
| LHR-BR | Barki Road | 31.5359, 74.4352 | IQAir map link | station-level, unverified |
| LHR-KN | Kahna Nau | 31.3669, 74.3689 | GeoNames centroid | neighbourhood only |
| LHR-GB3 | Gulberg III | 31.5081, 74.3375 | IQAir map link (credited to Urban Unit) | station-level, operator unclear |
| LHR-DHA6 | DHA Phase 6 | 31.4559, 74.4638 | IQAir map link | station-level, unverified |
| LHR-EG | Egerton Road | 31.5609, 74.3308 | IQAir map link | station-level, unverified |
| LHR-PU | Punjab University | 31.4797, 74.2661 | IQAir map link | medium (SW of campus) |
| LHR-WB | Wagha Border | 31.6022, 74.5449 | IQAir map link | station-level, unverified |
| LHR-SP | Safari Park | 31.3823, 74.2182 | IQAir map link | station-level, unverified |

Reverse-geocoded addresses from WAQI agree with the above (e.g. GT Road = UET Begampura; Shahdara = Govt Teaching Hospital; Egerton Road = Aiwan-e-Iqbal). The map must show a "position approximate" note until the EPA confirms (contribution C7 handles station placement uncertainty).

## Other-city sensors (Urban Unit, AirGradient, via OpenAQ unless noted)
Islamabad: E-11/4 (33.6990, 72.9819), Park Road F-8/1 (33.7103, 73.0313), Conservator of Forest (WAQI only).
Karachi: AKU main campus (24.8924, 67.0747), Climate Action Center (24.8638, 67.0566), Orangi Pilot Project (24.9373, 67.0190), G3 Engineering (24.8070, 67.0332), NED, Gulistan-e-Johar, Malir Cantt, Clifton (WAQI only).
Peshawar: Abasyn University (34.0322, 71.5864), IMSciences (33.9582, 71.3344 — verify), DG Local Govt (33.9917, 71.4351), Gandhara University (33.9927, 71.4809).
Quetta: University of Balochistan (30.1621, 66.9898), SWISS Plaza (30.2016, 67.0145), Simongli Town (30.0829, 66.9617) — IQAir/WAQI only, so display-only.
These go into `stations.csv` in Phase 1 once OpenAQ ids and licences are confirmed with the key.

## Punjab cities
36 district centroids from English Wikipedia infoboxes; adequate for a city-level disc on a national map. Replace with the EPA's own station coordinates if the permission reply provides them.
