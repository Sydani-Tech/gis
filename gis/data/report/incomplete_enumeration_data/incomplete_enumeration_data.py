
import frappe
from frappe.utils import getdate

def execute(filters=None):
    columns = []

    filters = filters or {}
    record_type = filters.get("record_type")

    if record_type == "Buildings":
        columns.extend([
            {"label": "Data", "fieldname": "data", "fieldtype": "Data", "width": 150},
            {"label": "Name", "fieldname": "record", "fieldtype": "Dynamic Link", "options": "data", "width": 220},
            {"label": "Reported", "fieldname": "households_reported", "fieldtype": "Int", "width": 150},
            {"label": "Enumerated", "fieldname": "households_enumerated", "fieldtype": "Int", "width": 150},
            {"label": "Date", "fieldname": "enumeration_date", "fieldtype": "Date", "width": 115},
            {"label": "Enumerator", "fieldname": "enumerator", "fieldtype": "Link", "options": "User", "width": 150},
            {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": "Grid", "fieldname": "grid", "fieldtype": "Link", "options": "Grid", "width": 150},
            {"label": "Settlement", "fieldname": "settlement", "fieldtype": "Link", "options": "Settlement", "width": 150},
            {"label": "Ward", "fieldname": "ward", "fieldtype": "Link", "options": "Ward", "width": 220},
        ])

        query = frappe.db.sql("""
            SELECT 
                b.name,
                b.grid,
                b.settlement,
                b.ward,
                b.local_government_area,
                b.state,
                b.status,
                b.creation,
                b.owner,
                b.how_many_households_occupy_this_building,
                IFNULL(h.hh_count, 0) AS household_count
            FROM `tabBuilding` b
            LEFT JOIN (
                SELECT building, COUNT(*) AS hh_count
                FROM `tabHousehold`
                WHERE 1=1
                {hh_state_filter}
                {hh_lga_filter}
                {hh_ward_filter}
                {hh_settlement_filter}
                {hh_grid_filter}
                GROUP BY building
            ) h ON h.building = b.name
            WHERE b.building_type = 'Residential'
              {b_state_filter}
              {b_lga_filter}
              {b_ward_filter}
              {b_settlement_filter}
              {b_grid_filter}
              {b_owner_filter}
              {b_status_filter}
              AND (
                    b.how_many_households_occupy_this_building = 0
                    OR (
                        h.hh_count <> b.how_many_households_occupy_this_building
                        AND h.hh_count > 0
                    )
                )
        """.format(
            # Building filters
            b_state_filter       = "AND b.state = %(state)s" if filters.get("state") else "",
            b_lga_filter         = "AND b.local_government_area = %(local_government_area)s" if filters.get("local_government_area") else "",
            b_ward_filter        = "AND b.ward = %(ward)s" if filters.get("ward") else "",
            b_settlement_filter  = "AND b.settlement = %(settlement)s" if filters.get("settlement") else "",
            b_grid_filter        = "AND b.grid = %(grid)s" if filters.get("grid") else "",
            b_owner_filter       = "AND b.owner = %(enumerator)s" if filters.get("enumerator") else "",
            b_status_filter      = "AND b.status = %(status)s" if filters.get("status") else "",

            # Household filters (mirroring building filters for optimization)
            hh_state_filter      = "AND state = %(state)s" if filters.get("state") else "",
            hh_lga_filter        = "AND local_government_area = %(local_government_area)s" if filters.get("local_government_area") else "",
            hh_ward_filter       = "AND ward = %(ward)s" if filters.get("ward") else "",
            hh_settlement_filter = "AND settlement = %(settlement)s" if filters.get("settlement") else "",
            hh_grid_filter       = "AND grid = %(grid)s" if filters.get("grid") else ""
        ), filters, as_dict=True)

        data = [{
            "data": "Building",
            "record": row.name,
            "households_reported": row.how_many_households_occupy_this_building,
            "households_enumerated": row.household_count,
            "enumeration_date": getdate(row.creation),
            "enumerator": row.owner,
            "status": row.status,
            "grid": row.grid,
            "settlement": row.settlement,
            "ward": row.ward,
        } for row in query]

        return columns, data

    elif record_type == "Households":
        columns.extend([
            {"label": "Data", "fieldname": "data", "fieldtype": "Data", "width": 150},
            {"label": "Name", "fieldname": "record", "fieldtype": "Dynamic Link", "options": "data", "width": 190},
            {"label": "Reported", "fieldname": "children_reported", "fieldtype": "Int", "width": 150},
            {"label": "Enumerated", "fieldname": "children_enumerated", "fieldtype": "Int", "width": 150},
            {"label": "Date", "fieldname": "enumeration_date", "fieldtype": "Date", "width": 115},
            {"label": "Enumerator", "fieldname": "enumerator", "fieldtype": "Link", "options": "User", "width": 150},
            {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
            {"label": "Grid", "fieldname": "grid", "fieldtype": "Link", "options": "Grid", "width": 150},
            {"label": "Settlement", "fieldname": "settlement", "fieldtype": "Link", "options": "Settlement", "width": 150},
            {"label": "Ward", "fieldname": "ward", "fieldtype": "Link", "options": "Ward", "width": 220},
        ])

        query = frappe.db.sql("""
            SELECT 
                hh.name,
                hh.grid,
                hh.settlement,
                hh.ward,
                hh.local_government_area,
                hh.state,
                hh.status,
                hh.creation,
                hh.owner,
                hh.how_many_household_members_are_below_5,
                IFNULL(c.children_count, 0) AS children_count
            FROM `tabHousehold` hh
            LEFT JOIN (
                SELECT household, COUNT(*) AS children_count
                FROM `tabChildren`
                WHERE 1=1
                {c_state_filter}
                {c_lga_filter}
                {c_ward_filter}
                {c_settlement_filter}
                {c_grid_filter}
                GROUP BY household
            ) c ON c.household = hh.name
            WHERE 1=1
                {hh_state_filter}
                {hh_lga_filter}
                {hh_ward_filter}
                {hh_settlement_filter}
                {hh_grid_filter}
                {hh_owner_filter}
				{hh_status_filter}
                AND (
                    hh.how_many_household_members_are_below_5 = 0
                    OR (
                        c.children_count <> hh.how_many_household_members_are_below_5
                        AND c.children_count > 0
                    )
                )
        """.format(
            hh_state_filter      = "AND hh.state = %(state)s" if filters.get("state") else "",
            hh_lga_filter        = "AND hh.local_government_area = %(local_government_area)s" if filters.get("local_government_area") else "",
            hh_ward_filter       = "AND hh.ward = %(ward)s" if filters.get("ward") else "",
            hh_settlement_filter = "AND hh.settlement = %(settlement)s" if filters.get("settlement") else "",
            hh_grid_filter       = "AND hh.grid = %(grid)s" if filters.get("grid") else "",
            hh_owner_filter      = "AND hh.owner = %(enumerator)s" if filters.get("enumerator") else "",
            hh_status_filter     = "AND hh.status = %(status)s" if filters.get("status") else "",

			# Children filters (mirroring household filters for optimization)
			c_state_filter       = "AND state = %(state)s" if filters.get("state") else "",
			c_lga_filter         = "AND local_government_area = %(local_government_area)s" if filters.get("local_government_area") else "",
			c_ward_filter        = "AND ward = %(ward)s" if filters.get("ward") else "",
			c_settlement_filter  = "AND settlement = %(settlement)s" if filters.get("settlement") else "",
			c_grid_filter        = "AND grid = %(grid)s" if filters.get("grid") else ""
        ), filters, as_dict=True)

        data = [{
            "data": "Household",
            "record": row.name,
            "children_reported": row.how_many_household_members_are_below_5,
            "children_enumerated": row.children_count,
            "enumeration_date": getdate(row.creation),
            "enumerator": row.owner,
            "status": row.status,
            "grid": row.grid,
            "settlement": row.settlement,
            "ward": row.ward,
        } for row in query]

        return columns, data

    # Default fallback
    return columns, []

