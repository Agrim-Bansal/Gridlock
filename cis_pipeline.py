"""
CIS Prediction Pipeline — 50 Zones (6-Hourly Congestion)
==========================================================
Prediction target: April 1, 2024 (Monday)

API strategy:
  Day 1: March 31, 2024 (Sunday — previous day)     → 4 slots (6am,12pm,6pm,12am)
  Day 2: March 25, 2024 (Monday — same weekday)      → 4 slots
  Freeflow: 5 calls (non-traffic, timeless)

  Traffic calls: 4 slots × 5 batches × 2 days = 40 calls (of 100)
  Freeflow calls: 5 (of 100 non-traffic pool)
  Nearby API: 50 calls
  Reverse Geocode: 50 calls

CIS = predicted_vpd × (congestion_ratio - 1)^1.25 × junction_boost × poi_weight
"""
import math, time, requests, json, os
import numpy as np
import pandas as pd
from collections import Counter

# ================================================================
# CONFIG
# ================================================================
CLIENT_ID     = "96dHZVzsAus7mW-gxZr5HCFK4rbTQMhgdTkhXlxa0v5p-2P9uUAcSo6g5XOAgQr1i1GseFvh-0XfcwuuCmS2jA=="
CLIENT_SECRET = "lrFxI-iSEg9uwVuPvhenKjWJ-MSdzBT3Glkr-r0QsB9SdkaoXUY5qm2jMBv_H2zcw3Ru0Vj4ruuBhPfzrGfxA8ESOasN09eS"

CELL_M   = 300.0
LAT_STEP = CELL_M / 111_000.0
LON_STEP = CELL_M / (111_000.0 * math.cos(math.radians(13.0)))

API_DATA_DIR = "api_responses_predict"
os.makedirs(API_DATA_DIR, exist_ok=True)

SHIFT_M    = 300
BATCH_SIZE = 10

# Two reference days for congestion profiling
REFERENCE_DAYS = {
    "prev_day":      "2024-03-31",   # Sunday — previous day
    "same_weekday":  "2024-03-25",   # Monday — same weekday as Apr 1
}

# 6-hourly slots: 6am, 12pm, 6pm, 12am
HOURS = [6, 12, 18, 0]

# Weight for combining the two days
# same_weekday gets more weight since Apr 1 is also a Monday
DAY_WEIGHTS = {
    "prev_day":     0.3,   # Sunday pattern — different but recent
    "same_weekday": 0.7,   # Monday pattern — matches target day type
}

POI_CAT_WEIGHTS = {
    "hospital": 3.0, "school": 2.5, "college": 2.5,
    "metro_station": 3.0, "bus_stand": 2.0, "government_office": 2.0,
    "shopping_mall": 2.0, "market": 1.5, "restaurant": 1.0, "bank": 1.0,
}

# ================================================================
# HELPERS
# ================================================================
def get_token():
    resp = requests.post(
        "https://outpost.mappls.com/api/security/oauth/token",
        data={"grant_type": "client_credentials",
              "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def cell_center(cell_id):
    i, j = map(int, cell_id.split("_"))
    return (i * LAT_STEP, j * LON_STEP)

def save_json(data, filename):
    path = os.path.join(API_DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"    Saved -> {path}")

def load_json(filename):
    path = os.path.join(API_DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def get_pair(cell_id):
    lat, lon = cell_center(cell_id)
    dlon = SHIFT_M / (111_000 * math.cos(math.radians(lat)))
    return (lat, lon), (lat, lon + dlon)


# ================================================================
# INPUT
# ================================================================
print("=" * 60)
print("Loading predicted data")
print("=" * 60)

pred_df = pd.read_csv("demo_april1_2024.csv").head(50)
predicted_vpd = dict(zip(pred_df["cell_id"].astype(str), pred_df["predicted_violations"]))

zones = sorted(predicted_vpd.keys())
pairs = {cid: get_pair(cid) for cid in zones}
print(f"Zones: {len(zones)}")

# Junction boost from training
train_results = None
if os.path.exists("cis_results.csv"):
    train_results = pd.read_csv("cis_results.csv", index_col=0)

if train_results is not None and "junction_boost" in train_results.columns:
    junction_boost = train_results["junction_boost"].reindex(zones).fillna(1.0)
    print(f"junction_boost: loaded ({junction_boost.min():.3f} — {junction_boost.max():.3f})")
else:
    junction_boost = pd.Series({cid: 1.0 for cid in zones})
    print("junction_boost: default 1.0")


# ================================================================
# DISTANCE MATRIX API
# ================================================================
def call_distance_matrix(zone_batch, resource, date_time=None, token=None):
    coords_parts = []
    for cid in zone_batch:
        src, _ = pairs[cid]
        coords_parts.append(f"{src[1]:.6f},{src[0]:.6f}")
    for cid in zone_batch:
        _, dst = pairs[cid]
        coords_parts.append(f"{dst[1]:.6f},{dst[0]:.6f}")

    n = len(zone_batch)
    url = f"https://apis.mappls.com/advancedmaps/v1/{token}/{resource}/driving/{';'.join(coords_parts)}"
    params = {"sources": ";".join(str(i) for i in range(n)),
              "destinations": ";".join(str(i) for i in range(n, 2*n)),
              "rtype": 0, "region": "ind"}
    if date_time:
        params["date_time"] = date_time

    resp = requests.get(url, params=params)
    if resp.status_code == 401:
        print(f"    401 — quota exhausted, skipping remaining calls")
        return None, None
    if resp.status_code != 200:
        print(f"    ERROR {resp.status_code}: {resp.text[:300]}")
        return None, None
    data = resp.json()

    if data.get("responseCode") and data["responseCode"] != 200:
        print(f"    API error: {data.get('responseCode')}")
        return {cid: 0 for cid in zone_batch}, data

    durations = data["results"]["durations"]
    return {cid: durations[i][i] for i, cid in enumerate(zone_batch)}, data


def group_zones_by_locality(zone_list, batch_size=BATCH_SIZE):
    """Sort zones by grid coordinates so each batch contains nearby zones."""
    coords = []
    for cid in zone_list:
        i, j = map(int, cid.split("_"))
        coords.append((cid, i, j))
    coarse = CELL_M * 5
    lat_step_int = max(1, round(coarse / 111_000.0 / LAT_STEP))
    lon_step_int = max(1, round(coarse / (111_000.0 * math.cos(math.radians(13.0))) / LON_STEP))
    coords.sort(key=lambda x: (x[1] // lat_step_int, x[2] // lon_step_int, x[1], x[2]))
    sorted_zones = [c[0] for c in coords]
    return [sorted_zones[i:i+batch_size] for i in range(0, len(sorted_zones), batch_size)]


def run_all_api_calls(token):
    """
    Fetch freeflow + 6-hourly traffic for 2 reference days.
    Total: 12 freeflow + 96 traffic = 108 calls.
    """
    print("\n" + "=" * 60)
    print("Distance Matrix API — 6-Hourly Congestion Profile")
    print("=" * 60)

    batches = group_zones_by_locality(zones, BATCH_SIZE)
    n_batches = len(batches)
    n_traffic_calls = n_batches * len(HOURS) * len(REFERENCE_DAYS)
    print(f"Batches: {n_batches}")
    print(f"Calls: {n_batches} freeflow + {n_traffic_calls} traffic = {n_batches + n_traffic_calls}")

    # --- Freeflow ---
    print("\n--- Freeflow ---")
    freeflow = {}
    for idx, batch in enumerate(batches):
        fname = f"freeflow_batch_{idx}.json"
        cached = load_json(fname)
        if cached:
            raw = cached.get("raw_response", cached)
            for i, cid in enumerate(batch):
                freeflow[cid] = raw["results"]["durations"][i][i]
            print(f"  Batch {idx+1}/{n_batches}: cached")
        else:
            print(f"  Batch {idx+1}/{n_batches}: calling API")
            result, raw = call_distance_matrix(batch, "distance_matrix", token=token)
            save_json({"zone_ids": list(batch), "raw_response": raw, "parsed": result}, fname)
            freeflow.update(result)
            time.sleep(1)
    save_json(freeflow, "freeflow_all.json")

    # --- Hourly traffic for each reference day ---
    # Structure: traffic[day_label][hour] = {cell_id: duration}
    traffic = {}
    call_count = 0
    quota_hit = False

    for day_label, date_str in REFERENCE_DAYS.items():
        print(f"\n--- {day_label}: {date_str} ({len(HOURS)} slots: {HOURS}) ---")
        traffic[day_label] = {}

        for hour in HOURS:
            dt = f"{date_str}T{hour:02d}:00"
            traffic[day_label][hour] = {}

            for idx, batch in enumerate(batches):
                fname = f"traffic_{day_label}_h{hour:02d}_batch_{idx}.json"
                cached = load_json(fname)
                if cached:
                    raw = cached.get("raw_response", cached)
                    for i, cid in enumerate(batch):
                        traffic[day_label][hour][cid] = raw["results"]["durations"][i][i]
                elif not quota_hit:
                    result, raw = call_distance_matrix(
                        batch, "distance_matrix_eta", date_time=dt, token=token
                    )
                    if result is None:
                        quota_hit = True
                        print(f"  Quota exhausted — using cached data only from here")
                        continue
                    save_json({
                        "zone_ids": list(batch), "day": day_label,
                        "hour": hour, "date_time": dt,
                        "raw_response": raw, "parsed": result,
                    }, fname)
                    traffic[day_label][hour].update(result)
                    call_count += 1
                    time.sleep(0.5)

            print(f"  {day_label} hour {hour:02d}: done ({call_count} API calls so far)")

        print(f"  {day_label}: {'all' if not quota_hit else 'partial'} {len(HOURS)} slots")

    # Save master file
    # Convert hour keys to strings for JSON
    traffic_json = {}
    for day_label in traffic:
        traffic_json[day_label] = {}
        for hour in traffic[day_label]:
            traffic_json[day_label][str(hour)] = traffic[day_label][hour]

    save_json({
        "freeflow": freeflow,
        "traffic": traffic_json,
        "reference_days": REFERENCE_DAYS,
        "n_zones": len(zones),
        "total_api_calls": call_count,
    }, "all_hourly_data.json")

    print(f"\nTotal traffic API calls: {call_count}")
    return freeflow, traffic


def load_saved_results():
    master = load_json("all_hourly_data.json")
    if not master:
        return None, None
    freeflow = master["freeflow"]
    # Convert string hour keys back to int
    traffic = {}
    for day_label in master["traffic"]:
        traffic[day_label] = {}
        for hour_str in master["traffic"][day_label]:
            traffic[day_label][int(hour_str)] = master["traffic"][day_label][hour_str]
    return freeflow, traffic


# ================================================================
# CONGESTION ANALYSIS
# ================================================================
def analyze_congestion(freeflow, traffic):
    """
    Build a 24-hour congestion profile per zone from 2 reference days.
    Output: single congestion_ratio per zone (weighted by violation hours)
    Also prints hourly analysis for presentation.
    """
    print("\n" + "=" * 60)
    print("Congestion Analysis — Hourly Profile")
    print("=" * 60)

    # Slot weights: how much each 6-hour window represents violation activity
    SLOT_WEIGHTS = {
        6:  2.0,   # 6am–12pm: morning peak — most violations
        12: 2.5,   # 12pm–6pm: afternoon + evening peak
        18: 1.5,   # 6pm–12am: evening tail-off
        0:  0.5,   # 12am–6am: overnight — few violations
    }

    # --- Step 1: Compute slot ratios per zone ---
    slot_ratios = {}  # {cid: {hour: ratio}}

    for cid in zones:
        ff = freeflow.get(cid, 0)
        if not ff or ff <= 0:
            slot_ratios[cid] = {h: 1.0 for h in HOURS}
            continue

        ratios = {}
        for hour in HOURS:
            weighted_r = 0.0
            total_w = 0.0
            for day_label, day_w in DAY_WEIGHTS.items():
                dur = traffic.get(day_label, {}).get(hour, {}).get(cid, ff)
                if not dur or dur <= 0:
                    dur = ff
                r = max(dur / ff, 1.0)
                weighted_r += day_w * r
                total_w += day_w
            ratios[hour] = weighted_r / total_w if total_w > 0 else 1.0
        slot_ratios[cid] = ratios

    # --- Step 2: Print slot congestion profile ---
    print("\n  Slot   |  Avg Ratio  |  Max Zone Ratio  |  Visual")
    print("  " + "-" * 55)
    for hour in HOURS:
        all_ratios = [slot_ratios[cid][hour] for cid in zones]
        avg_r = np.mean(all_ratios)
        max_r = np.max(all_ratios)
        bar = "█" * int((avg_r - 1.0) * 50)
        print(f"  {hour:02d}:00  |    {avg_r:.3f}    |      {max_r:.3f}       | {bar}")

    # --- Step 3: Find peak / off-peak slots ---
    avg_by_slot = {h: np.mean([slot_ratios[cid][h] for cid in zones]) for h in HOURS}
    peak_slot = max(avg_by_slot, key=avg_by_slot.get)
    offpeak_slot = min(avg_by_slot, key=avg_by_slot.get)
    print(f"\n  Peak congestion slot:     {peak_slot:02d}:00 (avg ratio: {avg_by_slot[peak_slot]:.3f})")
    print(f"  Off-peak slot:            {offpeak_slot:02d}:00 (avg ratio: {avg_by_slot[offpeak_slot]:.3f})")

    # --- Step 4: Compare reference days ---
    print(f"\n  --- Day comparison (city-wide average) ---")
    for day_label, date_str in REFERENCE_DAYS.items():
        day_ratios = []
        for cid in zones:
            ff = freeflow.get(cid, 0)
            if not ff or ff <= 0: continue
            for hour in HOURS:
                dur = traffic.get(day_label, {}).get(hour, {}).get(cid, ff)
                if dur and dur > 0:
                    day_ratios.append(dur / ff)
        if day_ratios:
            print(f"  {day_label:15s} ({date_str}): mean={np.mean(day_ratios):.3f}, "
                  f"max={np.max(day_ratios):.3f}")

    # --- Step 5: Per-zone congestion_ratio (slot-weighted) ---
    congestion_ratio = {}
    for cid in zones:
        weighted_r = sum(SLOT_WEIGHTS[h] * slot_ratios[cid][h] for h in HOURS)
        total_w = sum(SLOT_WEIGHTS.values())
        congestion_ratio[cid] = weighted_r / total_w

    cr = pd.Series(congestion_ratio, name="congestion_ratio")
    print(f"\n  Slot-weighted congestion_ratio:")
    print(f"    range: {cr.min():.3f} — {cr.max():.3f}")
    print(f"    mean:  {cr.mean():.3f}  median: {cr.median():.3f}")

    # --- Step 6: Per-zone peak slot (top 10) ---
    print(f"\n  --- Per-zone peak congestion slot (top 10) ---")
    for cid in sorted(zones, key=lambda c: congestion_ratio[c], reverse=True)[:10]:
        peak_h = max(HOURS, key=lambda h: slot_ratios[cid][h])
        peak_r = slot_ratios[cid][peak_h]
        print(f"  {cid}: peak at {peak_h:02d}:00 (ratio={peak_r:.3f}), weighted={congestion_ratio[cid]:.3f}")

    # Save slot profiles for dashboard
    profiles = {cid: {str(h): slot_ratios[cid][h] for h in HOURS} for cid in zones}
    save_json(profiles, "slot_congestion_profiles.json")
    print(f"\n  Saved slot profiles for dashboard visualization")

    return cr, slot_ratios


# ================================================================
# POI DENSITY (Nearby API)
# ================================================================
def fetch_poi_nearby(token):
    print("\n" + "=" * 60)
    print("POI density (Nearby API)")
    print("=" * 60)

    cached = load_json("poi_nearby_all.json")
    if cached:
        print("Loaded from cache")
        return cached

    KEYWORDS = ";".join(POI_CAT_WEIGHTS.keys())
    raw_results = {}

    for cid in zones:
        lat, lon = cell_center(cid)
        try:
            resp = requests.get(
                "https://atlas.mappls.com/api/places/nearby/json",
                params={"keywords": KEYWORDS, "refLocation": f"{lat},{lon}", "radius": 500},
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            total = data.get("pageInfo", {}).get("totalHits", len(data.get("suggestedLocations", [])))
            score = float(total)
            raw_results[cid] = {"score": score, "total_pois": total}
            print(f"  {cid}: {total} POIs nearby")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {cid}: error — {e}")
            raw_results[cid] = {"score": 0, "total_pois": 0}

    save_json(raw_results, "poi_nearby_all.json")
    return raw_results


# ================================================================
# ASSEMBLE CIS
# ================================================================
def assemble_cis(cr_series, poi_data=None):
    print("\n" + "=" * 60)
    print("FINAL CIS RANKINGS")
    print("=" * 60)

    df = pd.DataFrame(index=zones)
    df["predicted_vpd"]    = pd.Series(predicted_vpd)
    df["congestion_ratio"] = cr_series
    df["junction_boost"]   = junction_boost

    for cid in zones:
        lat, lon = cell_center(cid)
        df.loc[cid, "lat"] = lat
        df.loc[cid, "lon"] = lon

    # --- Congestion term: (congestion_ratio - 1)^1.25 ---
    # BPR delay function: superlinear because near-capacity roads
    # are disproportionately sensitive to each violation
    cong_term = (df["congestion_ratio"] - 1).clip(lower=0.01) ** 1.25

    # --- POI weight: 1 + ln(1 + poi_score) ---
    if poi_data:
        poi_scores = pd.Series({cid: poi_data.get(cid, {}).get("score", 0) for cid in zones})
        poi_w = 1 + np.log1p(poi_scores)
        df["poi_score"]  = poi_scores
        df["poi_weight"] = poi_w

        # Correlation analysis
        print(f"\n  --- POI Correlation Analysis ---")
        corr_cr  = poi_scores.corr(df["congestion_ratio"])
        corr_vpd = poi_scores.corr(df["predicted_vpd"])
        print(f"  Corr(poi_score, congestion_ratio):  {corr_cr:+.3f}")
        print(f"  Corr(poi_score, predicted_vpd):     {corr_vpd:+.3f}")

        if abs(corr_cr) > 0.7:
            print(f"  HIGH overlap — acknowledge in presentation")
        elif abs(corr_cr) < 0.3:
            print(f"  LOW overlap — independent signals, good")
        else:
            print(f"  MODERATE overlap — partial new info")

        for cid in zones:
            counts = poi_data.get(cid, {}).get("counts", {})
            if counts:
                top = max(counts, key=counts.get)
                df.loc[cid, "top_poi"] = f"{top} ({counts[top]})"
            else:
                df.loc[cid, "top_poi"] = "none"
    else:
        poi_w = pd.Series(1.0, index=zones)
        df["poi_score"] = 0
        df["poi_weight"] = 1.0

    # --- CIS ---
    df["cis"] = (
        df["predicted_vpd"]
        * cong_term
        * df["junction_boost"]
        * poi_w
    )

    df["rank"] = df["cis"].rank(ascending=False).astype(int)
    df = df.sort_values("cis", ascending=False)

    # Print
    print(f"\n{'='*105}")
    print(f"{'RANK':>4}  {'ZONE':<16} {'VPD':>6} {'CONG':>6} "
          f"{'JUNC':>5} {'POI_W':>6} {'CIS':>10}  {'WHY'}")
    print(f"{'-'*105}")
    for _, row in df.iterrows():
        poi_label = row.get("top_poi", "-")
        print(f"{row['rank']:4.0f}  {row.name:<16} {row['predicted_vpd']:6.2f} "
              f"{row['congestion_ratio']:6.3f} "
              f"{row['junction_boost']:5.2f} {row['poi_weight']:6.3f} "
              f"{row['cis']:10.4f}  {poi_label}")

    print(f"\n  Formula: CIS = predicted_vpd x (congestion_ratio-1)^1.25 x junction_boost x poi_weight")

    df.to_csv("cis_predictions.csv")
    print(f"  Saved cis_predictions.csv")
    return df


# ================================================================
# REVERSE GEOCODE
# ================================================================
def fetch_road_names(df_zones, token):
    print("\n" + "=" * 60)
    print("Reverse Geocode")
    print("=" * 60)

    cached = load_json("reverse_geocode_predict.json")
    if cached:
        print("Loaded from cache")
        for cid, info in cached.items():
            if cid in df_zones.index:
                df_zones.loc[cid, "road_name"] = info.get("road", "")
                df_zones.loc[cid, "area"] = info.get("area", "")
        return df_zones

    results = {}
    for cid in zones:
        lat, lon = cell_center(cid)
        try:
            resp = requests.get(
                f"https://apis.mappls.com/advancedmaps/v1/{token}/rev_geocode",
                params={"lat": lat, "lng": lon},
            )
            resp.raise_for_status()
            data = resp.json()["results"][0]
            info = {"road": data.get("street", data.get("formatted_address", "")),
                    "area": data.get("area", ""), "locality": data.get("locality", "")}
            results[cid] = info
            df_zones.loc[cid, "road_name"] = info["road"]
            df_zones.loc[cid, "area"] = info["area"]
            print(f"  {cid}: {info['road']}, {info['area']}")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {cid}: error — {e}")

    save_json(results, "reverse_geocode_predict.json")
    df_zones.to_csv("cis_predictions.csv")
    return df_zones


# ================================================================
# MAIN
# ================================================================
if __name__ == "__main__":
    print("#" * 60)
    print("# CIS PREDICTION — 50 ZONES (6-Hourly Congestion)")
    print("#" * 60)

    RUN_API         = True
    RUN_POI         = True
    RUN_REVERSE_GEO = True

    TOKEN = get_token()

    # --- Distance Matrix (hourly, 2 days) ---
    if RUN_API:
        freeflow, traffic = run_all_api_calls(TOKEN)
    else:
        freeflow, traffic = load_saved_results()
        if not freeflow:
            print("No cached data. Set RUN_API = True"); exit()

    # --- Congestion analysis + ratio ---
    congestion_ratio, hourly_profiles = analyze_congestion(freeflow, traffic)

    # --- POI ---
    poi_data = fetch_poi_nearby(TOKEN) if RUN_POI else load_json("poi_nearby_all.json")

    # --- CIS ---
    df_zones = assemble_cis(congestion_ratio, poi_data)

    # --- Road names ---
    if RUN_REVERSE_GEO:
        df_zones = fetch_road_names(df_zones, TOKEN)

    print("\n" + "=" * 60)
    print("DONE.")
    print(f"  cis_predictions.csv              — final rankings")
    print(f"  {API_DATA_DIR}/slot_congestion_profiles.json  — 6h profiles per zone")
    print(f"  {API_DATA_DIR}/                  — all raw API responses")
    print("=" * 60)