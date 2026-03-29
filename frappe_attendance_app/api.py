import frappe
import calendar
from frappe.utils import get_time, nowdate, getdate

def calculate_attendance_status(doc, method=None):
    try:
        settings = frappe.get_single("Attendance Settings")
    except Exception:
        return
    if not doc.accesstime or not settings.start_time:
        return

    log_time   = get_time(doc.accesstime)
    start_time = get_time(settings.start_time)
    end_time   = get_time(settings.end_time) if settings.end_time else None
    lunch_out  = get_time(settings.lunch_time_out) if settings.lunch_time_out else None
    lunch_in   = get_time(settings.lunch_time_in)  if settings.lunch_time_in  else None
    break_out  = get_time(settings.break_time_out) if settings.break_time_out else None
    break_in   = get_time(settings.break_time_in)  if settings.break_time_in  else None

    status = "On Time"

    if settings.early_check_in_limit:
        from frappe.utils import time_diff_in_seconds
        diff = time_diff_in_seconds(str(start_time), str(log_time))
        if diff > (int(settings.early_check_in_limit) * 60):
            status = "Early Check-in"
    elif log_time > start_time:
        status = "Late"

    if lunch_out and lunch_in and lunch_out <= log_time <= lunch_in:
        status = "Lunch Break"
    if break_out and break_in and break_out <= log_time <= break_in:
        status = "Break"
    if end_time and doc.direction and "out" in str(doc.direction).lower():
        if log_time < end_time:
            status = "Early Leave"

    doc.attendancestatus = status

    frappe.enqueue(
        "frappe_attendance_app.api.update_monthly_summary",
        queue="short",
        employee_id=doc.employeeid,
        access_date=str(doc.accessdate) if doc.accessdate else nowdate()
    )


def _last_day(year, month):
    return calendar.monthrange(year, month)[1]


def _time_diff_hours(t1, t2):
    try:
        from datetime import datetime
        a = datetime.strptime(str(t1), "%H:%M:%S")
        b = datetime.strptime(str(t2), "%H:%M:%S")
        return max(0.0, (b - a).total_seconds() / 3600)
    except Exception:
        return 0.0


def update_monthly_summary(employee_id, access_date):
    if not employee_id:
        return
    employee = frappe.db.get_value("Employee", {"employee_id": employee_id}, "name")
    if not employee:
        return

    date = getdate(access_date)
    month_map = {1:"January",2:"February",3:"March",4:"April",5:"May",6:"June",
                 7:"July",8:"August",9:"September",10:"October",11:"November",12:"December"}
    month = month_map[date.month]
    year  = date.year

    existing = frappe.db.get_value(
        "Employee Attendance Summary",
        {"employee": employee, "month": month, "year": year}, "name"
    )
    summary = frappe.get_doc("Employee Attendance Summary", existing) if existing               else frappe.new_doc("Employee Attendance Summary")
    if not existing:
        summary.employee = employee
        summary.month    = month
        summary.year     = year

    logs = frappe.db.get_all(
        "Hik Attendance Log",
        filters={"employeeid": employee_id,
                 "accessdate": ["between", [date.replace(day=1), date.replace(day=_last_day(year, date.month))]]},
        fields=["accessdate","accesstime","attendancestatus","direction"]
    )

    try:
        settings = frappe.get_single("Attendance Settings")
        work_hours_per_day = _time_diff_hours(settings.start_time, settings.end_time)
    except Exception:
        work_hours_per_day = 8.0

    from collections import defaultdict
    day_logs = defaultdict(list)
    for log in logs:
        day_logs[str(log.accessdate)].append(log)

    days_worked = days_late = days_early_leave = early_checkin = 0
    total_hours = overtime_hours = 0.0

    for day, entries in day_logs.items():
        statuses = [e.attendancestatus for e in entries]
        times    = sorted([get_time(e.accesstime) for e in entries if e.accesstime])
        days_worked += 1
        if "Late" in statuses:            days_late += 1
        if "Early Check-in" in statuses:  early_checkin += 1
        if "Early Leave" in statuses:     days_early_leave += 1
        if len(times) >= 2:
            hrs = _time_diff_hours(str(times[0]), str(times[-1]))
            total_hours += hrs
            if hrs > work_hours_per_day:
                overtime_hours += hrs - work_hours_per_day

    _, num_days = calendar.monthrange(year, date.month)
    days_absent = max(0, num_days - len(day_logs))

    summary.days_worked        = days_worked
    summary.days_late          = days_late
    summary.days_early_leave   = days_early_leave
    summary.days_absent        = days_absent
    summary.early_check_in     = early_checkin
    summary.total_hours_worked = round(total_hours, 2)
    summary.overtime_hours     = round(overtime_hours, 2)
    summary.save(ignore_permissions=True)
    frappe.db.commit()
