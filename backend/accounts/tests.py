from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from .models import LoginTwoFactorChallenge, University, UniversityIntegration, UserProfile


class AccountAuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.university = University.objects.create(name="BMSCE", country="India")

    def test_student_registration_creates_profile_with_student_role(self):
        payload = {
            "student_id": "BMS2026001",
            "username": "bms_student_1",
            "email": "bms_student_1@example.edu",
            "password": "TempPass123!",
            "university_id": self.university.id,
            "year_of_study": 2,
            "field_of_study": "Computer Science",
            "two_factor_enabled": True,
        }
        res = self.client.post("/api/accounts/register/", payload, format="json")
        self.assertEqual(res.status_code, 201)

        user = User.objects.get(username="bms_student_1")
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(profile.role, "student")
        self.assertEqual(profile.student_id, "BMS2026001")
        self.assertTrue(profile.two_factor_enabled)

    def test_role_enforced_login_endpoints(self):
        student_user = User.objects.create_user(username="student_user", password="TempPass123!")
        UserProfile.objects.create(
            user=student_user,
            role="student",
            student_id="STU1001",
            university=self.university,
        )

        admin_user = User.objects.create_user(username="admin_user", password="TempPass123!")
        UserProfile.objects.create(
            user=admin_user,
            role="admin",
            university=self.university,
        )

        student_login_res = self.client.post(
            "/api/accounts/login/student/",
            {"student_id": "STU1001", "password": "TempPass123!"},
            format="json",
        )
        self.assertEqual(student_login_res.status_code, 200)

        student_on_admin_res = self.client.post(
            "/api/accounts/login/admin/",
            {"username": "student_user", "password": "TempPass123!"},
            format="json",
        )
        self.assertEqual(student_on_admin_res.status_code, 403)

        admin_login_res = self.client.post(
            "/api/accounts/login/admin/",
            {"username": "admin_user", "password": "TempPass123!"},
            format="json",
        )
        self.assertEqual(admin_login_res.status_code, 200)

    def test_professor_can_use_admin_login(self):
        professor_user = User.objects.create_user(username="prof_user", password="TempPass123!")
        UserProfile.objects.create(
            user=professor_user,
            role="professor",
            university=self.university,
        )

        res = self.client.post(
            "/api/accounts/login/admin/",
            {"username": "prof_user", "password": "TempPass123!"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)

    @override_settings(DEBUG=True)
    def test_two_factor_login_and_verify(self):
        user = User.objects.create_user(
            username="two_factor_student",
            password="TempPass123!",
            email="two_factor_student@example.edu",
        )
        UserProfile.objects.create(
            user=user,
            role="student",
            student_id="STU2001",
            university=self.university,
            two_factor_enabled=True,
        )

        login_res = self.client.post(
            "/api/accounts/login/student/",
            {"student_id": "STU2001", "password": "TempPass123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, 202)
        challenge_id = login_res.data.get("challenge_id")
        debug_code = login_res.data.get("debug_code")
        self.assertTrue(challenge_id)
        self.assertTrue(debug_code)

        challenge = LoginTwoFactorChallenge.objects.get(challenge_id=challenge_id)
        self.assertEqual(challenge.user, user)

        verify_res = self.client.post(
            "/api/accounts/two-factor/verify/",
            {"challenge_id": challenge_id, "two_factor_code": debug_code},
            format="json",
        )
        self.assertEqual(verify_res.status_code, 200)
        self.assertEqual(verify_res.data.get("username"), "two_factor_student")

    @override_settings(DEBUG=True)
    def test_password_reset_flow(self):
        user = User.objects.create_user(username="reset_student", password="TempPass123!", email="reset@example.edu")
        UserProfile.objects.create(user=user, role="student", student_id="STU3001", university=self.university)

        forgot_res = self.client.post(
            "/api/accounts/password/forgot/",
            {"identifier": "STU3001"},
            format="json",
        )
        self.assertEqual(forgot_res.status_code, 200)
        uid = forgot_res.data.get("uid")
        token = forgot_res.data.get("token")
        self.assertTrue(uid)
        self.assertTrue(token)

        reset_res = self.client.post(
            "/api/accounts/password/reset/",
            {"uid": uid, "token": token, "new_password": "NewStrongPass123!"},
            format="json",
        )
        self.assertEqual(reset_res.status_code, 200)

        login_res = self.client.post(
            "/api/accounts/login/student/",
            {"student_id": "STU3001", "password": "NewStrongPass123!"},
            format="json",
        )
        self.assertEqual(login_res.status_code, 200)

    def test_sso_providers_include_google_by_default(self):
        res = self.client.get("/api/accounts/sso/providers/")
        self.assertEqual(res.status_code, 200)
        ids = [provider["id"] for provider in res.data.get("providers", [])]
        self.assertIn("google", ids)

    @patch.dict("os.environ", {"GOOGLE_OAUTH_CLIENT_ID": "test-google-client-id"}, clear=False)
    def test_sso_start_google_generates_google_auth_url_when_client_id_present(self):
        res = self.client.post(
            "/api/accounts/sso/start/",
            {"provider": "google", "redirect_uri": "http://localhost:3000"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data.get("provider"), "google")
        self.assertEqual(res.data.get("status"), "ready")
        self.assertIn("accounts.google.com", res.data.get("auth_url", ""))

    def test_integration_upsert_and_list_for_admin(self):
        admin_user = User.objects.create_user(username="admin_integrations", password="TempPass123!")
        UserProfile.objects.create(
            user=admin_user,
            role="admin",
            university=self.university,
        )
        self.client.force_authenticate(user=admin_user)

        upsert_res = self.client.post(
            "/api/accounts/integrations/upsert/",
            {
                "category": "lms",
                "provider_name": "Canvas",
                "status": "active",
                "base_url": "https://canvas.example.edu",
                "config": {"sync_courses": True},
                "api_key": "canvas-secret-key",
            },
            format="json",
        )
        self.assertEqual(upsert_res.status_code, 200)
        self.assertTrue(UniversityIntegration.objects.filter(university=self.university, provider_name="Canvas").exists())

        list_res = self.client.get("/api/accounts/integrations/")
        self.assertEqual(list_res.status_code, 200)
        self.assertGreaterEqual(len(list_res.data.get("integrations", [])), 1)

    def test_widget_embed_requires_admin_or_professor(self):
        student_user = User.objects.create_user(username="widget_student", password="TempPass123!")
        UserProfile.objects.create(
            user=student_user,
            role="student",
            student_id="WGT1001",
            university=self.university,
        )
        self.client.force_authenticate(user=student_user)
        denied = self.client.get("/api/accounts/widget/embed/")
        self.assertEqual(denied.status_code, 403)
