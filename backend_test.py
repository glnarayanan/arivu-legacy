#!/usr/bin/env python3

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests


class ArivuAPITester:
    def __init__(self, base_url="https://arivu.app/"):
        self.base_url = base_url.rstrip("/")
        self.api_url = f"{self.base_url}/api"
        self.token = None
        self.user_id = None
        self.test_email = None
        self.test_password = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
        else:
            print(f"❌ {name} - {details}")

        self.test_results.append(
            {"test": name, "success": success, "details": details, "timestamp": datetime.now().isoformat()}
        )

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {"Content-Type": "application/json"}

        if self.token:
            test_headers["Authorization"] = f"Bearer {self.token}"

        if headers:
            test_headers.update(headers)

        try:
            if method == "GET":
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, headers=test_headers, timeout=30)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            else:
                self.log_test(name, False, f"Unsupported method: {method}")
                return None

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"

            if not success:
                details += f" (Expected {expected_status})"
                try:
                    error_data = response.json()
                    details += f" - {error_data.get('detail', 'Unknown error')}"
                except ValueError:
                    details += f" - {response.text[:100]}"

            self.log_test(name, success, details)

            if success:
                try:
                    return response.json()
                except ValueError:
                    return {}
            return None

        except requests.RequestException as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return None

    def test_auth_signup(self):
        """Test user signup"""
        timestamp = int(time.time())
        signup_data = {
            "email": f"test{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}",
        }

        self.test_email = signup_data["email"]
        self.test_password = signup_data["password"]

        result = self.run_test("Auth - Signup", "POST", "auth/signup", 200, data=signup_data)

        if result and ("token" in result or "access_token" in result):
            self.token = result.get("token") or result.get("access_token")
            self.user_id = (result.get("user") or {}).get("id")
            return True
        return False

    def test_auth_login(self):
        """Test user login with existing credentials"""
        login_data = {
            "email": self.test_email or "test@example.com",
            "password": self.test_password or "TestPass123!",
        }

        result = self.run_test("Auth - Login (existing user)", "POST", "auth/login", 200, data=login_data)

        # If login fails, it's expected since we don't have existing users
        if not result:
            self.log_test("Auth - Login (no existing user)", True, "Expected - no existing test user")
            return True

        if result and ("token" in result or "access_token" in result):
            self.token = result.get("token") or result.get("access_token")
            self.user_id = (result.get("user") or {}).get("id")
            return True
        return False

    def test_auth_logout(self):
        result = self.run_test("Auth - Logout", "POST", "auth/logout", 200)
        return result is not None

    def test_health_check(self):
        result = self.run_test("Health - API", "GET", "health", 200)
        return result is not None

    def test_create_bookmark(self):
        """Test bookmark creation"""
        bookmark_data = {"url": "https://example.com"}

        result = self.run_test("Bookmarks - Create", "POST", "bookmarks", 200, data=bookmark_data)

        if result and "id" in result:
            return result["id"]
        return None

    def test_create_bookmark_wikipedia(self):
        """Test bookmark creation with Wikipedia URL"""
        bookmark_data = {"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"}

        result = self.run_test("Bookmarks - Create Wikipedia", "POST", "bookmarks", 200, data=bookmark_data)

        if result and "id" in result:
            return result["id"]
        return None

    def test_get_bookmarks(self):
        """Test getting bookmarks list"""
        result = self.run_test("Bookmarks - Get List", "GET", "bookmarks", 200)
        return result is not None

    def test_search_bookmarks(self):
        """Test bookmark search"""
        result = self.run_test("Bookmarks - Search", "GET", "bookmarks?search=artificial", 200)
        return result is not None

    def test_get_bookmark_detail(self, bookmark_id):
        """Test getting bookmark details"""
        if not bookmark_id:
            self.log_test("Bookmarks - Get Detail", False, "No bookmark ID available")
            return False

        result = self.run_test("Bookmarks - Get Detail", "GET", f"bookmarks/{bookmark_id}", 200)
        return result is not None

    def test_create_collection(self):
        """Test collection creation"""
        collection_data = {"name": f"Test Collection {int(time.time())}"}

        result = self.run_test("Collections - Create", "POST", "collections", 200, data=collection_data)

        if result and "id" in result:
            return result["id"]
        return None

    def test_get_collections(self):
        """Test getting collections"""
        result = self.run_test("Collections - Get List", "GET", "collections", 200)
        return result is not None

    def test_add_to_collection(self, collection_id, bookmark_id):
        """Test adding bookmark to collection"""
        if not collection_id or not bookmark_id:
            self.log_test("Collections - Add Bookmark", False, "Missing collection or bookmark ID")
            return False

        data = {"bookmark_id": bookmark_id}
        result = self.run_test("Collections - Add Bookmark", "POST", f"collections/{collection_id}/add", 200, data=data)
        return result is not None

    def test_detect_duplicates(self):
        """Test duplicate detection"""
        result = self.run_test("Duplicates - Detect", "GET", "bookmarks/duplicates/detect", 200)
        return result is not None

    def test_delete_bookmark(self, bookmark_id):
        """Test bookmark deletion"""
        if not bookmark_id:
            self.log_test("Bookmarks - Delete", False, "No bookmark ID available")
            return False

        result = self.run_test("Bookmarks - Delete", "DELETE", f"bookmarks/{bookmark_id}", 200)
        return result is not None

    def wait_for_ai_processing(self, bookmark_id, max_wait=30):
        """Wait for AI processing to complete"""
        if not bookmark_id:
            return False

        print(f"⏳ Waiting for AI processing on bookmark {bookmark_id}...")

        for i in range(max_wait):
            result = self.run_test(f"AI Processing - Check {i + 1}", "GET", f"bookmarks/{bookmark_id}", 200)

            if result and result.get("ai_summary", {}).get("processing_status") == "completed":
                print(f"✅ AI processing completed after {i + 1} seconds")
                return True
            elif result and result.get("ai_summary", {}).get("processing_status") == "failed":
                print(f"❌ AI processing failed after {i + 1} seconds")
                return False

            time.sleep(1)

        print(f"⏰ AI processing timeout after {max_wait} seconds")
        return False

    def test_get_profile(self):
        """Test getting user profile"""
        result = self.run_test("Profile - Get", "GET", "user/profile", 200)
        return result is not None and "email" in result

    def test_update_profile(self):
        """Test updating user profile"""
        update_data = {"name": f"Updated Name {int(time.time())}"}
        result = self.run_test("Profile - Update", "PUT", "user/profile", 200, data=update_data)
        return result is not None

    def test_change_password(self):
        """Test changing password (will fail without valid current password)"""
        change_data = {"current_password": "TestPass123!", "new_password": "NewTestPass456!"}
        # This test is expected to fail in most cases
        result = self.run_test("Password - Change", "POST", "auth/change-password", 200, data=change_data)
        # For test cleanup, if it succeeded, change back
        if result:
            self.run_test(
                "Password - Reset back",
                "POST",
                "auth/change-password",
                200,
                data={"current_password": "NewTestPass456!", "new_password": "TestPass123!"},
            )
        return True  # Test is informational

    def test_forgot_password(self):
        """Test forgot password endpoint (should always return success)"""
        forgot_data = {"email": "test@example.com"}
        # This should always succeed (to prevent email enumeration)
        result = self.run_test("Password - Forgot", "POST", "auth/forgot-password", 200, data=forgot_data)
        return result is not None

    def test_backup_json(self):
        """Test backup endpoint with JSON format"""
        backup_data = {"format": "json", "include_notes": True, "include_ai_summaries": True}
        result = self.run_test("Backup - JSON", "POST", "bookmarks/backup", 200, data=backup_data)
        return result is not None

    def test_backup_csv(self):
        """Test backup endpoint with CSV format"""
        backup_data = {"format": "csv", "include_notes": True, "include_ai_summaries": False}
        result = self.run_test("Backup - CSV", "POST", "bookmarks/backup", 200, data=backup_data)
        return result is not None


def parse_args():
    default_base_url = os.getenv("ARIVU_BASE_URL", "https://arivu.app/")
    parser = argparse.ArgumentParser(
        description="Run Arivu backend API smoke tests against a target base URL.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-url",
        default=default_base_url,
        help=(
            "Base URL for Arivu app (e.g., http://localhost). "
            "If omitted, uses ARIVU_BASE_URL and falls back to production URL."
        ),
    )
    parser.add_argument(
        "--smoke-profile",
        choices=["full", "core"],
        default="full",
        help=(
            "Smoke profile to run: 'full' includes AI-dependent checks, "
            "'core' skips AI/third-party-dependent checks for local Docker verification."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    base_url = args.base_url.rstrip("/")

    print("🚀 Starting Arivu API Testing...")
    print("=" * 50)
    print(f"🌐 Base URL: {base_url}")
    print(f"🧪 Smoke profile: {args.smoke_profile}")
    if base_url == "https://arivu.app":
        print("⚠️  Running against production URL. Use --base-url or ARIVU_BASE_URL for local verification.")

    tester = ArivuAPITester(base_url=base_url)

    print("\n🏥 Testing Health...")
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1

    # Test authentication
    print("\n📝 Testing Authentication...")
    if not tester.test_auth_signup():
        print("❌ Signup failed, stopping tests")
        return 1

    tester.test_auth_login()

    # Test bookmark operations
    print("\n📚 Testing Bookmark Operations...")
    bookmark_id = tester.test_create_bookmark()
    wikipedia_id = tester.test_create_bookmark_wikipedia()

    tester.test_get_bookmarks()
    tester.test_search_bookmarks()

    if bookmark_id:
        tester.test_get_bookmark_detail(bookmark_id)

    if args.smoke_profile == "full":
        # Test AI processing
        print("\n🤖 Testing AI Processing...")
        if wikipedia_id:
            tester.wait_for_ai_processing(wikipedia_id, max_wait=45)
            # Check the bookmark again to see AI results
            result = tester.run_test("AI Processing - Final Check", "GET", f"bookmarks/{wikipedia_id}", 200)
            if result and result.get("ai_summary"):
                ai_summary = result["ai_summary"]
                print(f"   📝 One sentence: {ai_summary.get('one_sentence', 'N/A')[:100]}...")
                print(f"   📋 Bullet points: {len(ai_summary.get('bullet_points', []))} points")
                print(f"   📖 Long form: {len(ai_summary.get('long_form', ''))} chars")
                print(f"   ✨ Highlights: {len(ai_summary.get('highlights', []))} highlights")
                print(f"   🏷️ Tags: {ai_summary.get('suggested_tags', [])}")
    else:
        print("\n⏭️  Skipping AI-dependent checks for core smoke profile")

    # Test collections
    print("\n📁 Testing Collections...")
    collection_id = tester.test_create_collection()
    tester.test_get_collections()

    if collection_id and bookmark_id:
        tester.test_add_to_collection(collection_id, bookmark_id)

    # Test duplicates
    print("\n🔍 Testing Duplicate Detection...")
    tester.test_detect_duplicates()

    # Cleanup - delete test bookmarks
    print("\n🧹 Cleanup...")
    if bookmark_id:
        tester.test_delete_bookmark(bookmark_id)
    if wikipedia_id:
        tester.test_delete_bookmark(wikipedia_id)

    print("\n🚪 Testing Logout...")
    tester.test_auth_logout()

    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")

    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
