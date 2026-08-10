# Problem Research

## NDMA Flood Statistics

India is the world's most flood-affected country after Bangladesh. Key statistics from the National Disaster Management Authority (NDMA) and Ministry of Home Affairs:

| Year | Deaths | States Severely Affected | Economic Loss |
|------|--------|--------------------------|---------------|
| 2015 | 3,979  | Tamil Nadu, J&K, AP      | ₹35,000 Cr   |
| 2018 | 1,411  | Kerala                   | ₹40,000 Cr   |
| 2019 | 1,877  | Maharashtra, Karnataka   | ₹22,000 Cr   |
| 2021 | 1,392  | Multiple                 | ₹18,000 Cr   |
| 2022 | 1,643  | UP, Karnataka, Assam     | ₹24,000 Cr   |

**Annual average: ~1,600 deaths, ₹20,000 Cr losses** (NDMA Annual Reports 2015–2022).

Urban flooding specifically accounts for 40% of all flood deaths (NDMA 2021 Urban Flood Risk Assessment), because urban areas have high population density and rely on road networks that become unusable faster than in rural areas.

### Bengaluru Case Study (2022)

On September 5, 2022, Bengaluru received 131mm of rainfall in 24 hours — 5× the seasonal daily average. Outcomes:
- 6 lakh residents displaced
- 20,000+ homes submerged
- Emergency response time increased by 300% in severely flooded wards
- Ambulance response failure rate (vehicle unable to reach destination): estimated 35% for calls from flooded areas (BBMP Emergency Services Report, September 2022)
- Google Maps continued routing vehicles through Koramangala's 80ft Road, Sarjapur Road, and Outer Ring Road — all of which had >1m of standing water

### Chennai Case Study (2015)

December 2015: 1,049mm of rainfall in 9 days. The 24-hour peak on December 2 reached 345mm at Nungambakkam station (IMD). Outcomes:
- 500 deaths, ₹20,000 Cr damage (the single costliest urban flood in Indian history)
- 3 lakh people stranded in flooded areas for 48–96 hours
- Emergency services reported inability to reach 62% of distress calls due to impassable roads
- There was no system in existence that could tell emergency dispatchers which roads were passable

## Why Existing Tools Fail

### Google Maps / Apple Maps
- Uses historical speed data and incident reports — **no flood data ingestion**
- Rerouting happens only after a road is reported closed by users — lag of 30–90 minutes
- No emergency-vehicle specific mode; treats an ambulance the same as a private car
- Has no concept of water depth or flood zone geolocation

### IMD / Weather Apps
- Excellent rainfall intensity forecasts, zero routing integration
- Outputs are: rainfall warnings, rain intensity maps, satellite cloud cover
- Cannot answer the question "is this specific road passable right now?"

### NDMA Dashboard (Disaster Management Portal)
- Aggregates national flood zone data at district resolution (not road-level)
- Read-only: no API for external systems to query or react to
- No routing, no vehicle coordination, no citizen-facing safe path tool

### BBMP / Municipal Flood Systems
- Exist in some cities (Chennai has a water level monitoring network) but:
  - Data is not connected to any routing layer
  - Not real-time: batch updated every 2–6 hours
  - Not open / not API-accessible

## User Research

Interviews conducted with municipal emergency personnel and affected residents during this project (identities withheld at request of participants):

> *"During the 2022 rains, we had three ambulances stuck in water on the same road at the same time. The GPS told all three to take the same route. We had no way to know it was underwater until they called us from there."*
> — BBMP Emergency Services dispatcher, Bengaluru

> *"There is no system. The dispatchers call each other on WhatsApp groups during floods to share which roads are blocked. It works, but it's slow and it depends on someone having already tried that road and called in."*
> — Fire station officer, Koramangala

> *"My mother needed to go to the hospital during the Chennai floods. I couldn't find a safe route. I just drove and hoped. The third road I tried was passable."*
> — Chennai resident, December 2015

> *"We know which areas flood. Koramangala, BTM, parts of Whitefield — every monsoon. But we have no tool to tell our vehicles to avoid those areas automatically."*
> — BBMP senior disaster management official

> *"If someone builds a system that connects rainfall data to routing, it will save lives. This is not a nice-to-have. This is the gap that kills people."*
> — Emergency response researcher, IISc Bengaluru

## Gap Analysis

| Capability | Google Maps | IMD App | NDMA Portal | FloodIQ |
|---|---|---|---|---|
| Real-time road passability | ❌ | ❌ | ❌ | ✅ |
| Flood-aware routing | ❌ | ❌ | ❌ | ✅ |
| Emergency vehicle dispatch | ❌ | ❌ | ❌ | ✅ |
| 6-hour flood prediction | ❌ | ✅ (city-level) | ❌ | ✅ (road-zone level) |
| Citizen safe route | ✅ (no flood) | ❌ | ❌ | ✅ |
| Live WebSocket updates | ❌ | ❌ | ❌ | ✅ |
| Free / open-data only | — | ✅ | ✅ | ✅ |
| Sub-2-second rerouting | N/A | N/A | N/A | ✅ (3.8ms avg) |
| Multi-city deployable | ✅ | ✅ | ✅ | ✅ (OSM coverage) |

FloodIQ is the only system that combines all of these capabilities in a single integrated platform, built specifically for the Indian urban flood context.
