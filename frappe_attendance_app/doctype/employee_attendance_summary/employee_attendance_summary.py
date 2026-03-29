import frappe
import calendar
from frappe.model.document import Document

class EmployeeAttendanceSummary(Document):

    def before_save(self):
        self.compute_metrics()

    def compute_metrics(self):
        try:
            settings = frappe.get_single("Attendance Settings")
        except Exception:
            return
        scheduled = self.get_scheduled_days(settings)
        days_worked = self.days_worked or 0
        days_late   = self.days_late or 0
        days_absent = self.days_absent or 0
        total_hrs   = self.total_hours_worked or 0
        ot_hrs      = self.overtime_hours or 0

        self.attendance_rate = round((days_worked / scheduled) * 100, 2) if scheduled else 0
        on_time = days_worked - days_late
        self.punctuality_rate = round((on_time / days_worked) * 100, 2) if days_worked else 0
        self.avg_work_hours_per_day = round(total_hrs / days_worked, 2) if days_worked else 0
        self.absence_rate = round((days_absent / scheduled) * 100, 2) if scheduled else 0
        regular = total_hrs - ot_hrs
        self.overtime_ratio = round((ot_hrs / regular) * 100, 2) if regular > 0 else 0

    def get_scheduled_days(self, settings):
        working = [d.strip() for d in (settings.day_of_week or "").split("\n") if d.strip()]
        day_map  = {"Monday":0,"Tuesday":1,"Wednesday":2,"Thursday":3,"Friday":4,"Saturday":5,"Sunday":6}
        work_nums = {day_map[d] for d in working if d in day_map}
        if not work_nums:
            return 22
        month_map = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,
                     "July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
        m = month_map.get(self.month, 1)
        y = int(self.year)
        _, num_days = calendar.monthrange(y, m)
        return sum(1 for d in range(1, num_days+1) if calendar.weekday(y, m, d) in work_nums)
