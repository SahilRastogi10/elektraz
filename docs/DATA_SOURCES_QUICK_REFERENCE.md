# Data Sources Quick Reference Guide

## Summary of Findings

| Source | Status | Current | Recommended | Action Required |
|--------|--------|---------|-------------|-----------------|
| **AADT** | ✗ BROKEN (403) | 2020 data | AZGeo Hub 2023 | Update URL + extract FS endpoint |
| **NFHL** | ✗ BROKEN (timeout) | FEMA timeout | ArcGIS Online FS | Update URL immediately |
| **Park & Ride** | ✗ BROKEN (400) | Valley Metro | Valley Metro GeoCenter | Update URL + get FS endpoint |
| **AFDC** | ✓ WORKING | developer.nrel.gov | Same (need API key) | Register API key (optional) |
| **Census ACS** | ✓ WORKING | Census API | Same (optional key) | Register API key (optional) |
| **EJSCREEN** | ✓ AVAILABLE | EPA FTP | Zenodo archive | Update URL for reliability |

---

## Critical Changes Required

### 1. NFHL - HIGHEST PRIORITY (Easiest Fix)

**Current:**
```
https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28
```

**Recommended:**
```
https://services.arcgis.com/2gdL2gxYNFY2TOUb/arcgis/rest/services/FEMA_National_Flood_Hazard_Layer/FeatureServer/0
```

**Why:** Current endpoint times out. Recommended is on reliable Esri infrastructure.

**Files to Update:**
1. `configs/default.yaml` - Line 30
2. `src/data/dataloader.py` - Line 74

---

### 2. AADT - MEDIUM PRIORITY (Need FS Endpoint Extraction)

**Current:**
```
https://services6.arcgis.com/clPWQMwZfdWn4MQZ/arcgis/rest/services/AADT_2020_gdb/FeatureServer/0
```

**Recommended:**
```
https://azgeo-open-data-agic.hub.arcgis.com/datasets/azgeo::aadt-2023-1
```

**Note:** May need to extract the actual FeatureServer URL from AZGeo Hub

**Files to Update:**
1. `configs/default.yaml` - Line 23
2. `src/data/dataloader.py` - Line 68

---

### 3. Park & Ride - MEDIUM PRIORITY (Need FS Endpoint Extraction)

**Current:**
```
https://services1.arcgis.com/Hp6G80Pky0om7QvQ/arcgis/rest/services/Park_and_Ride/FeatureServer/0
```

**Recommended:**
```
https://geocenter-valleymetro.opendata.arcgis.com/datasets/valley-metro-park-and-rides
```

**Fallback (if direct FS endpoint needed):**
```
https://maps.phoenix.gov/pub/rest/services/Public/ParkAndRide/MapServer/0
```

**Files to Update:**
1. `configs/default.yaml` - Line 33
2. `src/data/dataloader.py` - Line 81

---

### 4. EJSCREEN - LOW PRIORITY (Optional Data)

**Current:**
```
https://gaftp.epa.gov/EJSCREEN/2024/EJSCREEN_2024_StatePctile.csv.zip
```

**Recommended:**
```
https://zenodo.org/records/14767363
```

**Why:** EPA tool discontinued. Zenodo is permanent archival.

**Files to Update:**
1. `configs/default.yaml` - Line 36
2. `src/data/dataloader.py` - Line 100

---

## API Key Status

### NREL AFDC
- **Current Status:** WORKING with DEMO_KEY
- **Action:** Optional - register free key for production
- **URL:** https://developer.nrel.gov/signup/
- **Impact if not done:** Rate limited to 1000 requests/day

### Census API
- **Current Status:** WORKING without key
- **Action:** Optional - register free key for better performance
- **URL:** https://api.census.gov/data/key_signup.html
- **Impact if not done:** IP-based rate limiting

---

## Code Update Template

### `configs/default.yaml` changes:

```yaml
data:
  # Line 23 - AADT
  adot_aadt_url: "https://azgeo-open-data-agic.hub.arcgis.com/datasets/azgeo::aadt-2023-1"
  
  # Line 30 - NFHL
  nfhl_url: "https://services.arcgis.com/2gdL2gxYNFY2TOUb/arcgis/rest/services/FEMA_National_Flood_Hazard_Layer/FeatureServer/0"
  
  # Line 33 - Park & Ride
  valley_metro_pr_url: "https://geocenter-valleymetro.opendata.arcgis.com/datasets/valley-metro-park-and-rides"
  
  # Line 36 - EJSCREEN
  ejscreen_csv_zip: "https://zenodo.org/records/14767363"
```

### `src/data/dataloader.py` changes:

Update lines 66-104 in the `_init_sources()` method with the recommended URLs above.

---

## Testing Commands

```python
# Test NFHL endpoint
import requests
url = "https://services.arcgis.com/2gdL2gxYNFY2TOUb/arcgis/rest/services/FEMA_National_Flood_Hazard_Layer/FeatureServer/0/query"
params = {"where": "1=1", "f": "json", "resultRecordCount": 1}
r = requests.get(url, params=params, timeout=10)
print(f"NFHL Status: {r.status_code}")

# Test AFDC endpoint
url = "https://developer.nrel.gov/api/alt-fuel-stations/v1.json"
params = {"api_key": "DEMO_KEY", "state": "AZ", "fuel_type": "ELEC", "limit": 1}
r = requests.get(url, params=params, timeout=10)
print(f"AFDC Status: {r.status_code}")

# Test Census endpoint
url = "https://api.census.gov/data/2023/acs/acs5"
params = {"get": "NAME,B08201_001E", "for": "zip code tabulation area:*", "limit": 1}
r = requests.get(url, params=params, timeout=10)
print(f"Census Status: {r.status_code}")
```

---

## Special Notes

### AADT Data Extraction
- AZGeo Hub uses a catalog interface
- May need to visit webpage and extract FeatureServer URL programmatically
- Alternatively, check if `https://services.arcgis.com/[org_id]/arcgis/rest/services/AADT_2023/FeatureServer/0` pattern works

### Park & Ride Data
- Valley Metro GeoCenter is official source for Phoenix metro area
- Phoenix City endpoint is alternative for city-only coverage
- Both may require endpoint extraction from Hub interface

### FEMA NFHL Optimization
- Recommended approach: use Arizona bounding box instead of "1=1" WHERE clause
- Or: use smaller resultRecordCount (1000 instead of 2000) for pagination
- Data updates monthly - cache for 7 days is appropriate

### EJSCREEN Note
- EPA discontinued tool on Feb 5, 2025
- Data still accessible via Zenodo (permanent archive)
- Consider adding fallback to EPA FTP in code

---

## Resources

- AZGeo Hub: https://azgeo-open-data-agic.hub.arcgis.com/
- Valley Metro GeoCenter: https://geocenter-valleymetro.opendata.arcgis.com/
- FEMA NFHL Viewer: https://www.arcgis.com/apps/webappviewer/index.html?id=8b0adb51996444d4879338b5529aa9cd
- NREL AFDC API: https://developer.nrel.gov/docs/transportation/alt-fuel-stations-v1/
- Census API Guide: https://api.census.gov/data/2023/acs/acs5.html
- Zenodo: https://zenodo.org/records/14767363

---

**Report Date:** 2025-11-21
**Priority Order:** NFHL (Critical) → AADT (High) → Park & Ride (High) → EJSCREEN (Low)
