
app_name = "frappe_attendance_app"
app_title = "Frappe Attendance App"
app_publisher = "Ashley"
app_description = "HikCentral Attendance Integration"
app_email = "ashley@example.com"
app_license = "mit"

doc_events = {
    "Hik Attendance Log": {
        "before_insert": "frappe_attendance_app.api.calculate_attendance_status"
    }
}
