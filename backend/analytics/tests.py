from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import University, UserProfile


class AdminAnalyticsEndpointsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.university = University.objects.create(name="Dayananda Sagar University", country="India")

        self.admin_user = User.objects.create_user(username="admin_portal_user", password="TempPass123!")
        UserProfile.objects.create(
            user=self.admin_user,
            role="admin",
            university=self.university,
        )

        self.student_user = User.objects.create_user(username="student_portal_user", password="TempPass123!")
        UserProfile.objects.create(
            user=self.student_user,
            role="student",
            student_id="DSU1001",
            university=self.university,
        )

    def test_admin_endpoints_require_admin_or_professor_context(self):
        self.client.force_authenticate(user=self.student_user)

        for endpoint in [
            "/api/analytics/admin/overview/",
            "/api/analytics/admin/student-insights/",
            "/api/analytics/admin/reports/",
            "/api/analytics/admin/activity-log/",
        ]:
            res = self.client.get(endpoint)
            self.assertEqual(res.status_code, 403)

    def test_admin_endpoints_return_payload_for_admin(self):
        self.client.force_authenticate(user=self.admin_user)

        overview = self.client.get("/api/analytics/admin/overview/")
        self.assertEqual(overview.status_code, 200)
        self.assertIn("university_overview", overview.data)
        self.assertIn("system_health", overview.data)

        insights = self.client.get("/api/analytics/admin/student-insights/")
        self.assertEqual(insights.status_code, 200)
        self.assertIn("class_level", insights.data)
        self.assertIn("individual_student_analytics", insights.data)

        reports = self.client.get("/api/analytics/admin/reports/")
        self.assertEqual(reports.status_code, 200)
        self.assertIn("platform_usage_reports", reports.data)
        self.assertIn("ai_performance_metrics", reports.data)

        activity = self.client.get("/api/analytics/admin/activity-log/")
        self.assertEqual(activity.status_code, 200)
        self.assertIn("recent_activity_log", activity.data)
