
# import requests
# import frappe
# import datetime
# import re
# import json
# from difflib import SequenceMatcher

# def find_best_match(vaccination, children_records):
#     """Find the best matching Children record based on full_name similarity."""
#     best_match = None
#     highest_ratio = 0
    
#     for child in children_records:
#         match_ratio = SequenceMatcher(None, vaccination.full_name, child.full_name).ratio()
#         if match_ratio > highest_ratio:
#             highest_ratio = match_ratio
#             best_match = child
    
#     return best_match

# def has_sufficient_name_match(vaccination_name, child_name):
#     """Check if there is a sufficient match between the names by comparing word occurrences."""
#     vaccination_words = set(vaccination_name.lower().split())
#     child_words = set(child_name.lower().split())
#     common_words = vaccination_words.intersection(child_words)

#     return len(common_words) >= 2  # Adjust threshold as needed

# def match_vaccination_to_children():
#     """Matches Vaccination records with Children records based on given criteria."""
#     vaccinations = frappe.get_all(
#         "Vaccination", 
#         filters={"status": "Approved", "children": ("is", "not set")},
#         fields=["name", "full_name", "date_of_birth", "gender", "ward", "state"]
#     )
    
#     for vaccination in vaccinations:
#         children_records = frappe.get_all(
#             "Children", 
#             filters={
#                 "status": "Approved", 
#                 "date_of_birth": vaccination["date_of_birth"], 
#                 "gender": vaccination["gender"], 
#                 "state": vaccination["state"]
#             },
#             fields=["name", "full_name"]
#         )
        
#         # Filter based on name similarity using word matching
#         matching_children = [child for child in children_records if has_sufficient_name_match(vaccination["full_name"], child["full_name"])]
        
#         if not matching_children:
#             continue
        
#         best_match = find_best_match(vaccination, matching_children)
        
#         if best_match:
#             frappe.db.set_value("Vaccination", vaccination["name"], "children", best_match["name"])
#             frappe.db.commit()


import frappe
from difflib import SequenceMatcher

def has_sufficient_name_match(vaccination_name, child_name):
    vacc_words = set(vaccination_name.lower().split())
    child_words = set(child_name.lower().split())
    return len(vacc_words.intersection(child_words)) >= 2  # same rule as before

def match_vaccination_to_children():
    """
    Same outcome as your original function:
    - Only Vaccinations with status=Approved and children is not set.
    - Candidate Children must be Approved and match DOB, gender, state.
    - Use word-overlap >= 2 as preliminary filter.
    - Pick best match via SequenceMatcher ratio.
    - Write back vaccination.children.
    """

    # 1) Pull ALL candidates in one SQL JOIN (huge reduction in round-trips)
    #    We fetch fields we need for both sides.
    pairs = frappe.db.sql("""
        SELECT
            v.name        AS vacc_name,
            v.full_name   AS vacc_full_name,
            v.date_of_birth AS vacc_dob,
            v.gender      AS vacc_gender,
            v.state       AS vacc_state,

            c.name        AS child_name,
            c.full_name   AS child_full_name
        FROM `tabVaccination` v
        JOIN `tabChildren`   c
              ON c.status = 'Approved'
             AND c.date_of_birth = v.date_of_birth
             AND c.gender       = v.gender
             AND c.state        = v.state
        WHERE v.status = 'Approved'
          AND (v.children IS NULL OR v.children = '')
    """, as_dict=True)

    if not pairs:
        return

    # 2) Group candidate children by vaccination to keep memory local and fast
    from collections import defaultdict
    group = defaultdict(list)
    for row in pairs:
        group[row["vacc_name"]].append(row)

    # 3) For each vaccination, apply the same name filters and pick best via SequenceMatcher
    to_update = []  # list of tuples (children_name, vaccination_name)
    for vacc_name, rows in group.items():
        vacc_full = rows[0]["vacc_full_name"]  # same for this vaccination across rows

        # preliminary filter: word overlap >= 2
        prelim = [
            r for r in rows
            if has_sufficient_name_match(vacc_full, r["child_full_name"])
        ]
        if not prelim:
            continue

        # pick best
        best_row = None
        best_ratio = -1.0
        for r in prelim:
            ratio = SequenceMatcher(None, vacc_full, r["child_full_name"]).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_row = r

        if best_row:
            to_update.append((best_row["child_name"], vacc_name))

    # 4) Apply updates in batches to avoid per-row commits
    if not to_update:
        return

    BATCH = 1000
    for i in range(0, len(to_update), BATCH):
        batch = to_update[i:i+BATCH]
        # Use parameterized updates to avoid SQL injection & keep it simple
        # (Frappe doesn't support multi-row SET in one statement easily, so do executemany)
        args = [(child, vacc) for child, vacc in batch]
        frappe.db.sql("""
            UPDATE `tabVaccination`
            SET children = %s
            WHERE name = %s
        """, args, as_list=False)  # executemany behavior with a list of tuples
        frappe.db.commit()

            

def update_approved_records():
    approved_vaccinations = frappe.get_all("Vaccination", {"status": "Approved"}, ["name"])
    for vaccination in approved_vaccinations:
        doc = frappe.get_doc("Vaccination", vaccination.name)
        doc.status = "Approved"
        doc.save()
    frappe.db.commit()

    approved_children = frappe.get_all("Children", {"status": "Approved"}, ["name"])
    for child in approved_children:
        doc = frappe.get_doc("Children", child.name)
        doc.status = "Approved"
        doc.save()
    frappe.db.commit()


def update_fully_vaccinated_households():
    frappe.db.sql("""
        UPDATE `tabHousehold` h
        LEFT JOIN (
            SELECT 
                c.household,
                COUNT(*) AS total_children,
                SUM(c.vaccination_status = 'Fully Vaccinated (Measles 2)') AS fully_vaccinated_children
            FROM `tabChildren` c
            WHERE c.status = 'Approved'
            GROUP BY c.household
        ) child_stats
        ON h.name = child_stats.household
        SET h.has_all_fully_vaccinated_children = 
            CASE 
                WHEN child_stats.total_children > 0
                     AND child_stats.total_children = child_stats.fully_vaccinated_children
                THEN 1 ELSE 0 
            END
        WHERE h.status = 'Approved'
    """)
    frappe.db.commit()


# def update_building_vaccination_status():
#     """
#     Updates `percentage_of_vaccinated_children` and `building_vaccination_status`
#     for all Approved buildings, based on linked Approved Children and Vaccination records.
#     """

#     query = """
#         SELECT 
#             b.name AS building_name,
#             -- Count approved children
#             SUM(CASE 
#                 WHEN c.status = 'Approved' THEN 1 ELSE 0 
#             END) AS total_children,
#             SUM(CASE 
#                 WHEN c.status = 'Approved' AND c.vaccination_status IN 
#                     ('Vaccinated to Age', 'Fully Vaccinated (Measles 2)') THEN 1 ELSE 0 
#             END) AS vaccinated_children,
            
#             -- Count approved standalone vaccinations
#             SUM(CASE 
#                 WHEN v.status = 'Approved' THEN 1 ELSE 0 
#             END) AS total_vaccinations,
#             SUM(CASE 
#                 WHEN v.status = 'Approved' AND v.vaccination_status IN 
#                     ('Vaccinated to Age', 'Fully Vaccinated (Measles 2)') THEN 1 ELSE 0 
#             END) AS vaccinated_vaccinations,
            
#             -- Collect statuses for determining building color
#             GROUP_CONCAT(DISTINCT CASE WHEN c.status = 'Approved' THEN c.vaccination_status END) AS child_statuses,
#             GROUP_CONCAT(DISTINCT CASE WHEN v.status = 'Approved' THEN v.vaccination_status END) AS vacc_statuses

#         FROM `tabBuilding` b
#         LEFT JOIN `tabChildren` c ON c.building = b.name
#         LEFT JOIN `tabVaccination` v ON v.building = b.name

#         WHERE b.status = 'Approved'
#         GROUP BY b.name
#     """

#     results = frappe.db.sql(query, as_dict=True)

#     for row in results:
#         total = (row["total_children"] or 0) + (row["total_vaccinations"] or 0)
#         vaccinated = (row["vaccinated_children"] or 0) + (row["vaccinated_vaccinations"] or 0)
#         percentage = round((vaccinated / total) * 100) if total > 0 else 0

#         # Combine statuses
#         all_statuses = []
#         if row["child_statuses"]:
#             all_statuses.extend(row["child_statuses"].split(","))
#         if row["vacc_statuses"]:
#             all_statuses.extend(row["vacc_statuses"].split(","))

#         # Determine color
#         color = "gray"
#         if all_statuses:
#             if any(s not in ("Fully Vaccinated (Measles 2)", "Vaccinated to Age") for s in all_statuses):
#                 color = "red"
#             elif all(s in ("Fully Vaccinated (Measles 2)", "Vaccinated to Age") for s in all_statuses) and \
#                  any(s == "Vaccinated to Age" for s in all_statuses):
#                 color = "yellow"
#             elif all(s == "Fully Vaccinated (Measles 2)" for s in all_statuses):
#                 color = "green"

#         # Update building
#         frappe.db.set_value(
#             "Building",
#             row["building_name"],
#             {
#                 "percentage_of_vaccinated_children": percentage,
#                 "building_vaccination_status": color
#             }
#         )

#     frappe.db.commit()
#     print(f"Updated vaccination status for {len(results)} buildings.")


# def update_building_vaccination_status():
#     """
#     Compute vaccination % and status for Approved buildings using SQL-only aggregation,
#     then update tabBuilding in small batches to avoid lock waits.
#     No new indexes are created on base tables; only TEMP tables are used.
#     Outcome identical to original Python logic.
#     """
#     ok1 = "Vaccinated to Age"
#     ok2 = "Fully Vaccinated (Measles 2)"

#     # be tolerant to existing temp tables from a previous crash
#     frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_c_agg")
#     frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_v_agg")
#     frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_sum")
#     frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_changes")

#     # keep read view light; keep lock waits reasonable for this job
#     frappe.db.sql("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
#     frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 120")

#     # 1) Pre-aggregate CHILDREN by building (Approved only)
#     frappe.db.sql(f"""
#         CREATE TEMPORARY TABLE tmp_c_agg
#         AS
#         SELECT
#             c.building,
#             SUM(c.status = 'Approved') AS tot,
#             SUM(c.status = 'Approved' AND c.vaccination_status IN ('{ok1}','{ok2}')) AS ok,
#             SUM(c.status = 'Approved' AND c.vaccination_status IS NOT NULL) AS s_cnt,
#             SUM(c.status = 'Approved' AND c.vaccination_status = '{ok1}') AS age_cnt,
#             SUM(c.status = 'Approved' AND c.vaccination_status = '{ok2}') AS full_cnt,
#             SUM(c.status = 'Approved' AND c.vaccination_status IS NOT NULL
#                                       AND c.vaccination_status NOT IN ('{ok1}','{ok2}')) AS non_ok
#         FROM `tabChildren` c
#         WHERE c.building IS NOT NULL
#         GROUP BY c.building
#     """)
#     # Temp table key (fast join, doesn't touch real schema)
#     frappe.db.sql("ALTER TABLE tmp_c_agg ADD PRIMARY KEY (building)")

#     # 2) Pre-aggregate VACCINATION by building (Approved only)
#     frappe.db.sql(f"""
#         CREATE TEMPORARY TABLE tmp_v_agg
#         AS
#         SELECT
#             v.building,
#             SUM(v.status = 'Approved') AS tot,
#             SUM(v.status = 'Approved' AND v.vaccination_status IN ('{ok1}','{ok2}')) AS ok,
#             SUM(v.status = 'Approved' AND v.vaccination_status IS NOT NULL) AS s_cnt,
#             SUM(v.status = 'Approved' AND v.vaccination_status = '{ok1}') AS age_cnt,
#             SUM(v.status = 'Approved' AND v.vaccination_status = '{ok2}') AS full_cnt,
#             SUM(v.status = 'Approved' AND v.vaccination_status IS NOT NULL
#                                       AND v.vaccination_status NOT IN ('{ok1}','{ok2}')) AS non_ok
#         FROM `tabVaccination` v
#         WHERE v.building IS NOT NULL
#         GROUP BY v.building
#     """)
#     frappe.db.sql("ALTER TABLE tmp_v_agg ADD PRIMARY KEY (building)")

#     # 3) Sum the two aggregates together (no row expansion)
#     frappe.db.sql("""
#         CREATE TEMPORARY TABLE tmp_sum
#         AS
#         SELECT 
#             b.name AS building_name,
#             COALESCE(c.tot,0)  + COALESCE(v.tot,0)  AS total_items,
#             COALESCE(c.ok,0)   + COALESCE(v.ok,0)   AS ok_items,
#             COALESCE(c.s_cnt,0)+ COALESCE(v.s_cnt,0) AS status_count,
#             COALESCE(c.age_cnt,0)+COALESCE(v.age_cnt,0) AS age_count,
#             COALESCE(c.full_cnt,0)+COALESCE(v.full_cnt,0) AS full_count,
#             COALESCE(c.non_ok,0)+ COALESCE(v.non_ok,0) AS non_ok_count
#         FROM `tabBuilding` b
#         LEFT JOIN tmp_c_agg c ON c.building = b.name
#         LEFT JOIN tmp_v_agg v ON v.building = b.name
#         WHERE b.status = 'Approved'
#     """)
#     frappe.db.sql("ALTER TABLE tmp_sum ADD PRIMARY KEY (building_name)")

#     # 4) Compute final desired values & keep only rows that would change
#     frappe.db.sql(f"""
#         CREATE TEMPORARY TABLE tmp_changes
#         AS
#         SELECT
#             b.name AS name,
#             IF(s.total_items > 0, ROUND(100 * s.ok_items / s.total_items), 0) AS new_pct,
#             CASE
#                 WHEN s.status_count = 0 THEN 'gray'
#                 WHEN s.non_ok_count > 0 THEN 'red'
#                 WHEN (s.age_count > 0)
#                      AND (s.non_ok_count = 0)
#                      AND (s.full_count + s.age_count = s.status_count) THEN 'yellow'
#                 WHEN s.full_count = s.status_count THEN 'green'
#                 ELSE 'gray'
#             END AS new_status
#         FROM tmp_sum s
#         JOIN `tabBuilding` b ON b.name = s.building_name
#         WHERE b.status = 'Approved'
#           AND (
#               b.percentage_of_vaccinated_children <>
#                   IF(s.total_items > 0, ROUND(100 * s.ok_items / s.total_items), 0)
#               OR b.building_vaccination_status <>
#                   CASE
#                       WHEN s.status_count = 0 THEN 'gray'
#                       WHEN s.non_ok_count > 0 THEN 'red'
#                       WHEN (s.age_count > 0)
#                            AND (s.non_ok_count = 0)
#                            AND (s.full_count + s.age_count = s.status_count) THEN 'yellow'
#                       WHEN s.full_count = s.status_count THEN 'green'
#                       ELSE 'gray'
#                   END
#           )
#     """)
#     frappe.db.sql("ALTER TABLE tmp_changes ADD PRIMARY KEY (name)")

#     # 5) Update in small, short transactions; retry on lock waits by shrinking batch
#     batch = 1000  # start size; will auto-shrink on lock waits
#     total = 0

#     while True:
#         # get a deterministic slice of keys to update
#         names = frappe.db.sql(f"""
#             SELECT name FROM tmp_changes
#             ORDER BY name
#             LIMIT {batch}
#         """)
#         if not names:
#             break

#         # bind list for IN (...)
#         keys = [n[0] for n in names]
#         placeholders = ", ".join(["%s"] * len(keys))

#         try:
#             # one small transaction per batch
#             frappe.db.sql("""
#                 UPDATE `tabBuilding` b
#                 JOIN tmp_changes t ON t.name = b.name
#                 SET b.percentage_of_vaccinated_children = t.new_pct,
#                     b.building_vaccination_status = t.new_status
#                 WHERE b.name IN (""" + placeholders + ")",
#                 keys,
#             )
#             affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
#             total += affected

#             # remove processed keys from tmp_changes (keeps next LIMIT fast)
#             frappe.db.sql("DELETE FROM tmp_changes WHERE name IN (" + placeholders + ")", keys)
#             frappe.db.commit()

#             # if we had to shrink before, gradually grow back up (optional)
#             if batch < 1000:
#                 batch = min(1000, int(batch * 1.5))

#         except Exception as e:
#             # If lock wait / deadlock, shrink batch and retry that slice later
#             frappe.db.rollback()
#             msg = str(e)
#             if "Lock wait timeout" in msg or "Deadlock" in msg or "1205" in msg or "1213" in msg:
#                 batch = max(50, batch // 2)
#             else:
#                 # unexpected; re-raise
#                 raise

#     print(f"Updated vaccination status for {total} buildings.")


def update_building_vaccination_status():
    """
    Recompute building_vaccination_status and percentage_of_vaccinated_children
    for ALL Approved Buildings using ONLY Approved Children rows.

    Rules (Children.status == 'Approved' only):
      - If approved_total_rows = 0                -> gray, 0%
      - Else if non_ok_count > 0                  -> red
      - Else if age_count > 0 and all are OK      -> yellow
      - Else if full_count == status_count > 0    -> green
      - Else                                      -> gray (fallback)
    """
    ok1 = "Vaccinated to Age"
    ok2 = "Fully Vaccinated (Measles 2)"

    # Clean up any leftovers
    frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_c_agg")
    frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_sum")
    frappe.db.sql("DROP TEMPORARY TABLE IF EXISTS tmp_changes")

    # Reasonable session settings for long batch jobs
    frappe.db.sql("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    frappe.db.sql("SET SESSION innodb_lock_wait_timeout = 120")

    # 1) Aggregate ONLY Approved Children by building
    frappe.db.sql(f"""
        CREATE TEMPORARY TABLE tmp_c_agg
        AS
        SELECT
            c.building,
            /* count of Approved children (whether or not vaccination_status is set) */
            SUM(c.status = 'Approved') AS appr_tot,
            /* Approved children that have a non-NULL vaccination_status */
            SUM(c.status = 'Approved' AND c.vaccination_status IS NOT NULL) AS status_count,
            /* breakdown of Approved children by vaccination_status */
            SUM(c.status = 'Approved' AND c.vaccination_status = '{ok1}') AS age_count,
            SUM(c.status = 'Approved' AND c.vaccination_status = '{ok2}') AS full_count,
            SUM(c.status = 'Approved' AND c.vaccination_status IS NOT NULL
                                AND c.vaccination_status NOT IN ('{ok1}','{ok2}')) AS non_ok_count
        FROM `tabChildren` c
        WHERE c.building IS NOT NULL
        GROUP BY c.building
    """)
    frappe.db.sql("ALTER TABLE tmp_c_agg ADD PRIMARY KEY (building)")

    # 2) Join to ALL Approved Buildings so buildings without any Approved children get zeros
    frappe.db.sql("""
        CREATE TEMPORARY TABLE tmp_sum
        AS
        SELECT
            b.name AS building_name,
            COALESCE(c.appr_tot, 0)      AS approved_total_rows,
            COALESCE(c.status_count, 0)  AS status_count,
            COALESCE(c.age_count, 0)     AS age_count,
            COALESCE(c.full_count, 0)    AS full_count,
            COALESCE(c.non_ok_count, 0)  AS non_ok_count
        FROM `tabBuilding` b
        LEFT JOIN tmp_c_agg c ON c.building = b.name
        WHERE b.status = 'Approved'
    """)
    frappe.db.sql("ALTER TABLE tmp_sum ADD PRIMARY KEY (building_name)")

    # 3) Compute desired values & select only rows that would actually change
    frappe.db.sql(f"""
        CREATE TEMPORARY TABLE tmp_changes
        AS
        SELECT
            b.name AS name,
            /* Percent only from Approved children where vaccination_status is defined */
            IF(s.status_count > 0,
               ROUND(100 * (s.age_count + s.full_count) / s.status_count),
               0) AS new_pct,
            CASE
                /* No Approved children at all -> gray */
                WHEN s.approved_total_rows = 0 THEN 'gray'
                /* Some Approved children exist; any non-OK among them -> red */
                WHEN s.non_ok_count > 0 THEN 'red'
                /* Some "Vaccinated to Age", none non-OK, and all with status are OK -> yellow */
                WHEN (s.age_count > 0)
                     AND (s.non_ok_count = 0)
                     AND (s.full_count + s.age_count = s.status_count) THEN 'yellow'
                /* All Approved children with status are "Fully Vaccinated (Measles 2)" -> green */
                WHEN s.full_count = s.status_count AND s.status_count > 0 THEN 'green'
                /* Fallback */
                ELSE 'gray'
            END AS new_status
        FROM tmp_sum s
        JOIN `tabBuilding` b ON b.name = s.building_name
        WHERE b.status = 'Approved'
          AND (
                NOT (b.percentage_of_vaccinated_children <=> 
                     IF(s.status_count > 0,
                        ROUND(100 * (s.age_count + s.full_count) / s.status_count),
                        0))
                OR
                NOT (NULLIF(b.building_vaccination_status, '') <=> 
                     CASE
                         WHEN s.approved_total_rows = 0 THEN 'gray'
                         WHEN s.non_ok_count > 0 THEN 'red'
                         WHEN (s.age_count > 0)
                              AND (s.non_ok_count = 0)
                              AND (s.full_count + s.age_count = s.status_count) THEN 'yellow'
                         WHEN s.full_count = s.status_count AND s.status_count > 0 THEN 'green'
                         ELSE 'gray'
                     END)
              )
    """)
    frappe.db.sql("ALTER TABLE tmp_changes ADD PRIMARY KEY (name)")

    # 4) Batched updater with lock-wait backoff
    batch = 1000
    total = 0
    while True:
        rows = frappe.db.sql(f"SELECT name FROM tmp_changes ORDER BY name LIMIT {batch}")
        if not rows:
            break
        keys = [r[0] for r in rows]
        placeholders = ", ".join(["%s"] * len(keys))
        try:
            frappe.db.sql(
                """
                UPDATE `tabBuilding` b
                JOIN tmp_changes t ON t.name = b.name
                SET b.percentage_of_vaccinated_children = t.new_pct,
                    b.building_vaccination_status = t.new_status
                WHERE b.name IN (""" + placeholders + ")",
                keys,
            )
            affected = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
            total += affected

            frappe.db.sql("DELETE FROM tmp_changes WHERE name IN (" + placeholders + ")", keys)
            frappe.db.commit()

            if batch < 1000:
                batch = min(1000, int(batch * 1.5))
        except Exception as e:
            frappe.db.rollback()
            m = str(e)
            if "Lock wait timeout" in m or "Deadlock" in m or "1205" in m or "1213" in m:
                batch = max(50, batch // 2)
            else:
                raise

    print(f"Updated vaccination status for {total} buildings.")



def set_enumerated_vaccination_status():
    """
    Copy vaccination_status -> enumerated_vaccination_status
    only where enumerated_vaccination_status is not set (NULL or empty)
    and vaccination_status is set (non-NULL, non-empty).
    """
    frappe.db.sql("""
        UPDATE `tabChildren`
        SET enumerated_vaccination_status = vaccination_status
        WHERE (enumerated_vaccination_status IS NULL OR enumerated_vaccination_status = '')
          AND vaccination_status IS NOT NULL AND vaccination_status <> ''
    """)
    frappe.db.commit()



def create_missing_facility_buildings():
    facilities = frappe.get_all("Facility", filters={"selected_facility": 1}, fields=["name", "facility_name", "ward", "longitude", "latitude"])

    for facility in facilities:
        # Check if buildings exist for the facility
        building_count = frappe.db.count("Building", filters={"health_facility": facility.name})
        if building_count > 0:
            continue  # Facility already has buildings

        # Check for matching settlements
        settlements = frappe.get_all(
            "Settlement",
            filters={
                "name_of_nearest_facility_to_settlement": facility.name,
                "ward": facility.ward,
                "status": "Approved"
            },
            fields=["name"],
            limit=1
        )

        if not settlements:
            continue  # No matching settlement, skip this facility

        for settlement in settlements:
            building = frappe.new_doc("Building")
            building.building_number = "001"
            building.building_address = facility.facility_name
            building.street_name = facility.name.replace("-", ", ")
            building.describe_the_building = facility.facility_name
            building.building_type = "Non-residential"
            building.establishment_type = "Health Facility"
            building.health_facility = facility.name
            building.settlement = settlement.name
            building.status = "Approved"
            building.project = "STRICAN - Phase 2"
            building.longitude = facility.longitude
            building.latitude = facility.latitude

            # Create GeoJSON Point
            building.geolocation = json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Point",
                        "coordinates": [facility.longitude, facility.latitude]
                    }
                }]
            })

            building.insert(ignore_permissions=True)
            frappe.db.commit()
            print(f"Created Building for Facility: {facility.name} in Settlement: {settlement.name}")



def update_all_building_vaccination_percentages(batch_size: int = 200):
    """
    Scheduled job:
    - Find all buildings that have Approved Children / Vaccination records
    - Compute vaccination percentage per building
    - Update Building.percentage_of_vaccinated_children via SQL (no doc events)
    """

    APPROVED_STATUSES = ("Vaccinated to Age", "Fully Vaccinated (Measles 2)")

    # Buildings from Children
    child_buildings = frappe.get_all(
        "Children",
        filters={"status": "Approved", "building": ["!=", ""]},
        pluck="building",
        distinct=True,
    )

    # Buildings from Vaccination
    vacc_buildings = frappe.get_all(
        "Vaccination",
        filters={"status": "Approved", "building": ["!=", ""]},
        pluck="building",
        distinct=True,
    )

    # Unique list of buildings to process
    all_buildings = list({b for b in (child_buildings + vacc_buildings) if b})

    for i, building_name in enumerate(all_buildings, start=1):
        if not building_name:
            continue

        # ---- Children stats ----
        child_row = frappe.db.sql(
            """
            SELECT
                COUNT(*) AS total_children,
                SUM(
                    CASE
                        WHEN vaccination_status IN %(statuses)s THEN 1
                        ELSE 0
                    END
                ) AS vaccinated_children
            FROM `tabChildren`
            WHERE status = 'Approved'
              AND building = %(building)s
            """,
            {"building": building_name, "statuses": APPROVED_STATUSES},
            as_dict=True,
        )[0]

        total_children = child_row.total_children or 0
        vaccinated_children = child_row.vaccinated_children or 0

        # ---- Vaccination stats (standalone vaccinations) ----
        vacc_row = frappe.db.sql(
            """
            SELECT
                COUNT(*) AS total_vaccinations,
                SUM(
                    CASE
                        WHEN vaccination_status IN %(statuses)s THEN 1
                        ELSE 0
                    END
                ) AS vaccinated_records
            FROM `tabVaccination`
            WHERE status = 'Approved'
              AND building = %(building)s
              AND (children = '' OR children IS NULL)
            """,
            {"building": building_name, "statuses": APPROVED_STATUSES},
            as_dict=True,
        )[0]

        total_vaccinations = vacc_row.total_vaccinations or 0
        vaccinated_vaccinations = vacc_row.vaccinated_records or 0

        total = total_children + total_vaccinations
        vaccinated_total = vaccinated_children + vaccinated_vaccinations

        combined_percentage = round((vaccinated_total / total) * 100) if total > 0 else 0

        # ---- Update Building via SQL (no doc events) ----
        # frappe.db.sql(
        #     """
        #     UPDATE `tabBuilding`
        #     SET percentage_of_vaccinated_children = %s
        #     WHERE name = %s
        #     """,
        #     (combined_percentage, building_name),
        # )

        frappe.db.sql(
            """
            UPDATE `tabBuilding`
            SET
                percentage_of_vaccinated_children = %s,
                modified = NOW(),
                modified_by = %s
            WHERE name = %s
            """,
            (combined_percentage, frappe.session.user, building_name),
        )


        # Batch commits to avoid giant transaction
        if i % batch_size == 0:
            frappe.db.commit()

    frappe.db.commit()

import frappe
from frappe.utils import getdate, today, date_diff, add_days

def recompute_children_vaccination_fields(batch_size: int = 2000):
    """
    Batch recompute of:
      - vaccines_taken
      - vaccination_status
      - next_vaccination_date

    For Children where:
      - status = 'Approved'
      - modified is older than 14 days (or NULL)

    Runs in batches, uses raw SQL, and does NOT trigger doc events.
    """

    offset = 0
    today_date = getdate(today())
    cutoff_date = add_days(today_date, -14)  # 14 days ago

    # Static maps (defined once)
    vaccine_stages = {
        "BCG": 0, "HEP B0": 0, "OPV 0": 0,
        "PENTA 1": 1, "ROTA 1": 1, "PCV 1": 1, "OPV 1": 1, "IPV 1": 1,
        "PENTA 2": 2, "ROTA 2": 2, "PCV 2": 2, "OPV 2": 2,
        "PENTA 3": 3, "ROTA 3": 3, "PCV 3": 3, "OPV 3": 3, "IPV 2": 3,
        "VIT A": 4, "Yellow Fever": 4, "Men A": 4, "MEN A": 4,
        "Measles 1": 5,
        "Measles 2": 6,
    }

    next_vaccine_days = {
        0: 42,    # 6 weeks
        1: 28,    # 4 weeks
        2: 28,    # 4 weeks
        3: 70,    # 10 weeks
        4: 84,    # 12 weeks
        5: 168,   # 24 weeks
        6: None,  # No next vaccination
    }

    while True:
        # 1) Fetch a batch of Children (only the fields we need)
        children = frappe.db.sql(
            """
            SELECT
                name,
                date_of_birth,
                last_vaccination_date
            FROM `tabChildren`
            WHERE status = 'Approved'
              AND (modified IS NULL OR modified < %s)
            ORDER BY name
            LIMIT %s OFFSET %s
            """,
            (cutoff_date, batch_size, offset),
            as_dict=True,
        )

        if not children:
            break

        child_names = [c["name"] for c in children]

        # 2) Fetch all vaccines for this batch in ONE query
        vaccines_rows = frappe.db.sql(
            """
            SELECT
                parent AS child,
                vaccine
            FROM `tabVaccine Multiselect`
            WHERE parent IN %(child_names)s
            """,
            {"child_names": tuple(child_names)},
            as_dict=True,
        )

        # Build a dict: child -> [vaccine, ...]
        child_to_vaccines = {}
        for row in vaccines_rows:
            child_to_vaccines.setdefault(row.child, []).append(row.vaccine)

        # 3) Process each child in Python
        for child in children:
            name = child.name
            dob = child.date_of_birth
            vacc_date = child.last_vaccination_date

            # If no DOB, we can't compute age-related logic; skip
            if not dob:
                continue

            date_of_birth = getdate(dob)
            age_in_days = date_diff(today_date, date_of_birth)
            age_in_weeks = age_in_days // 7

            vaccine_records = child_to_vaccines.get(name, []) or []
            vaccines_taken = "[" + ", ".join(f'"{v}"' for v in vaccine_records) + "]"

            # ---- vaccination_status logic (your original conditions) ----
            vaccination_status = None

            if not vaccine_records:
                vaccination_status = "Never Vaccinated"

            elif (
                ("PENTA 1" not in vaccine_records and
                 "PENTA 2" not in vaccine_records and
                 "PENTA 3" not in vaccine_records)
                and age_in_weeks > 6
            ):
                vaccination_status = "Zero Dose"

            elif (
                (age_in_weeks >= 0 and "BCG" not in vaccine_records) or
                (age_in_weeks >= 0 and "HEP B0" not in vaccine_records) or
                (age_in_weeks >= 0 and "OPV 0" not in vaccine_records) or
                (age_in_weeks >= 6 and "PENTA 1" not in vaccine_records) or
                (age_in_weeks >= 10 and "PENTA 2" not in vaccine_records) or
                (age_in_weeks >= 14 and "PENTA 3" not in vaccine_records) or
                (age_in_weeks >= 24 and "VIT A" not in vaccine_records) or
                (age_in_weeks >= 36 and "Measles 1" not in vaccine_records) or
                (age_in_weeks >= 60 and "Measles 2" not in vaccine_records)
            ):
                vaccination_status = "Under Immunized"

            elif (
                (age_in_weeks >= 0 and age_in_weeks <= 6 and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records) or

                (age_in_weeks >= 6 and age_in_weeks <= 10 and
                 "PENTA 1" in vaccine_records and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records) or

                (age_in_weeks >= 10 and age_in_weeks <= 14 and
                 "PENTA 2" in vaccine_records and
                 "PENTA 1" in vaccine_records and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records) or

                (age_in_weeks >= 14 and age_in_weeks <= 36 and
                 "PENTA 3" in vaccine_records and
                 "PENTA 2" in vaccine_records and
                 "PENTA 1" in vaccine_records and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records) or

                (age_in_weeks >= 24 and age_in_weeks <= 48 and
                 "VIT A" in vaccine_records and
                 "PENTA 3" in vaccine_records and
                 "PENTA 2" in vaccine_records and
                 "PENTA 1" in vaccine_records and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records) or

                (age_in_weeks >= 36 and age_in_weeks <= 60 and
                 "Measles 1" in vaccine_records and
                 "VIT A" in vaccine_records and
                 "PENTA 3" in vaccine_records and
                 "PENTA 2" in vaccine_records and
                 "PENTA 1" in vaccine_records and
                 "BCG" in vaccine_records and
                 "HEP B0" in vaccine_records and
                 "OPV 0" in vaccine_records)
            ):
                vaccination_status = "Vaccinated to Age"

            elif (
                ("BCG" in vaccine_records) and
                ("HEP B0" in vaccine_records) and
                ("OPV 0" in vaccine_records) and
                ("PENTA 1" in vaccine_records) and
                ("PENTA 2" in vaccine_records) and
                ("PENTA 3" in vaccine_records) and
                ("VIT A" in vaccine_records) and
                ("Measles 1" in vaccine_records) and
                ("Measles 2" in vaccine_records)
            ):
                vaccination_status = "Fully Vaccinated (Measles 2)"

            # ---- next_vaccination_date logic ----
            next_vaccination_date = None
            if vacc_date:
                last_vaccination_date = getdate(vacc_date)

                highest_stage = -1
                for v in vaccine_records:
                    stage = vaccine_stages.get(v.strip())
                    if stage is not None and stage > highest_stage:
                        highest_stage = stage

                if highest_stage >= 0:
                    days_to_add = next_vaccine_days.get(highest_stage)
                    if days_to_add:
                        next_vaccination_date = add_days(last_vaccination_date, days_to_add)
                    else:
                        next_vaccination_date = None

            # 4) Update this child via SQL (no doc events)
            frappe.db.sql(
                """
                UPDATE `tabChildren`
                SET
                    vaccines_taken = %s,
                    vaccination_status = %s,
                    next_vaccination_date = %s,
                    modified = NOW()
                WHERE name = %s
                """,
                (vaccines_taken, vaccination_status, next_vaccination_date, name),
            )

        frappe.db.commit()
        offset += batch_size

    frappe.db.commit()




def fetch_odk_data():
    # print("Function fetch_odk_data_program is executed.")

    mapping_dict = {
        #Facilities
        "PHC (B) \nAlukusu": "Alukusu Primary Health Center-Sidisaba-Katcha",
        "BHC Katcha": "BHC Katcha-Katcha-Katcha-Niger",
        "PHC Babangona": "PHC Babangona-Tegina West-Rafi-Niger",
        "Alala PHCC": "Alala PHCC-Tunga Wawa-Kontagora-Niger",
        "PHC Gabi": "PHC Gabi-Dzwafu-Katcha-Niger",
        "Mabono PHC": "Mabono PHC-Gulbiboka-Mariga-Niger",
        "Comprehensive health centre Beri": "Comprehensive health centre Beri-Beri-Mariga-Niger",
        "PHC \nMantuntun": "PHC  Mantuntun-Bisanti-Katcha-Niger",
        "Kanpanin Waya PHCC": "Kanpanin Waya PHCC-Usalle-Kontagora-Niger",
        "Kawo Model PHCC": "Kawo Model PHCC-Kawo-Kontagora-Niger",
        "Madangyen PHCC": "Madangyen PHCC-Tunga Wawa-Kontagora-Niger",
        "BHC Mariga": "BHC Mariga-Inkwai-Mariga-Niger",
        "PHCC Kwana": "Kwana Health Center-Tegina West-Rafi",
        "PHC Sabo mariga": "PHC Sabo mariga-Tegina West-Rafi-Niger",
        "Madangyn PHC": "Madangyn PHC-Tunga Wawa-Kontagora-Niger",
        "Tunga Wawa PHCC": "Tunga Wawa PHCC-Tunga Wawa-Kontagora-Niger",
        "Gulbinboka PHC": "Gulbinboka PHC-Gulbiboka-Mariga-Niger",
        "MCH Pandogori": "PHCC  pandogori-Kongoma Central-Rafi-Niger",
        "PHC Gimi": "PHC Gimi-Tegina Central-Rafi-Niger",
        "Masaha PHCC": "Masaha PHCC-Madara-Kontagora-Niger",
        "PHC Shadadi": "PHC Shadadi-Bangi-Mariga-Niger",
        "MCH Bangi": "MCH Bangi-Bangi-Mariga-Niger",
        "Tukura Primary Health Centre": "Tukura Primary Health Centre-Arewa-Kontagora-Niger",
        "Kaswan garba PHC": "Kaswan garba PHC-Igwama-Mariga-Niger",
        "Nasarawa PHCC": "Nasarawa PHCC-Kudu-Kontagora-Niger",
        "PHC Mayaki Legbodza": "PHC MAYAKI LEGBOZHA TIFIN-Essa-Katcha-Niger",
        "Ishanga PHC": "Ishanga PHC-Kakihum-Mariga-Niger",
        "RIJINYAN NGWAMATSE PHCC": "RIJINYAN NGWAMATSE PHCC-Ngwamatse-Kontagora-Niger",
        "PHCC Tegina": "PHCC Tegina-Tegina Central-Rafi-Niger",
        "PHCC  pandogori": "PHCC  pandogori-Kongoma Central-Rafi-Niger",
        "PHC Kakihum": "PHC Kakihum-Kakihum-Mariga-Niger",
        "Kampanin Bobi PHC": "Kampanin Bobi PHC-Bobi-Mariga-Niger",
        "PHC Matari": "PHC Matari-Bobi-Mariga-Niger",
        "Essa PHC": "PHC MAYAKI LEGBOZHA TIFIN-Essa-Katcha-Niger",

        #Settlements
        "ALUKUSU B": "Alukusu B",
        "NDALADA": "Ndalada",
        "UNG. AUDU": "Ung Audu",
        "CECEKO": "CECEKO",
        "GABI": "Gabi",
        "DZANGBODO": "Dzangbodo",
        "EMITSOWA": "Emitsowa",
        "ALUKUSU B": "Alukusu B",
        "MANTUTUN": "Mantuntun",
        "AMINA WOYE": "Amina Woye",
        "TUKURA B": "Tukura B",
        "RIGASA": "Rigasa",
        "ROAD SAFETY AREA": "Road safety Area",
        "KANWURI": "Kanwuri",
        "Masaha": "Masaha",
        "RIJINYAN NGWAMATSE ": "Rijinyan Ngwamatse",
        "UNG. AUDU": "Ung Audu",
        "UNG. SULE A": "Ung Sule A",
        "Unguwan usman": "Usman A",
        "TSANGAYA": "Tsangaya",
        "UNG. SARKIN TASHA": "Ung Sarkin Tasha",
        "TUNGA NA UKU": "Tunga Na Uku",
        "UNG. YANGA": "Ung Yanga",
        "bakin kasuwa": "Bakin Kasuwa",
        "MAGANDU SABO": "Magandu Sabo",
        "UNGUWAN ALHAJI DANLAMI": "Unguwan Alhaji Danlami",
        "UNG UKATA": "Ung Ukata",
        "UNGUWAN GALADIMA": "UNGUWAN GALADIMA",
        "MAGAMA": "Magama",
        "GANGARE": "Gangare",
        

        #Vaccines
        "HEP_B0": "HEP B0",
        "OPV0": "OPV 0",
        "OPV1": "OPV 1",
        "OPV2": "OPV 2",
        "OPV3": "OPV 3",
        "PCV_1": "PCV 1",
        "PCV2": "PCV 2",
        "PCV3": "PCV 3",
        "IPV1": "IPV 1",
        "IPV2": "IPV 2",
        "ROTA1": "ROTA 1",
        "ROTA2": "ROTA 2",
        "ROTA3": "ROTA 3",
        "VIT_A": "VIT A",
        "MEN_A": "MEN A",
        "MEASLES_1": "Measles 1",
        "MEASLES_2": "Measles 2",
        "YELLOW_FEVER": "Yellow Fever",
        "BCG": "BCG",
        "PENTA_1": "PENTA 1",
        "PENTA2": "PENTA 2",    
        "PENTA3": "PENTA 3",

        #Type of Vaccination Post:
        "OUTREACH TEAM": "Outreach Team",
        "Mobile Team": "Mobile Team",
        "Special Team": "Special Team",

        #Gender
        "male": "Male",
        "female": "Female",
        # Add more mappings as needed
    }

    def transform_values(value):
        if value in mapping_dict:
            return mapping_dict[value]
        else:
            return value

    def pull_vaccination_data(odk_server_url, form_id, username, password):
        try:
            # print("Attempting to fetch data from ODK server.")
            response = requests.get(odk_server_url.format(FORM_ID=form_id), auth=(username, password))
            # print("Response Status Code:", response.status_code)
            # print("Response Content:", response.content)

            if response.status_code == 200:
                for item in response.json()["value"]:
                    instance_id = item.get("meta", {}).get("instanceID", "")
                    # print("Instance ID:", instance_id)

                    # Print the item to understand the structure and identify the keys
                    # print("ODK item:", item)

                    # Mapping and transformation
                    vaccination_date = item.get("Enter_the_date", "")
                    print ("Date:", vaccination_date)
                    # review_state = item.get("__system", {}).get("reviewState", "")
                    # print ("Review State:", review_state)
                    vaccinators_name = item.get("Please_input_your_name", "")
                    print ("Vaccinator's Name:", vaccinators_name)
                    vaccinators_phone_number = item.get("please_input_your_phone_number", "")
                    print ("Vaccinator's Phone Number:", vaccinators_phone_number)
                    team_code = item.get("Team_code", "")
                    print ("Team Code:", team_code)

                    grid_record = frappe.db.get_all("Grid", {"title": team_code}, ["name"], limit=1)
                    grid = grid_record[0].name if grid_record else None
                    print("Grid:", grid)

                    settlement = transform_values(item.get("settlement", ""))
                    print ("Settlement:", settlement)
                    facility = transform_values(item.get("facility", ""))
                    print ("Facility:", facility)
                    type_of_vaccination_post = transform_values(item.get("Type_of_vaccination_post", ""))
                    print ("Type of Vaccination Post:", type_of_vaccination_post)
                    geolocation = item.get("Record_your_current_location")
                    if geolocation:
                        formatted_geolocation = json.dumps({
                            "type": "FeatureCollection",
                            "features": [
                                {
                                    "type": "Feature",
                                    "properties": {
                                        "accuracy": geolocation.get("properties", {}).get("accuracy")
                                    },
                                    "geometry": {
                                        "type": "Point",
                                        "coordinates": geolocation.get("coordinates")[:2]  # Only take longitude and latitude
                                    }
                                }
                            ]
                        })
                        # print("Formatted Geolocation:", formatted_geolocation)
                    else:
                        formatted_geolocation = None
                    print("Geolocation:", formatted_geolocation)
                    start_time = item.get("start", "")
                    start_time = datetime.datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_time = start_time.strftime("%Y-%m-%d %H:%M:%S")
                    print("Start Time:", start_time)

                    end_time = item.get("end", "")
                    end_time = datetime.datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_time = end_time.strftime("%Y-%m-%d %H:%M:%S")
                    print ("End Time:", end_time)
                    odk_parent_id = item.get("__id", "")
                    print ("ODK Parent ID:", odk_parent_id)
                    

                    #Actual Data
                    group_dp5rd99 = item.get("group_dp5rd99", {})

                    for data in item.get("group_dp5rd99", []):

                        odk_child_id = data.get("__id", "")
                        print ("ODK Child ID:", odk_child_id)

                        care_givers_surname = data.get("surName_of_the_caregiver", "")
                        if care_givers_surname == None:
                            care_givers_surname = "N/A"
                        care_givers_surname = re.sub(r'[^a-zA-Z0-9]', '', care_givers_surname)
                        print ("Caregiver's Surname:", care_givers_surname)
                        care_givers_firstname = data.get("FirstName_of_the_caregiver", "")
                        if care_givers_firstname == None:
                            care_givers_firstname = "N/A"
                        care_givers_firstname = re.sub(r'[^a-zA-Z0-9]', '', care_givers_firstname)
                        print ("Caregiver's Firstname:", care_givers_firstname)
                        care_givers_phone_no = data.get("Care_giver_Mai_angwa_phone_number", "")
                        print ("Caregiver's Phone Number:", care_givers_phone_no)
                        care_givers_age = data.get("Age_of_the_caregiver_number", "")
                        # Calculate date of birth from age
                        if care_givers_age:
                            try:
                                today = datetime.date.today()
                                care_givers_date_of_birth = datetime.date(today.year - int(care_givers_age), 1, 1)
                            except ValueError:
                                care_givers_date_of_birth = None
                        else:
                            care_givers_date_of_birth = None
                        print("Caregiver's Date of Birth:", care_givers_date_of_birth)
                        
                        
                        last_name = data.get("surName_of_the_child", "")
                        if last_name == None:
                            last_name = "N/A"
                        last_name = re.sub(r'[^a-zA-Z0-9]', '', last_name)
                        print ("Last Name:", last_name)
                        first_name = data.get("firstName_of_the_child", "")
                        if first_name == None:
                            first_name = "N/A"
                        first_name = re.sub(r'[^a-zA-Z0-9]', '', first_name)
                        print ("First Name:", first_name)
                        date_of_birth = data.get("Date_of_birth_of_the_child", "")
                        print ("Date of Birth:", date_of_birth)
                        gender = transform_values(data.get("What_is_the_gender_of_the_child_", ""))
                        print ("Gender:", gender)
                        vaccines_taken = data.get("Select_the_vaccines_that_were_given", "")
                        vaccines_taken_list = [transform_values(vaccine.strip()) for vaccine in vaccines_taken.split()]
                        print ("Vaccines Taken:", vaccines_taken_list)
                        does_the_child_have_a_child_health_card = data.get("Child_have_health_card", "")
                        print ("Does the child have a health card:", does_the_child_have_a_child_health_card)
                        
                        did_you_administer_the_child_health_card = data.get("administer_child_health_card", "")
                        if did_you_administer_the_child_health_card == None:
                            did_you_administer_the_child_health_card = "No"
                        

                        print ("Did you administer the child health card:", did_you_administer_the_child_health_card)
                        why_were_health_cards_not_given = data.get("Why_were_health_cards_not_given", "")
                        print ("Why were health cards not given:", why_were_health_cards_not_given)
                        
                        
                        # Load the list of specific odk_child_id to skip from a file
                        skip_file_path = "/home/frappe/frappe-bench/apps/gis/gis/skip_odk_child_ids.txt"
                        with open(skip_file_path, "r") as file:
                            skip_odk_child_ids = [line.strip() for line in file.readlines()]

                        parent_id_skip_file_path = "/home/frappe/frappe-bench/apps/gis/gis/skip_odk_parent_ids.txt"
                        with open(parent_id_skip_file_path, "r") as file:
                            skip_odk_parent_ids = [line.strip() for line in file.readlines()]

                        # Check if a record with the same odk_child_id already exists
                        existing_record = frappe.db.exists("Vaccination", {"odk_child_id": odk_child_id})
                        if existing_record or odk_child_id in skip_odk_child_ids or odk_parent_id in skip_odk_parent_ids:
                            print(f"Record with odk_child_id {odk_child_id} already exists or is in the skip list. Skipping...")
                            continue
                        try:
                            # Insert data into Vaccination table
                            vaccination = frappe.new_doc("Vaccination")
                            vaccination.vaccination_date = vaccination_date
                            vaccination.vaccinators_name = vaccinators_name
                            vaccination.vaccinators_phone_number = vaccinators_phone_number
                            vaccination.team_code = team_code
                            vaccination.settlement = settlement
                            vaccination.grid = grid
                            vaccination.ward = frappe.db.get_value("Settlement", {"name": settlement}, "ward")
                            vaccination.local_government_area = frappe.db.get_value("Settlement", {"name": settlement}, "local_government_area")
                            vaccination.state = frappe.db.get_value("Settlement", {"name": settlement}, "state")
                            vaccination.country = frappe.db.get_value("Settlement", {"name": settlement}, "country")
                            vaccination.facility = facility
                            building_record = frappe.db.get_all("Building", {"health_facility": facility}, ["name"], limit=1)
                            vaccination.building = building_record[0].name if building_record else None
                            vaccination.type_of_vaccination_post = type_of_vaccination_post
                            vaccination.geolocation = formatted_geolocation
                            vaccination.response_geolocation = formatted_geolocation
                            vaccination.start_time = start_time
                            vaccination.end_time = end_time
                            vaccination.odk_parent_id = odk_parent_id
                            vaccination.care_givers_surname = care_givers_surname
                            vaccination.care_givers_firstname = care_givers_firstname
                            vaccination.care_givers_name = f"{care_givers_firstname} {care_givers_surname}"
                            vaccination.care_givers_phone_no = care_givers_phone_no
                            vaccination.care_givers_date_of_birth = care_givers_date_of_birth
                            vaccination.last_name = last_name
                            vaccination.first_name = first_name
                            vaccination.full_name = f"{first_name} {last_name}"
                            vaccination.date_of_birth = date_of_birth
                            vaccination.gender = gender
                            for vaccine in vaccines_taken_list:
                                vaccination.append("last_vaccines_administered", {"vaccine": vaccine})
                            vaccination.does_the_child_have_a_child_health_card = does_the_child_have_a_child_health_card
                            vaccination.did_you_administer_the_child_health_card = did_you_administer_the_child_health_card
                            vaccination.why_were_health_cards_not_given = why_were_health_cards_not_given
                            vaccination.odk_child_id = odk_child_id
                            vaccination.status = "Submitted"
                            vaccination.project = "STRICAN - Phase 2"
                            vaccination.was_the_child_vaccinated_during_this_program = "Yes"

                            vaccination.insert(ignore_permissions=True)
                            vaccination.save()
                        except Exception as e:
                            print(f"Error: {e}, settlement: {settlement}, facility: {facility}, id: {odk_child_id}")
                            frappe.log_error(f"Error: {e}, {odk_child_id}")
                            
                            # Write the odk_child_id to the skip file
                            with open(skip_file_path, "a") as file:
                                file.write(f"{odk_child_id}\n")
                            
                            # return "Error: " + str(e)
                            pass
                            

                        
                    

                

                    # print("Records inserted successfully.")

                return "Data fetched successfully"
            else:
                return "Error fetching data from ODK server" 
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return "Error: " + str(e)
        except Exception as e:
            print("Error:", str(e))
            return "Error: " + str(e)

    # Replace the following placeholders with your actual values
    # odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*&$top=5000"
    odk_server_url = "https://odk.sydani.org/v1/projects/31/forms/{FORM_ID}.svc/Submissions?$expand=*"
    form_id = "Vaccination%20Team%20Tool"
    username = frappe.get_site_config().get("odk_username")
    password = frappe.get_site_config().get("odk_password")

    return pull_vaccination_data(odk_server_url, form_id, username, password)

