"""
Fetch health indicators from the DHIS2 public demo instance.
https://play.dhis2.org/demo
Auth: admin / district
"""

import requests
from datetime import datetime, timezone
from .db import get_session, Dhis2Data

DHIS2_BASE = "https://play.im.dhis2.org/dev/api"
DHIS2_AUTH = ("admin", "district")

# Health indicator IDs from DHIS2 demo
INDICATORS = [
    {"id": "Uvn6LCg7dVU", "name": "ANC 1 Coverage"},
    {"id": "ReUHfIn0pTQ", "name": "ANC 1-3 Dropout Rate"},
    {"id": "OdiHJayrsKo", "name": "ANC 4 Coverage"},
    {"id": "sB79w2hiLp8", "name": "ANC IPT 1 Coverage"},
    {"id": "AUqdhY4mpvp", "name": "ANC IPT 2 Coverage"},
    {"id": "dwEq7wi6nXV", "name": "ANC visits per clinical professional"},
    {"id": "s46m5MS0hxu", "name": "BCG Coverage <1y"},
    {"id": "FnYCr2EAzWS", "name": "BMI female"},
    {"id": "bCSmEaVnJSy", "name": "Bed Occupancy Rate"},
    {"id": "eTDtyyaSA7f", "name": "Fully Immunized <1y Coverage"},
]

PERIODS = ["202301", "202302", "202303", "202304", "202305", "202306"]


def fetch_from_dhis2():
    """Fetch aggregated health indicators from DHIS2 demo."""
    session = get_session()
    try:
        imported = 0
        errors = []

        # Fetch analytics data
        indicator_ids = ";".join([ind["id"] for ind in INDICATORS])
        period_str = ";".join(PERIODS)

        url = (
            f"{DHIS2_BASE}/analytics.json"
            f"?dimension=dx:{indicator_ids}"
            f"&dimension=pe:{period_str}"
            f"&dimension=ou:ImspTQPwCqd"  # Sierra Leone (demo org unit)
            f"&skipMeta=false"
        )

        try:
            resp = requests.get(url, auth=DHIS2_AUTH, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            return {"error": f"DHIS2 API request failed: {str(e)}"}

        # Build indicator name lookup from metadata
        name_lookup = {ind["id"]: ind["name"] for ind in INDICATORS}
        meta_items = data.get("metaData", {}).get("items", {})
        for item_id, item_data in meta_items.items():
            if item_id in name_lookup:
                name_lookup[item_id] = item_data.get("name", name_lookup[item_id])

        rows = data.get("rows", [])
        for row in rows:
            if len(row) < 3:
                continue

            dx_id = row[0]
            period = row[1]
            org_unit = row[2]
            value = row[3] if len(row) > 3 else None

            indicator_name = name_lookup.get(dx_id, dx_id)
            org_name = meta_items.get(org_unit, {}).get("name", org_unit)

            try:
                float_val = float(value) if value is not None else None
            except (ValueError, TypeError):
                float_val = None

            obj = Dhis2Data(
                indicator_name=indicator_name,
                indicator_id=dx_id,
                period=period,
                org_unit=org_name,
                value=float_val,
            )
            session.add(obj)
            imported += 1

        session.commit()

        return {
            "source": "DHIS2 Demo (Sierra Leone)",
            "total_imported": imported,
            "indicators": len(INDICATORS),
            "periods": len(PERIODS),
        }

    except Exception as e:
        session.rollback()
        return {"error": str(e)}
    finally:
        session.close()
