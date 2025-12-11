#!/usr/bin/env python3

import requests
import sys
import json
import time
from datetime import datetime

class ArivuAPITester:
    def __init__(self, base_url="https://arivu.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
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
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if not success:
                details += f" (Expected {expected_status})"
                try:
                    error_data = response.json()
                    details += f" - {error_data.get('detail', 'Unknown error')}"
                except:
                    details += f" - {response.text[:100]}"

            self.log_test(name, success, details)
            
            if success:
                try:
                    return response.json()
                except:
                    return {}
            return None

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return None

    def test_auth_signup(self):
        """Test user signup"""
        timestamp = int(time.time())
        signup_data = {
            "email": f"test{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}"
        }
        
        result = self.run_test(
            "Auth - Signup",
            "POST",
            "auth/signup",
            200,
            data=signup_data
        )
        
        if result and 'token' in result:
            self.token = result['token']
            self.user_id = result['user']['id']
            return True
        return False

    def test_auth_login(self):
        """Test user login with existing credentials"""
        # Try to login with a test account
        login_data = {
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        
        result = self.run_test(
            "Auth - Login (existing user)",
            "POST", 
            "auth/login",
            200,
            data=login_data
        )
        
        # If login fails, it's expected since we don't have existing users
        if not result:
            self.log_test("Auth - Login (no existing user)", True, "Expected - no existing test user")
            return True
        
        if result and 'token' in result:
            self.token = result['token']
            self.user_id = result['user']['id']
            return True
        return False

    def test_create_bookmark(self):
        """Test bookmark creation"""
        bookmark_data = {
            "url": "https://example.com"
        }
        
        result = self.run_test(
            "Bookmarks - Create",
            "POST",
            "bookmarks",
            200,
            data=bookmark_data
        )
        
        if result and 'id' in result:
            return result['id']
        return None

    def test_create_bookmark_wikipedia(self):
        """Test bookmark creation with Wikipedia URL"""
        bookmark_data = {
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence"
        }
        
        result = self.run_test(
            "Bookmarks - Create Wikipedia",
            "POST",
            "bookmarks",
            200,
            data=bookmark_data
        )
        
        if result and 'id' in result:
            return result['id']
        return None

    def test_get_bookmarks(self):
        """Test getting bookmarks list"""
        result = self.run_test(
            "Bookmarks - Get List",
            "GET",
            "bookmarks",
            200
        )
        return result is not None

    def test_search_bookmarks(self):
        """Test bookmark search"""
        result = self.run_test(
            "Bookmarks - Search",
            "GET",
            "bookmarks?search=artificial",
            200
        )
        return result is not None

    def test_get_bookmark_detail(self, bookmark_id):
        """Test getting bookmark details"""
        if not bookmark_id:
            self.log_test("Bookmarks - Get Detail", False, "No bookmark ID available")
            return False
            
        result = self.run_test(
            "Bookmarks - Get Detail",
            "GET",
            f"bookmarks/{bookmark_id}",
            200
        )
        return result is not None

    def test_create_collection(self):
        """Test collection creation"""
        collection_data = {
            "name": f"Test Collection {int(time.time())}"
        }
        
        result = self.run_test(
            "Collections - Create",
            "POST",
            "collections",
            200,
            data=collection_data
        )
        
        if result and 'id' in result:
            return result['id']
        return None

    def test_get_collections(self):
        """Test getting collections"""
        result = self.run_test(
            "Collections - Get List",
            "GET",
            "collections",
            200
        )
        return result is not None

    def test_add_to_collection(self, collection_id, bookmark_id):
        """Test adding bookmark to collection"""
        if not collection_id or not bookmark_id:
            self.log_test("Collections - Add Bookmark", False, "Missing collection or bookmark ID")
            return False
            
        data = {"bookmark_id": bookmark_id}
        result = self.run_test(
            "Collections - Add Bookmark",
            "POST",
            f"collections/{collection_id}/add",
            200,
            data=data
        )
        return result is not None

    def test_detect_duplicates(self):
        """Test duplicate detection"""
        result = self.run_test(
            "Duplicates - Detect",
            "GET",
            "bookmarks/duplicates/detect",
            200
        )
        return result is not None

    def test_delete_bookmark(self, bookmark_id):
        """Test bookmark deletion"""
        if not bookmark_id:
            self.log_test("Bookmarks - Delete", False, "No bookmark ID available")
            return False
            
        result = self.run_test(
            "Bookmarks - Delete",
            "DELETE",
            f"bookmarks/{bookmark_id}",
            200
        )
        return result is not None

    def wait_for_ai_processing(self, bookmark_id, max_wait=30):
        """Wait for AI processing to complete"""
        if not bookmark_id:
            return False
            
        print(f"⏳ Waiting for AI processing on bookmark {bookmark_id}...")
        
        for i in range(max_wait):
            result = self.run_test(
                f"AI Processing - Check {i+1}",
                "GET",
                f"bookmarks/{bookmark_id}",
                200
            )
            
            if result and result.get('ai_summary', {}).get('processing_status') == 'completed':
                print(f"✅ AI processing completed after {i+1} seconds")
                return True
            elif result and result.get('ai_summary', {}).get('processing_status') == 'failed':
                print(f"❌ AI processing failed after {i+1} seconds")
                return False
                
            time.sleep(1)
        
        print(f"⏰ AI processing timeout after {max_wait} seconds")
        return False

def main():
    print("🚀 Starting KnolHub API Testing...")
    print("=" * 50)
    
    tester = KnolHubAPITester()
    
    # Test authentication
    print("\n📝 Testing Authentication...")
    if not tester.test_auth_signup():
        print("❌ Signup failed, stopping tests")
        return 1
    
    # Test bookmark operations
    print("\n📚 Testing Bookmark Operations...")
    bookmark_id = tester.test_create_bookmark()
    wikipedia_id = tester.test_create_bookmark_wikipedia()
    
    tester.test_get_bookmarks()
    tester.test_search_bookmarks()
    
    if bookmark_id:
        tester.test_get_bookmark_detail(bookmark_id)
    
    # Test AI processing
    print("\n🤖 Testing AI Processing...")
    if wikipedia_id:
        tester.wait_for_ai_processing(wikipedia_id, max_wait=45)
        # Check the bookmark again to see AI results
        result = tester.run_test(
            "AI Processing - Final Check",
            "GET",
            f"bookmarks/{wikipedia_id}",
            200
        )
        if result and result.get('ai_summary'):
            ai_summary = result['ai_summary']
            print(f"   📝 One sentence: {ai_summary.get('one_sentence', 'N/A')[:100]}...")
            print(f"   📋 Bullet points: {len(ai_summary.get('bullet_points', []))} points")
            print(f"   📖 Long form: {len(ai_summary.get('long_form', ''))} chars")
            print(f"   ✨ Highlights: {len(ai_summary.get('highlights', []))} highlights")
            print(f"   🏷️ Tags: {ai_summary.get('suggested_tags', [])}")
    
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