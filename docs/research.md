1) Problem definition (within “Electricity in & to Arizona”)
Place a finite number of solar-augmented DC fast charging (DCFC) sites to (i) maximize access and equity for current EV drivers, (ii) minimize lifecycle cost to own/operate (including grid energy when solar is insufficient), (iii) ensure reliability under Arizona heat, and (iv) comply with corridor coverage expectations—while avoiding congestion/safety pitfalls.
Decision: locations and sizes (kW and #ports) of new stations.
Outputs: ranked site list, map, budget use, coverage metrics (share of AADT covered, corridor coverage, % population within X miles), station utilization/load profiles, and PV production vs. grid draw by month.
2) Why ZIP Code (ZCTA) granularity
•	City block is often too noisy for statewide datasets (AADT, crime, EV registrations, utility territory, hosting capacity proxies aren’t block-level statewide).
•	County is too coarse for siting and corridor spacing decisions.
•	ZCTA is the sweet spot: statewide coverage, linkable to ACS demographics and many agency datasets; compatible with corridor/traffic overlays; and operationally practical for sponsors/judges. Census.gov
3) Public datasets to use (and what each backs)
Existing EV infra & corridors
•	AFDC Station Locator + OCPI terminology (all U.S. stations, fuel type, status) for baseline supply & gaps. Alternative Fuels Data Center
•	FHWA Alternative Fuel Corridors (AFC) NTAD layer (Round 8, 2025 update) to measure corridor coverage and candidate interchange sites. geodata.bts.gov
•	ADOT EV Deployment Plans/NEVI for Arizona-specific siting priorities and constraints. (Use latest 2025 streamlined plan + 2023 plan for historical context.) Arizona Department of Transportation+1
Demand & accessibility proxies
•	ADOT AADT statewide layer (2023) to weight road segments by likely charging demand & to avoid creating new congestion hot spots. azgeo-open-data-agic.hub.arcgis.com
•	AZDOT Traffic Monitoring & TCDS/TMAS/HPMS context for methods/coverage. Arizona Department of Transportation
Solar yield & heat derating
•	NREL NSRDB (1998–2023) hourly irradiance & met data → monthly/annual PV yield per candidate site. Data.gov
•	NREL PVWatts API (V8) to translate irradiance + temperature into expected kWh (incorporates thermal effects). NREL Developer Network+1
•	DOE/NREL SAM documentation for performance & finance modeling (temp derating, losses). The Department of Energy's Energy.gov+1
•	Phoenix/NWS climate normals & extremes to parameterize heat-stress/derating and O&M cadence. Weather.gov
Grid, utility territories, & siting feasibility
•	APS & SRP service territory maps to check utility jurisdiction and programs. ArcGIS+2aps+2
•	Hosting capacity best-practice/atlas references to justify using utility HCA where available and to proxy constraints otherwise. The Department of Energy's Energy.gov+1
Safety & site security
•	City of Phoenix crime incidents (2015–present, daily updates); Tucson PD open data; AZ DPS Crime Statistics portal → build a “site risk” penalty and avoid high-risk blocks for public chargers. Phoenix Open Data+2ArcGIS+2
Population & equity
•	U.S. Census ACS (demographics, income, vehicles/HH) by ZCTA. Census.gov
•	EPA EJSCREEN (downloadable) to weight equity in scoring (e.g., higher benefit to underserved communities). US EPA
Environment / hazards / land
•	FEMA NFHL flood hazard to avoid flood-prone parcels. FEMA+1
•	BLM Arizona GIS for federal/public lands constraints and permitting context. gbp-blm-egis.hub.arcgis.com
EV performance & range constraints
•	EPA FuelEconomy.gov datasets & 2025 Guide for realistic usable ranges and consumption (kWh/100mi) across models. Fuel Economy+2EPA+2
Costs & economics
•	NREL DCFC cost/viability & levelized charging cost datasets; AFDC O&M guidance to parameterize capex/opex, demand charges, and PV/storage value. NREL Docs+2NREL Data+2
•	Peer-reviewed corridor DCFC cost study (California sites) to set realistic cost ranges and variance. ScienceDirect
•	EVI-Pro/EVI-Pro Lite & EVI-X (methods & APIs) for load profile generation from historical travel data assumptions. (We’ll use only the historical-behavior scenarios per your constraint.) Alternative Fuels Data Center+3NREL+3NREL Developer Network+3
Policy & siting rules of thumb
•	NEVI standards (2023 final rule) sets power/performance requirements;
•	2025 interim guidance gives more flexibility on the earlier “every 50 miles, within 1 mile of AFC” rule—still a useful spacing target/baseline constraint. electricera.tech+3Federal Register+3infrainsightblog.com+3
4) Factors (each tied to a public data source)
Access & demand
•	Coverage of AFC corridors and interchanges (site within 1 mi of corridor; spacing near ~50 mi as baseline, unless justified otherwise). geodata.bts.gov+1
•	AADT-weighted proximity to major roads and trip attractors; penalize very high-AADT curb sites that worsen congestion (favor existing parking/rest areas). azgeo-open-data-agic.hub.arcgis.com+1
•	Population & equity need by ZCTA (ACS + EJSCREEN). Census.gov+1
•	Existing station competition & gaps from AFDC; ensure coverage continuity and redundancy. Alternative Fuels Data Center
Technical performance
•	PV energy yield by site via NSRDB + PVWatts; incorporate temperature-driven derating and losses per SAM/PVWatts. Data.gov+2NREL Developer Network+2
•	EV range feasibility—ensure reasonable hop distances for popular models (EPA dataset for ranges/kWh/100mi). Fuel Economy+1
•	Grid feasibility—utility territory check (APS/SRP) and hosting capacity proxy/scoring (prefer feeders/areas with capacity or behind-the-meter PV+storage to mitigate). ArcGIS+2SRPNet+2
Risk, safety & resiliency
•	Crime risk avoidance/penalty (Phoenix/Tucson incidents; AZ DPS statewide). Phoenix Open Data+2ArcGIS+2
•	Flood risk avoidance via FEMA NFHL. FEMA
•	Extreme heat O&M uplift—cleaning, connector replacement, component derates (NWS climate; NREL PV performance loss factors and O&M guidance). Weather.gov+2NREL Docs+2
Costs
•	Capex: charger hardware, civil works, interconnection; use ranges grounded by NREL + peer-reviewed corridor study. NREL Docs+1
•	Opex: electricity tariff (incl. demand charges), routine maintenance/warranty per AFDC guidance; solar offsets reduce grid cost (NREL studies). Alternative Fuels Data Center+1
•	Realistic budget: parameterize scenarios using ADOT NEVI plan allocations and local utility rate contexts (include APS/SRP territory split and current price sensitivity). Arizona Department of Transportation+1
5) Hybrid ML + Optimization design
Data layer (ZCTA grid + candidate nodes)
•	Build candidate sites at: AFC interchanges (1-mile buffer), ADOT rest areas, park-and-rides, large public parking near arterials. (AFC/ADOT layers + TIGER roads/places.) Data.gov+3geodata.bts.gov+3Arizona Department of Transportation+3
ML module (historical-only features)
•	Target: “site score” ≈ expected utilization (kWh/day) at each candidate.
•	Features: AADT (and distance to high-AADT segment), population & income (ACS), current station density (AFDC), corridor buffer flag, travel-behavior proxy from EVI-Pro Lite weekday/weekend load shapes (use as engineered features, not future projections), crime risk, PV yield, flood risk, utility territory, EJ weight. US EPA+8azgeo-open-data-agic.hub.arcgis.com+8Census.gov+8
•	Models: Gradient-boosted trees or random forest for interpretability + SHAP to show factor importance (helps presentation).
•	Clustering: K-means or HDBSCAN to ensure geographic diversity and prevent selecting many proximate candidates in one metro before optimization.
Optimization module (Pyomo)
•	Type: Capacitated Facility Location / P-median hybrid with additional constraints.
•	Decision variables: open site (binary), number of DCFC ports per site, PV array size (kW), optional battery size (kWh).
•	Objective (multi-term, weights tunable):
o	maximize ML-predicted utilization & equity score,
o	minimize net present cost (capex + opex − PV savings),
o	penalize crime/flood risk and grid-capacity conflicts.
•	Hard constraints:
o	Corridor spacing (baseline ≤50 mi between DCFC along AFC; relaxable with penalty under 2025 guidance), within 1 mi of AFC where applicable. Federal Register+1
o	Coverage: ≥X% of population within Y miles of a DCFC node. (ACS) Census.gov
o	Grid/load: per-site max interconnection (proxy via utility/HCA references) and total program budget. The Department of Energy's Energy.gov
o	Site safety: exclude high-crime top decile & floodways. Phoenix Open Data+1
o	Thermal/uptime: ensure PVWatts monthly output meets M% of daytime station energy in at least Z months (the rest from grid). NREL Developer Network
•	Solver: HiGHS/CBC (open-source) via Pyomo; sensitivity runs for budget levels.
Energy sub-model
•	PV sizing with PVWatts (V8) per site, using NSRDB TMY/PSM V3; simple rule: size PV to meet a chosen fraction of annual DCFC energy (from ML-predicted kWh). SAM used to validate temperature derating and LCOE checks for a couple of “hero” sites in Phoenix and Flagstaff for presentation. NREL Developer Network+2PVWatts+2
6) Realistic budget & scenarios (examples the judges can follow)
•	Baseline (NEVI-style): $X M total; station design 4x 150–350 kW ports per site; cost per site drawn from NREL/peer-review ranges (present median & IQR and justify dispersion). NREL Docs+1
•	PV adders: 50–250 kW PV canopies per site sized by local yield; include O&M ($/kW-yr) and inverter replacements per NREL performance loss factors. NREL Docs
•	Operating cost: rate scenarios (APS vs SRP territory), TOU demand sensitivity; maintenance from AFDC O&M page. aps+2SRPNet+2
7) Validation & presentation checklist (what to show in 24 hours)
1.	Data provenance table with links (above).
2.	Map: current stations (AFDC), AFC corridors, AADT heatmap, ZCTAs, candidate nodes, proposed sites. Alternative Fuels Data Center+2geodata.bts.gov+2
3.	PV yield bars (per site) from PVWatts + heat derating notes. NREL Developer Network
4.	Equity & access: % population within Y miles before/after; EJSCREEN overlay. US EPA
5.	Budget sheet: per-site capex/opex with citations; LCOC (levelized cost of charging) vs. utilization. NREL Data
6.	ML feature importance (SHAP) explaining siting rationale.
7.	Optimization sensitivity: budget ±20%, corridor spacing tight vs. flexible (per 2025 guidance), APS vs SRP rates. infrainsightblog.com
8) How this addresses your “more factors” list
•	Heat durability: include temperature derate & O&M uplift using NREL performance references + NWS climate normals. NREL Docs+1
•	Traffic congestion: avoid super-high AADT frontage; prefer rest areas/parking just off ramps. azgeo-open-data-agic.hub.arcgis.com+1
•	Not too far apart: enforce AFC spacing baseline and population coverage constraints (relaxable under 2025 guidance). Federal Register+1
•	Avoid low-use remote areas: ML score integrates AADT, population, existing stations. azgeo-open-data-agic.hub.arcgis.com+1
•	Range feasibility: EPA ranges inform max hop distance and charger power selection. Fuel Economy+1
•	Security: exclude high-crime zones. Phoenix Open Data+1
•	Year-round power optimization: PVWatts/NSRDB by month and TOU alignment. NREL Developer Network+1
•	“Don’t spend more than you save”: compare PV-offset value and demand-charge mitigation against capex/opex; cite LCOC and O&M sources. NREL Data+1
•	Durability & resilience: avoid flood zones; heat derating and component replacement modeled. FEMA+1
9) Tooling stack you can use right now
•	Data wrangling/ML: Python (pandas, scikit-learn, shap).
•	Optimization: Pyomo + HiGHS/CBC.
•	Energy: PVWatts API + SAM for a couple of deep-dives. NREL Developer Network+1
•	Mapping: QGIS/ArcGIS Pro (AZGeo layers). AZGeo
________________________________________









Factors 
Demand & accessibility
•	Current network coverage (existing public chargers; gaps/overlap)
•	Traffic intensity (AADT) near candidate sites
•	Trip attractors (employment, retail, campuses, parks, airports)
•	Population density & car ownership
•	Equity need (income, multifamily housing, access to off-street parking)
•	Urban vs. rural accessibility
Spacing, range & corridor coverage
•	Max distance between fast chargers along key corridors
•	Detour distance from highway to site (≤ ~1 mile preferred)
•	EV range realism across common models (usable range, consumption)
•	Redundancy/resilience (backup options within a reasonable radius)
Site feasibility & land use
•	Parcel availability (public parking, rest areas, park-and-ride, transit hubs)
•	Zoning/land-use compatibility
•	Permitting complexity; jurisdiction (state, county, city, tribal, federal land)
•	Setbacks, visibility, ADA compliance
Safety & security
•	Crime risk (site-level incident history)
•	Lighting, passive surveillance, proximity to staffed facilities
•	Flood/fire/other hazards (avoidance or mitigation)
Grid & interconnection
•	Utility territory (APS, SRP, co-ops)
•	Hosting capacity / feeder constraints (or proxies)
•	Interconnection timeline/complexity
•	Tariff structure (TOU energy, demand charges, standby fees)
Solar resource & system performance
•	Solar irradiance (annual & seasonal)
•	Ambient temperature & thermal derating
•	Soiling, shading, and losses
•	Roof vs. canopy vs. ground-mount feasibility
Energy balance & storage (optional)
•	PV sizing vs. station load profile
•	Battery storage for peak shaving / resiliency
•	Expected PV fraction of annual energy
•	Grid draw profile (hourly/seasonal)
Costs & economics
•	Capex: site work, hardware (150–350 kW DCFC), switchgear, PV, storage
•	Opex: electricity (incl. demand), maintenance, networking, warranties
•	Incentives/subsidies (e.g., NEVI), make-ready contributions
•	LCOC / breakeven vs. utilization; sensitivity to rates and PV output
•	Budget constraints (program-level and per-site)
Operations & maintenance
•	Routine maintenance cadence in heat/dust
•	Parts replacement cycles (cables, contactors, inverters)
•	Uptime targets, SLAs, remote monitoring
•	Snow/ice at elevation (Flagstaff etc.) vs. desert heat (Phoenix/Tucson)
Traffic & user experience
•	Queueing risk / expected dwell times
•	Parking layout: pull-through for trailers, EV-only enforcement
•	Wayfinding/signage, driver amenities (restrooms, shade, Wi-Fi)
•	24/7 access, payment interoperability
Policy, standards & compliance
•	NEVI performance/spacing expectations (as baseline)
•	Electrical code, fire code, accessibility standards
•	Utility interconnection rules and metering
•	Environmental review thresholds (if any)
Environmental & community impact
•	Noise/visual impacts; canopy glare
•	Heat-island mitigation (shade canopies, trees)
•	Stormwater handling around pads/canopies
Resilience & reliability
•	Extreme heat design margins, de-rating in summer
•	Backup power / ride-through capability
•	Redundant sites along corridors and within metros
Data quality & modeling hygiene
•	Timestamp alignment and seasonality handling
•	Spatial resolution choice (ZCTA chosen over block/county)
•	Outlier handling (rare events, station outages)
•	Train/validation splits by geography to avoid leakage
ML features (historical-only)
•	AADT and distance to major arterials/highways
•	Population, income, housing type, EJ indicators
•	Existing station density & nearest-neighbor features
•	PV yield (monthly), temperature stats, hazard flags
•	Crime risk score, utility territory/tariff class
•	Points of interest density (trip attractors)
Optimization mechanics
•	Decision variables: site open/close, #ports, PV (and optional storage) size
•	Objective mix: maximize expected utilization & equity; minimize NPC/LCOC;
penalize crime/flood risk and weak grid locations
•	Hard constraints: corridor spacing, coverage (% pop within X miles),
grid capacity limits (or proxies), budget cap, hazard exclusions
•	Sensitivities: budget ±, tariff scenarios (APS/SRP), PV size, spacing rules




















Optimized Solar EV Charging Station Placement in Arizona
Plan for Optimizing Placement of Solar-Powered EV Charging Stations in Arizona
Introduction
Arizona’s fast-growing electric vehicle (EV) market and abundant sunshine present a prime opportunity to optimize the placement of solar-powered EV charging stations. In this hackathon project, our team will design a solution focusing on where to install solar-powered EV chargers across Arizona to maximize accessibility, efficiency, and sustainability. The goal is to ensure that EV drivers can easily find reliable charging (reducing “range anxiety”) while leveraging Arizona’s high solar potential to power the stations. We will incorporate a hybrid approach combining machine learning (ML) and optimization techniques to determine optimal locations, using publicly available data on travel patterns, EV adoption, solar resources, and more. The following sections outline the key factors to consider (with supporting data), relevant existing solutions and research, and our proposed ML-enhanced optimization strategy for this problem.

Key Factors and Public Data Inputs
To tackle optimal charger placement, we identified numerous factors backed by public data and research. These factors span demand and coverage, technical and environmental constraints, safety and accessibility, and economic feasibility. Each factor below is grounded in data from reputable public sources:
•	EV Adoption and Demand Distribution: Understand where EVs are concentrated and how many are on the road. Arizona is among the top EV-adopting states, with nearly 90,000 EVs registered as of 2023caranddriver.com. Major population centers (Phoenix, Tucson, etc.) and highways with heavy traffic will have higher charging demand. Public EV registration data (e.g., DOE’s AFDC or state reports) will inform how we weight locations – for example, Maricopa County likely has the most EVs, so more stations should be nearby. This ensures we “meet the needs of EV drivers” where demand is highestpowerflex.compowerflex.com. We will use Arizona’s EV registration statistics and maps of EV ownership by ZIP code (if available) as a starting point for demand hotspots.
•	Highway Travel Corridors and Coverage Gaps: A core requirement is enabling long-distance travel across Arizona. We must ensure chargers are spaced such that an EV can reliably go from one to the next on major routes without running out of charge. Federal guidelines (from the NEVI program) recommend fast chargers no more than 50 miles apart along designated highwaysazdot.gov. Arizona’s state EV plan follows these rules, ensuring stations at least every 50 miles and within 1 mile of highway exitsazdot.govazdot.gov. Using this as a constraint, we’ll map out Arizona’s interstates (I-10, I-17, I-40, etc.) and state routes to identify gaps where no charger exists within ~50 miles. Public data from the Alternative Fuel Corridors map and the DOE’s station locator will be used to find existing charger locations and then pinpoint underserved stretches. Our optimization will target filling these gaps to “reduce range anxiety by closing existing network gaps”azdot.gov.
•	Traffic Volume and Usage Patterns: Not all roads are equal – placing chargers on routes with higher traffic or popular travel destinations will yield greater utilization. We’ll incorporate Average Annual Daily Traffic (AADT) data from ADOT’s public traffic countsazgeo-open-data-agic.hub.arcgis.com to prioritize busy corridors and junctions. For example, highways connecting Phoenix to Flagstaff or Tucson have heavy usage and likely need more charging infrastructure than low-traffic rural roads. Remote areas with very low traffic may not justify multiple stations (or any, if an alternative route is nearby), since rural chargers tend to see low utilization and struggle to be financially viableplanetizen.com. In fact, an analysis in mid-2025 showed only ~45% of rural U.S. counties even have a fast charger, partly because private investors avoid low-use areas that can’t break even without subsidiesplanetizen.com. Thus, our model will consider demand density – focusing on highways and locations with sufficient travel volume, while possibly providing at least minimal coverage in remote stretches (for safety), but avoiding redundant stations where usage would be sparse.
•	Proximity to Amenities and Driver Comfort: A successful charging site offers more than electricity – drivers prefer locations where they can safely wait and have access to amenities. We will favor sites near stores, restaurants, rest stops, and restrooms, etc. Research shows co-locating chargers with amenities greatly increases usage: chargers within 500 m of dining saw 2.7× more monthly charging sessions, and those near grocery stores saw 5.2× more sessionsnext10.org. In surveys, 74% of EV drivers favored charging at rest stops, 71% at shopping malls, and 59% at restaurants over isolated locationsnext10.org. This is because while a car charges (especially at Level 3 fast chargers taking ~20-40 minutes), drivers appreciate having things to do. To incorporate this, we will use public data (or OpenStreetMap directories) to identify locations with existing amenities (travel plazas, shopping centers, parks, etc.). Strategically placing chargers near amenities not only improves user experience but also boosts station profitability, as evidenced by the Next10 reportnext10.orgnext10.org. This means our optimization will give extra weight to candidate sites that have nearby conveniences (or at least room to add them).
•	Site Accessibility, Safety, and Security: Charging stations must be accessible and safe for users. We should avoid placing chargers in areas that would impede traffic or be unsafe. For example, we wouldn’t put a charger in the middle of a busy street where cars might queue into traffic – instead, they should be in parking lots or designated pull-outs where vehicles can park out of the flow. Design guidelines note that vehicle and pedestrian traffic patterns around the site should be evaluated to ensure accessibility and safetyportal.ct.gov. We’ll look for locations with adequate space for cars to maneuver and queue without causing congestion. Additionally, personal safety is key: stations should be well-lit, visible, and in secure locations to encourage use at all hours. Best practices recommend installing chargers in highly visible, well-lit areas (for instance, “in front of a store” rather than behind a dark alley)thehartford.com. Proper lighting and visibility not only make users (especially at night) more comfortable but also deter vandalismevchargingsummit.cominchargeus.com. We will leverage data such as crime rates or existing lighting (where available) and prefer sites that are public and patrolled (e.g., highway rest areas, retail parking lots with security). Moreover, vandalism and theft is a consideration – chargers in isolated, “unsecure” spots are more likely to be damagedinchargeus.com. Mitigation measures include cameras and durable, tamper-resistant equipmentinchargeus.com, but our siting strategy will inherently lean toward secure, populated locations. In summary, any candidate location must be checked for adequate space, safe ingress/egress, and the ability to add lighting or surveillance if not already present (the NREL safety fact sheet highlights lighting and visibility as critical design elementsdriveelectric.gov).
•	Distance Between Stations (Range Coverage): This relates to both highway coverage and urban density. In cities, stations can be closer due to higher concentration of users, whereas on highways we adhere to the ~50-mile rule. We will explicitly include a distance constraint: no two adjacent stations on key routes should be more than the typical EV range apart. For instance, since many EVs have effective highway ranges of 150–250 miles, a 50-mile spacing offers plenty of cushionazdot.gov. We will use a graph of major travel routes and enforce maximum gap distances. Also, we should avoid over-clustering stations too closely where unnecessary – e.g., building multiple new stations in the same area when one would suffice for that locality. Instead, distribution should be balanced so that remote areas get at least one station for connectivity, but urban areas get enough stations to meet higher demand. Public maps of existing chargers will tell us where clusters already exist (e.g., metro Phoenix has many Level 2 chargers but might need more DC fast chargers). Our optimization can include a coverage objective: maximize the number of EVs (or vehicle-miles) covered by the network, given a budget of stations, ensuring no critical gap in distance.
•	Electrical Grid Capacity and Power Supply: Because these stations are solar-powered (with likely battery backup), they might be less dependent on the grid, but grid access is still relevant. Fast charging draws high power (a single 150 kW DC fast charger is standardazdot.gov), and if a station has multiple chargers it could easily require 600+ kW of capacityazdot.gov. Placing chargers in areas with sufficient electrical infrastructure (or planning for off-grid solutions) is important. Guidance from city planning suggests minimizing stress on the power grid by siting chargers where the local grid (transformers, distribution lines) can handle the loadc40knowledgehub.org. We will consult utility grid maps or substation locations if available, or use proxies like proximity to built-up areas (since rural grid nodes might be weaker). However, since we aim for solar-powered systems, each station will include solar panels (and possibly energy storage) to supply much of its energy. This means sites need physical space for solar arrays (e.g., a canopy over parking). Solar resource availability is a factor too – fortunately, Arizona has excellent solar irradiance nearly statewide. Phoenix, for example, receives about 35% more solar energy than a cloudy city like Chicagopalmetto.com. We will still consider micro-differences: northern Arizona (Flagstaff) has slightly cooler, sometimes cloudier weather (and shorter winter days) compared to the Phoenix or Yuma areas which are among the sunniest in the U.S. According to NREL data, Arizona’s annual solar potential is on the order of 6-7 kWh/m² per day (peak sun hours) in many regions, one of the highest in the countrypalmetto.com. This means virtually any Arizona location is viable for solar generation, though we might optimize panel tilt or capacity to account for seasonal variations (strong summer sun vs. weaker winter sun). We will use NASA/NREL solar maps or the NREL PVWatts database for site-specific solar output estimatespalmetto.com. The design will ensure solar panel capacity plus battery storage can meet the station’s needs during peak usage and at night. In summary, our siting will favor locations that either have grid tie-in available as backup or are sunny enough and spacious enough to support a standalone solar setup.
•	Climate and Durability Considerations: Arizona’s climate poses unique challenges. Extreme heat is a serious factor – much of Arizona experiences summer highs well above 100°F (38°C). High temperatures can degrade charging equipment performance and EV charging efficiency. Studies note that “extreme heat causes slower EV charging, higher energy use (due to cooling systems), and can shorten battery and equipment life”chargie.comairquality.org. Charger hardware can overheat or even temporarily shut down if not designed or sited properlyinchargeus.com. Also, intense sun exposure can wear out cable insulation and electronics over timeinchargeus.com. To combat this, we plan to integrate shading and cooling in our station design – for example, using solar canopies that both generate power and shade the chargers/vehicles. A real-world example is the Phoenix Zoo solar-covered EV charging station, which provides shade for 20 charging spots under a solar panel canopymedia.srpnet.commedia.srpnet.com. Our site selection will consider if a location has natural shade or if we can feasibly install a canopy. Additionally, monsoon weather (dust storms, heavy rains) means equipment should have high ingress protection (waterproofing) and be built sturdily. We will choose durable, weather-resistant components – many modern chargers are NEMA-rated for outdoor use, but placement in a flood-prone spot, for instance, would be unwise. We’ll use FEMA flood zone data to avoid low-lying areas. Finally, maintenance needs to be factored: remote stations should be accessible for maintenance crews. Overall, selecting sites where climate impacts can be mitigated (or are less severe, e.g., higher elevation areas are cooler) will improve reliability. This ties back to design: including routine inspection plans especially in summer months to catch heat-related wear earlyinchargeus.com is part of ensuring the “whole system should not break” prematurely.
•	Economic Feasibility and Costs: A solution isn’t truly optimized unless it’s cost-effective. We will incorporate budget constraints and aim to maximize impact per dollar. Key cost factors include hardware, installation, and operation/maintenance. Public cost data shows a single DC fast charger (150 kW) unit can cost around $75,000 (equipment only)portal.ct.gov, and installation (construction, wiring, etc.) can equal or exceed that, especially if multiple chargers are installed (though there are economies of scale for multi-charger sites). Solar panels and battery systems add to upfront cost, but reduce operating costs by supplying free renewable energy. We’ll gather data on solar EV charging station costs – for instance, a 50 kW solar array with storage might cost on the order of a few tens of thousands of dollars (we will look at sources like NREL or DOE reports for distributed solar+EV charger costs). Our objective is to not spend more than what the benefits justify. Benefits can be quantified as: electricity cost savings (solar energy replacing grid energy), revenue from charging fees, and societal/environmental benefits (harder to monetize in the model, but we note them). For ROI calculations, consider that a busy charger could dispense several hundred kWh per day; with electricity at say $0.15/kWh, and if charging fees are, e.g., $0.30/kWh, revenue might be ~$45/day for a single busy charger. We’ll use such data to estimate payback. High-utilization sites (e.g., along interstates or in city centers) will generate more revenue and better justify the investment than a rarely used rural site. This doesn’t mean we ignore equity in coverage, but perhaps those low-usage sites might need external funding. We will also look at public incentives: Arizona is receiving $76 million in federal NEVI funds to build out EV chargersazdot.gov, and there are likely state grants or utility programs as well. These can subsidize installations, effectively lowering the cost constraint in certain locations. A recent industry analysis noted that by leveraging subsidies and choosing high-traffic sites, operators can achieve over 25% annual ROI on charging stationssinoevse.com. While our project’s scope is not to maximize profit per se, it highlights that smart site selection (high traffic, potential subsidy eligibility) is key to financial sustainability. Therefore, our optimization will likely include a weighting or secondary objective for economic viability (for instance, we might prefer a site that is slightly less ideal geographically if it significantly lowers cost or qualifies for a grant). Ultimately, we will select a set of sites that fit within a given budget and yield the greatest benefit (in coverage and usage) for that investment. Part of our hackathon deliverable will include a brief cost report detailing how many stations we propose, estimated costs, and how those costs compare to projected usage or savings (e.g., how much grid electricity is offset by solar).
Public Data Sources: In summary, to support the above factors, we will rely on a variety of publicly available datasets and tools, including but not limited to:
•	U.S. DOE Alternative Fuels Data Center (AFDC): Provides the locations and details of existing charging stations and designated Alternative Fuel Corridors. This helps identify current infrastructure and gapsazdot.gov. The AFDC also publishes state-level EV registration countscaranddriver.com and other relevant statistics we can use for demand estimation.
•	Arizona Department of Transportation (ADOT) Data: ADOT’s EV Infrastructure Deployment Plan (2022) and updates (publicly accessible on azdot.gov) detail planned charger locations and contain maps of existing vs. proposed stations. We will use these as a reference and ensure our solution aligns with or intelligently deviates from the official plan. ADOT also provides Traffic Count Data (Average Annual Daily Traffic for highways) via their AZGeo Open Data portalazgeo-open-data-agic.hub.arcgis.com, which we will use to quantify traffic volumes at candidate sites.
•	NREL Renewable Energy Data: The National Renewable Energy Lab offers tools like PVWatts and the National Solar Radiation Database, which give solar irradiance and expected solar PV output by locationpalmetto.com. This will allow us to estimate how much solar energy each potential site could generate annually, informing how self-sufficient a solar charger at that site would be. NREL’s research publications (e.g., on charger safety and usage) will also guide some of our assumptionsinchargeus.comdriveelectric.gov.
•	Geospatial Data (GIS): We will utilize GIS layers such as land use/land ownership (to find available public lands or parking lots), locations of amenities (from sources like OpenStreetMap or city open data), and possibly demographic data (population density, commuter flows from Census or MAG regional data). These public datasets help in scoring sites for factors like nearby population or services.
•	Climate and Weather Data: Historical climate data from NOAA (for temperatures, extreme weather frequency) will back our considerations for durability. While we likely won’t need granular weather data in the model, referencing climate normals for different parts of AZ supports our planning (e.g., knowing that Phoenix averages 110°F in summer vs. Flagstaff’s 80s).
•	Cost and Technical References: We will use publicly available reports for EV infrastructure costs (for example, the Connecticut state guideline provided hardware cost tablesportal.ct.gov, and studies by ICCT or DOE on charging station economics). These give ballpark figures to feed into our model’s budget constraint and ROI analysis. Also, if available, we’ll use open data on electrical grid (utility rate tariffs, locations of substations or transmission lines from utilities’ public maps) to gauge where connecting a charger might be easier or harder.
By grounding our project in these public data sources, we ensure that our assumptions are realistic and that our solution meets the hackathon requirement of using public information (we will clearly cite at least two public datasets in our final report, as required).





Existing Solutions and Research Insights
Before finalizing our approach, it’s important to learn from existing optimized solutions and widely adopted practices in EV charging infrastructure. Several ongoing initiatives and studies provide guidance:
•	Arizona’s EV Infrastructure Plan (NEVI Program): As mentioned, Arizona is already planning a network of fast chargers along interstates with federal funding. The NEVI standards (every 50 miles, within 1 mile of highway, 4 ports of 150 kW each per station) have become a de facto standard for highway chargingazdot.govazdot.gov. Our project will build on this by possibly extending coverage to state highways or filling gaps NEVI doesn’t cover (like intrastate routes or urban charging deserts). The state plan’s method involved mapping existing stations and doing a “technical analysis with stakeholder input” to propose locationsazdot.gov. Those proposed locations (often at highway exits near towns) can serve as candidates for our model too. Essentially, NEVI provides a backbone; we can optimize beyond that by considering solar power integration and more granular placement off the highway exits (since private contractors will ultimately pick exact sitesazdot.gov).
•	Private Charging Networks: Companies like Tesla (Supercharger network) and Electrify America have deployed many stations nationwide, including Arizona. Tesla’s strategy historically was to place Superchargers roughly 120–150 miles apart on highways and near amenities (e.g., at shopping centers or restaurants just off interstates) so that long-range Teslas can travel easily. In Arizona, for example, Tesla Superchargers are in locations like Quartzsite, Kingman, Flagstaff, Tucson, etc., which correspond to logical route stops. We don’t have proprietary data on Tesla’s network optimization, but public observation shows their sites often have canopies (some solar) and are near food or retail. We will take a page from this by choosing sites near highway exits that have services (gas stations, eateries) whenever possible, as this mirrors what has been “widely adopted” in industry. Another example: Electrify America (a public network) often partners with big retail parking lots (Walmarts, shopping centers) for similar reasons – large parking area, amenities, and easy access from highways. These practical siting choices align with our factors list (amenities, safety, access) and validate them.
•	Solar-Powered Charging Projects: There are examples of solar EV charging in practice. The Phoenix Zoo project by SRP (Salt River Project utility) that we described is one – it combines 20 Level 2 charging ports under a solar-covered parking structuremedia.srpnet.com. The solar feeds into SRP’s grid (so it’s grid-tied solar), offsetting the energy used by the chargersmedia.srpnet.com. This demonstrates the viability of solar canopies for large installations in Arizona’s sun. Another example is the use of stand-alone solar EV charging units in some Arizona communities: for instance, the City of Glendale tested a portable solar EV charger unit that can charge two vehicles using solar+battery (as reported by the Arizona Technology Council)aztechcouncil.org. These are effectively off-grid and can be relocated. While smaller scale, they illustrate a solution for remote or temporary needs. Our plan leans towards more permanent stations, but we could incorporate such units for remote spots where grid connection is too costly. Overall, solar integration in EV stations is increasingly common – not only for power but also to provide shade (a critical factor in Arizona). We will look at case studies from other hot regions (like California or the Middle East) for best practices on cooling and panel maintenance (to deal with dust, etc.). The success of these projects indicates that our solar-powered approach is realistic.
•	Research on Optimal Charger Placement: The field of Operations Research and Transportation Planning has many studies on this problem. Traditionally, it has been tackled as a location optimization problem (like variations of the Facility Location or Set Covering problem, with constraints for coverage and capacity). Widely used methods include GIS-based Multi-Criteria Decision Making (MCDM) – for example, researchers use GIS layers to score every potential site on criteria such as proximity to major roads, population density, land cost, traffic volume, and power availabilityarxiv.org, and then select the best-scoring sites. Techniques like Analytic Hierarchy Process (AHP) and TOPSIS have been “widely adopted” to weight and rank charger locations in past studiesarxiv.org. These methods rely on expert-set weights for each factor. We can draw from this by initially scoring locations with a weighted sum of factors (our list of factors effectively covers similar criteria). However, purely static MCDM can be limited, which is why we plan to enhance it with ML for data-driven weighting. Recent research trends incorporate machine learning to improve site selection. In fact, a 2025 review notes that ML techniques (supervised learning, clustering, and even reinforcement learning) are being applied to optimize EV charger placement, integrating “spatial, demographic, technical, and environmental considerations”papers.ssrn.com. For example, studies have trained models to forecast charging demand in different areas based on data like existing station usage, land use, and population – essentially predicting where a new station would get the most usearxiv.org. Some projects use clustering algorithms on trip data or commute flows to find central points to serve many drivers. Others employ reinforcement learning (RL) where an agent “learns” where to add stations by simulating EV drivers’ behavior – one case study in Hanoi showed an RL-based strategy could reduce average waiting times by over 50% compared to a baselinearxiv.org. These advanced methods underscore the value of combining data and simulation with optimization. While implementing deep RL in a 24-hour hackathon is likely too ambitious, we can incorporate simplified versions of these ideas (e.g., simulation of driver paths to test our network’s performance). In summary, existing literature provides both the criteria we should consider and novel approaches (ML, GIS, OR techniques) that we can leverage. Our plan is to stand on the shoulders of these works – using a proven optimization formulation, and enhancing it with machine learning for better accuracy and adaptability.



Proposed ML-Enhanced Optimization Approach
Given the above factors and insights, we propose a hybrid approach that merges data-driven machine learning analysis with classical optimization modeling. This approach will allow us to handle the complex criteria involved and arrive at a well-justified solution. We considered multiple methodologies and chose the hybrid ML+OR strategy as the optimal path for this challenge, balancing sophistication with practicality (keeping in mind the 24-hour hackathon timeline and available data). Below we outline the approach in steps, and explain why it’s preferred over alternatives:
1. Generate Candidate Locations: First, we will enumerate potential sites where a charging station could be installed. These might be highway exit areas, popular destinations (malls, parks), and gaps along major routes. We’ll likely generate a list using GIS – e.g., every interstate exit, every town above a certain population, every 50-mile interval on key highways, plus some strategic city locations (like downtown parking garages or university campuses). This initial list might be a few hundred candidates statewide. (We’ll ensure these are on publicly accessible land or have willing hosts, as per data available – for hackathon scope we assume if it’s a public location like a rest area or parking lot, it’s a viable site.)
2. Feature Extraction for Candidates (Data for ML): For each candidate site, we will compile the relevant factor data: e.g., distance to nearest existing charger, traffic volume, population within X radius, number of nearby amenities, solar irradiance, distance from highway, etc. This creates a feature vector for each site. We will use public datasets as described to fill these values.
3. Machine Learning Demand Prediction: Using the features above, we plan to employ an ML model to predict the expected utilization or “score” of each candidate site. For instance, we could frame it as a regression problem: predict the expected number of charging sessions per day a station at that site would get. Training such a model requires data – we might use data from existing chargers (if available publicly, e.g., some cities release utilization data, or we use proxies like nearby EV registrations). If comprehensive training data is hard to get in 24 hours, an alternative is to use unsupervised learning: apply a clustering algorithm to group similar areas and identify which clusters likely indicate high demand (e.g., cluster by population and traffic – clusters with high values are high-demand). Another ML approach is a ranking model: we could train a model (even based on expert labels or proxy metrics) to rank sites by suitability. The ML component is useful because it can capture nonlinear relationships among factors that a simple weighted sum might miss. For example, it might learn that a site needs both high traffic and some amenities to truly have high usage – not just one or the other. Recent studies indeed emphasize combining environmental and behavioral data via ML to better predict charging needspapers.ssrn.comarxiv.org. We will likely keep the ML model relatively simple (perhaps a random forest or gradient boosting regressor using a dataset of known station performances from analogous regions). This ML step helps us quantitatively estimate demand for each site, which we can then feed into the optimization. It’s a more data-driven way to assign weights than arbitrary point scoring.
4. Optimization Model Formulation: With candidate sites and an estimated “utility” or demand score for each, we will formulate an optimization problem to select the best sites under given constraints. This is essentially a facility location optimization. A possible formulation is:
•	Decision variables: x_i = 1 if we build a station at candidate site i, 0 if not.
•	Objective: Maximize total “benefit”. Benefit can be the sum of demand scores (so we maximize expected usage served), or a combination of coverage and score. We might formulate it as a weighted sum: e.g., maximize (α * total demand served + β * number of EVs within 50 miles covered).
•	Constraints:
o	Budget constraint: ∑(cost_i * x_i) ≤ Budget. (We include installation cost for each site; we might assume a uniform cost per station for simplicity, or include site-specific adjustments if some sites are inherently costlier). If we don’t have a strict budget number, we could instead constrain the number of stations (e.g., select 20 sites out of the list) or require cost-benefit threshold.
o	Coverage constraints: ensure key routes are covered. For example, for each critical highway segment, at least one station is installed within that segment. Or more directly, ensure the distance between consecutive stations on each route is ≤ 50 miles (this may be handled by pre-selecting candidates appropriately).
o	Distance constraints: potentially enforce a minimum distance between chosen stations if needed to avoid clustering (though this might be naturally handled by the demand scoring, we can add it if the model tries to pick too many sites in one city).
o	Technical constraints: e.g., limit to X stations per city if needed, or ensure at least Y stations in rural vs urban (if equity is a concern).
o	Solar constraint is mostly about ensuring the site has enough sun; in Arizona that’s generally fine so we likely don’t need a hard constraint for it. Instead, solar viability is reflected in the demand score if we downweight sites that can’t generate year-round power (e.g., heavily shaded canyon, if any).
We will solve this as an integer linear programming (ILP) or mixed-integer problem. The problem size is moderate (hundreds of candidates), which is solvable with modern solvers (CBC, Gurobi, etc.). We will likely use Pyomo or PuLP in Python to model the ILP, since those are accessible open-source toolsampcontrol.io. This approach ensures an optimal selection of sites given our input data and constraints, rather than a purely heuristic selection.
5. Evaluation of Solutions: Optimization will give us a chosen set of locations. We will then evaluate how this solution performs on key metrics, possibly using simulation or simple calculations:
•	Check that all major travel corridors are indeed covered (no gap >50 miles).
•	Estimate how many EV drivers are served: using the demand scores or population coverage from our data, sum up how many EVs likely have access to the network.
•	Calculate the expected usage (sessions/day) and compare it to station capacity (we might assume each station can handle e.g. 4 cars simultaneously, maybe ~100 sessions a day max with fast chargers). This ensures we didn’t under-provide in high demand areas.
•	Compute rough economics: total cost vs. total kWh delivered (from demand estimates) to see cost per kWh or ROI. If something looks off (e.g., one station costs a lot but serves very few), we might adjust constraints to force a better balance.
•	Scenario tests: If time permits, we can simulate a few scenarios (e.g., EV growth in 5 years doubling demand in cities – does our network still hold up?). Or simulate a simple “road trip” model to ensure one can drive from any major point A to B using our stations.
Why a Hybrid ML + Optimization Approach? We weighed a few approaches before settling on this:
•	Approach A: Pure Optimization with Manually Set Weights. We could have done a multi-criteria optimization by assigning a score to each factor (like weight for traffic, weight for population, etc.) and maximizing that. However, setting those weights correctly is difficult and subjective. ML offers a way to derive weighting from data (learning from how existing stations perform), which is more objective. Pure OR without ML might oversimplify complex relationships or miss hidden factors.
•	Approach B: Heuristic or Greedy Placement. Another approach is a greedy algorithm (iteratively pick the best next location based on some criteria) or using genetic algorithms to evolve a solution. While these can find decent solutions, they don’t guarantee optimality and might require a lot of tuning. Given we have powerful ILP solvers and a manageable problem size, it’s better to mathematically optimize rather than rely on heuristics alone. We will, however, use domain knowledge to intelligently limit candidates and constraints, which keeps the ILP solvable.
•	Approach C: Full Simulation/Agent-Based Model with Reinforcement Learning. As research suggests, one could simulate EV movements and use RL to place stations optimallyarxiv.orgarxiv.org. This is very intriguing because it could capture dynamic effects (like congestion at stations). But doing this from scratch is complex and likely infeasible within hackathon time. Instead, our hybrid plan captures some benefits of ML (learning from data) and OR (clear optimal solution) without diving into full-blown simulation. It’s the most realistic approach for this competition – leveraging readily available tools (scikit-learn for ML, Pyomo for OR) and data, and it aligns with how many planning problems are solved in industry (often called an “analytics” or “predict-then-optimize” approach).
By combining ML predictions with OR optimization, we ensure that data informs our decision-making, and then optimization rigorously picks the best set. This hybrid approach is increasingly common in infrastructure planningarxiv.org, leveraging the strengths of both techniques. We anticipate that this method will yield a solution that is both quantitatively justified and practically robust.


Implementation Plan and Conclusion
To implement our plan within the hackathon timeframe, we will divide tasks among team members (taking advantage of a mix of skills: at least one member with operations research expertise and one with data science/ML skills, as recommended). Key steps include data gathering/processing, model training, and optimization coding. We’ll make use of open-source tools and languages (Python for both ML and OR, possibly using libraries like pandas, scikit-learn, and Pyomo/Gurobi). We will also prepare a concise presentation and a report of our findings, per hackathon requirements. The presentation will highlight the defined problem, our approach, and results with visuals like maps or charts (creatively showing the optimized station locations and their solar impact). We’ll ensure to cite all data sources used, demonstrating the use of at least two public datasets as required (in fact, we have several, from ADOT, NREL, DOE, etc.).
In conclusion, our plan addresses the theme “Electricity in and to Arizona” by proposing a network of solar-powered EV charging stations optimized for Arizona’s unique conditions. By exploring a broad range of factors – from technical constraints like distance and power, to human factors like convenience and safety – and backing them with public data, we increase our solution’s credibility and effectiveness. The incorporation of a machine learning hybrid optimization approach sets our project apart, showing we can innovate beyond straightforward methods and handle complexity intelligently. We aim to deliver a completed project within 24 hours that is not “perfect” in every detail but is excellent in its holistic approach, demonstrating the power of analytics and optimization to solve real-world sustainability challenges in transportation.
Through this project, not only do we create a blueprint for EV infrastructure in Arizona, but we also gain experience in a highly relevant, resume-worthy endeavor – exactly the kind of differentiator the hackathon sponsors intended for participants. We are excited to execute this plan and contribute to Arizona’s electric mobility future with a creative, data-driven solution.





AZ datasets request
Arizona first, public data catalog mapped directly to the siting factors we’ve been using for solar powered EV fast charging. Every entry is publicly accessible (API/CSV/GeoJSON/feature service or PDF) and scoped so you can actually download and model with it.
How to read this: grouped by factor → dataset (publisher) → what you get → why it matters (for your optimization). I kept it realistic (state + metro + national sources that cover AZ). Citations are clickable.
________________________________________
A) Demand, trip patterns & existing activity centers
•	Traffic volumes (AADT & truck mix) — ADOT HPMS/AADT
Road centerlines with 2024/2023 AADT, truck AADT, functional class, NHS, lanes; feature services and dashboard. Supports demand weighting and corridor coverage constraints. AZGeo Data+2Arizona Department of Transportation+2
•	Work/home flows (commuter O–D) — U.S. Census LEHD LODES
Block to block residence↔work flows (2002–2022), plus OnTheMap/LED Extraction for tract/ZIP aggregations. Use to locate all day chargers near job clusters and to size Level 3 vs. Level 2. LEHD+1
•	Commute catchments (Phoenix region) — MAG Commute Shed Reports
30 minute morning commute sheds for key intersections; quick proxy for daytime demand and reach. Maricopa Association of Governments
•	Park and Ride lots (Valley Metro / ADOT)
Park and ride facility points (great for colocating chargers where dwell time is predictable). Valley Metro Data Hub
•	Interstate rest areas (rural dwell time) — ADOT
Locations/attributes of state rest areas—prime rural DCFC candidates. Arizona Department of Transportation
•	Airports (major trip generators) — AZGeo subset of FAA Airports
Statewide airport points from FAA, filtered to Arizona. Arizona Sun Cloud
•	Hospitals & 24/7 facilities — Arizona Department of Health Services (ADHS) GIS
State licensed hospital locations (monthly updates). Useful for “always on” demand & resilience siting. ADHS GIS Portal
________________________________________
B) Existing EV charging & corridor rules
•	Public & private EV station locations — DOE/NREL AFDC Station Locator
Daily updated stations dataset (all fuels, filter to electric). Download via BTS/NTAD feature service or NREL API. Use for “coverage gap,” nearest neighbor, competitive density, uptime fields, connector types, kW. Geodata BTS+2Alternative Fuels Data Center+2
•	Stations along FHWA Alternative Fuel Corridors — AFDC corridors table
For corridor compliance checks and 50 mile spacing diagnostics (even as federal guidance evolves). Alternative Fuels Data Center
•	NEVI minimum standards & definitions — FHWA Final Rule / eCFR
The authoritative specs (power levels, uptime, interoperability, access). Use to check feasibility/compliance of candidate sites. Federal Register+1
•	Arizona’s NEVI plan (what’s funded/planned) — ADOT 2025 EV Plan Update
State approved plan (Oct 2025) and station roadmap to coordinate with (avoid duplicative siting). Arizona Department of Transportation
________________________________________
C) EV adoption (to weight demand by local fleet)
•	EV registrations by state (time series) — DOE AFDC/NREL
State counts (rounded; 2016–2024+) for macro weighting and adoption curves. Alternative Fuels Data Center+1
•	Arizona EV count (state budget context) — Arizona Legislature fiscal note citing ADOT
Recent point in time EV count (e.g., ~72.3k EVs referenced) for cross check. Arizona Legislature
•	State EV registrations dataset (open access mirror) — Open Energy Data Portal (Atlas Public Policy)
Public CSV compilation for many states; useful when you need a consistent ingest. (Confirm AZ coverage in current drop.) openenergyhub.ornl.gov
________________________________________
D) Socio demographics, driveway access & equity
•	ACS 5 year (2019–2023) via API — U.S. Census Bureau
Pull vehicles per household (DP04/DP03), tenure (renters/owners), household income, multi unit share to proxy home charging access and pricing sensitivity; tract/ZIP/ZCTA levels. Census.gov+1
•	ACS vehicle availability (ready made layer) — Esri curated from ACS
Tract level households by # of vehicles—quickly flags low car/low driveway areas with higher public charging reliance. ArcGIS
•	EJSCREEN (indexes & technical docs) — U.S. EPA
EJ indexes and climate/health indicators at block group resolution for equity scoring & benefit allocation; use 2024 public release files and 2.3 tech doc. (Note: the interactive site changed in 2025; data files/tech docs remain publicly accessible.) Data.gov+1
________________________________________
E) Siting feasibility: land use, parcels & public land options
•	City owned parcels (Phoenix) — City of Phoenix Open Data / EGISHub
City owned properties where public chargers can be permitted faster; includes a browsable map and GeoService. Phoenix Open Data+1
•	Parcels (Phoenix) — City of Phoenix
Parcel boundaries/attributes (CSV/GeoJSON/shape) for precise siting and cost modeling. Phoenix Open Data
•	Pima County (Tucson area) Open GIS — Pima County Geospatial Data Portal
Broad catalog (parcels, zoning, transportation, flood control layers). gisopendata.pima.gov
•	City of Tucson Open Data — City of Tucson
Hub for zoning/land use and facilities in Tucson jurisdiction. gisdata.tucsonaz.gov
________________________________________
F) Environmental & climate hazards (durability, insurance, resilience)
•	Floodplains — FEMA National Flood Hazard Layer (NFHL)
Flood zones and base flood elevations to screen out flood prone sites. FEMA
•	Wildfire hazard potential (2023) — USFS WHP
Continuous/classified wildfire hazard rasters—avoid very high risk areas or harden sites. U.S. Forest Service Data+1
•	Extreme heat / heat vulnerability — ADHS statewide hub & Tucson HVI
State heat resource hub + Tucson’s tract level heat vulnerability index to calibrate thermal derate assumptions and maintenance cycles. State of Arizona+1
•	NOAA Storm Events / climate normals — NCEI
Historic heat, wind, monsoon, lightning for O&M risk; climate datasets indexable to stations. NCEI+1
________________________________________
G) Grid context, utility territories, reliability & tariffs
•	Electric retail service territories / transmission & substations — HIFLD (DHS)
Transmission lines & substations (≥69 kV), and retail service territories—use to identify interconnection partners and proximity. hifld-dhs-gii.opendata.arcgis.com+2ArcGIS+2
•	Reliability metrics (SAIDI/SAIFI) — EIA 861 & Electric Power Annual
State/utility reliability indices for resilience scoring and backup sizing. U.S. Energy Information Administration+1
•	Tariffs & price plans (commercial/EV) — APS / SRP / TEP
Time of use + demand charge structures and TEP EV specific plans for revenue modeling and optimal battery buffering. aps+2SRPNet+2
•	Charging economics & capex/opex references — NREL & AFDC
DCFC viability and cost drivers; O&M guidance (network fees, uptime). Use for realistic cost priors in the optimization. NREL Docs+1
________________________________________
H) Solar resource & ambient temperature (PV sizing, thermal derate)
•	Solar irradiance & TMY weather — NREL NSRDB
High resolution irradiance + meteorology for PV yield and temperature related charger/array derates; API & bulk download. NSRDB
________________________________________
I) Safety & security context (for vandalism/lighting risk + traffic safety)
•	Crash trends & project level crash querying — ADOT ACIS & MAG
Training & dashboards to pull intersection/segment crashes; helps avoid unsafe ingress/egress or improve design. Arizona Department of Transportation+1
•	City open data portals (crime/security proxies) — Phoenix & Tucson
Use incident layers where available (or at least city facility layers) to proxy lighting/security context and site operations. Phoenix Open Data+1
________________________________________
J) What else you might want (optional, still public)
•	Alternative Fueling Stations (daily) — BTS NTAD mirror / FeatureServer
A maintained ArcGIS service mirroring AFDC—handy for direct GIS joins/filters. ArcGIS Services
•	Joint Office EV Stations resource — quick view and links to tech specs. Energy and Transportation Office
________________________________________
How these datasets cover your stated factors
•	Spacing & reachability: ADOT AADT + AFDC stations + corridor table + LEHD → enforce min/max spacing, reachable with typical EPA ranges (pair with EV model data) and prioritize high flow segments. LEHD+3AZGeo Data+3Geodata BTS+3
•	Avoid busy streets / traffic conflict & safety: AADT + crash querying; choose parcels with safe ingress/egress away from conflict points. AZGeo Data+1
•	Not too far apart in remote areas: Rest areas & Park and Ride anchor rural and commuter spacing. Arizona Department of Transportation+1
•	Security: City open data + hospital/airport presence (lighting/activity) as proxies where crime layers are limited. Arizona Sun Cloud+3Phoenix Open Data+3gisdata.tucsonaz.gov+3
•	Durability (heat, wildfire, flood): WHP 2023, NFHL, NOAA, heat vulnerability layers → site hardening and O&M assumptions. climateaction.tucsonaz.gov+3U.S. Forest Service Data+3FEMA+3
•	All year power balance for solar powered sites: NSRDB (irradiance/TMY) + NOAA + tariff data → PV & storage sizing, thermal derates, and demand charge mitigation. NSRDB+2NCEI+2
•	Financial realism: Tariffs (APS/SRP/TEP) + NREL cost/O&M → capex/opex and pricing/take rate stress tests. Alternative Fuels Data Center+4aps+4SRPNet+4
•	Equity and driveway access: ACS (renters, multi unit, vehicles/HH, income) + EJSCREEN for equitable coverage scoring. Census.gov+2ArcGIS+2
•	Grid interconnection feasibility: HIFLD substations/transmission + service territories + EIA reliability to avoid weak feeders and to justify buffer storage where reliability is lower. U.S. Energy Information Administration+3hifld-dhs-gii.opendata.arcgis.com+3ArcGIS+3
•	Permitting & footprint: City owned parcels, county GIS (parcels/zoning) to short circuit siting delays. Phoenix Open Data+1
________________________________________
Download & modeling tips (so you can move fast)
•	Pull once, cache, and version: For feeds with frequent updates (AFDC, AADT dashboards), pull nightly, version the parquet/geojson, and keep a “competition freeze” snapshot to ensure historical only modeling, per rules. Geodata BTS+1
•	Standardize geographies: Normalize everything to census tracts for scoring (ACS/EJSCREEN/LODES), then join to parcels/segments for the optimizer. Census.gov+1
•	Use tariffs as scenarios: Build at least three tariff cases (APS/SRP/TEP), each with on/off peak and demand charge assumptions, and combine with NSRDB monthly profiles for solar powered variants. NSRDB+3aps+3SRPNet+3

