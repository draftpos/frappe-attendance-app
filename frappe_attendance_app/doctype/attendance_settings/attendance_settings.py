import frappe
from frappe.model.document import Document

class AttendanceSettings(Document):
    def validate(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                frappe.throw("End Time must be after Start Time")
        if self.lunch_time_out and self.lunch_time_in:
            if self.lunch_time_out >= self.lunch_time_in:
                frappe.throw("Lunch End must be after Lunch Start")
        if self.break_time_out and self.break_time_in:
            if self.break_time_out >= self.break_time_in:
                frappe.throw("Break End must be after Break Start")
