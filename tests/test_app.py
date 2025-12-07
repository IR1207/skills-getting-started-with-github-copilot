"""
Test suite for the Mergington High School Activities API

Tests cover:
- GET /activities endpoint
- POST /activities/{activity_name}/signup endpoint
- DELETE /activities/{activity_name}/unregister endpoint
- Error handling and validation
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name] = details


class TestGetActivities:
    """Test cases for GET /activities endpoint"""
    
    def test_get_activities_returns_dict(self, client, reset_activities):
        """Test that /activities returns a dictionary of activities"""
        response = client.get("/activities")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_activities_contains_expected_fields(self, client, reset_activities):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_info in data.items():
            assert "description" in activity_info
            assert "schedule" in activity_info
            assert "max_participants" in activity_info
            assert "participants" in activity_info
            assert isinstance(activity_info["participants"], list)
    
    def test_get_activities_contains_known_activity(self, client, reset_activities):
        """Test that known activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Drama Club" in data
    
    def test_get_activities_participants_are_emails(self, client, reset_activities):
        """Test that participants are email addresses"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_info in data.values():
            for participant in activity_info["participants"]:
                assert "@" in participant


class TestSignupForActivity:
    """Test cases for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        new_email = "test@mergington.edu"
        
        # Get initial participant count
        response_before = client.get("/activities")
        participants_before = response_before.json()["Chess Club"]["participants"].copy()
        
        # Sign up
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": new_email}
        )
        
        # Check participant was added
        response_after = client.get("/activities")
        participants_after = response_after.json()["Chess Club"]["participants"]
        
        assert new_email in participants_after
        assert len(participants_after) == len(participants_before) + 1
    
    def test_signup_duplicate_fails(self, client, reset_activities):
        """Test that signing up twice for same activity fails"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()
    
    def test_signup_nonexistent_activity_fails(self, client, reset_activities):
        """Test that signing up for non-existent activity fails"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_signup_multiple_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple activities"""
        email = "versatile@mergington.edu"
        
        # Sign up for Chess Club
        response1 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Programming Class
        response2 = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify both signups
        response = client.get("/activities")
        data = response.json()
        assert email in data["Chess Club"]["participants"]
        assert email in data["Programming Class"]["participants"]


class TestUnregisterFromActivity:
    """Test cases for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "michael@mergington.edu"
        
        # Verify participant is there initially
        response_before = client.get("/activities")
        assert email in response_before.json()["Chess Club"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        
        # Verify participant was removed
        response_after = client.get("/activities")
        assert email not in response_after.json()["Chess Club"]["participants"]
    
    def test_unregister_not_registered_fails(self, client, reset_activities):
        """Test that unregistering a non-registered user fails"""
        response = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()
    
    def test_unregister_nonexistent_activity_fails(self, client, reset_activities):
        """Test that unregistering from non-existent activity fails"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_unregister_then_reregister(self, client, reset_activities):
        """Test that a student can unregister and re-register"""
        email = "temp@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        # Unregister
        response1 = client.delete(
            "/activities/Chess%20Club/unregister",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Re-register
        response2 = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify registered again
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]


class TestRoot:
    """Test cases for root endpoint"""
    
    def test_root_redirects_to_static(self, client, reset_activities):
        """Test that root endpoint redirects to static HTML"""
        response = client.get("/", follow_redirects=False)
        
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestEdgeCases:
    """Test cases for edge cases and special scenarios"""
    
    def test_email_with_special_characters(self, client, reset_activities):
        """Test handling of emails with special characters"""
        email = "student+tag@mergington.edu"
        
        response = client.post(
            "/activities/Chess%20Club/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]
    
    def test_activity_name_with_spaces(self, client, reset_activities):
        """Test handling of activity names with spaces"""
        # "Programming Class" has spaces
        response = client.post(
            "/activities/Programming%20Class/signup",
            params={"email": "programmer@mergington.edu"}
        )
        
        assert response.status_code == 200
    
    def test_case_sensitive_activity_names(self, client, reset_activities):
        """Test that activity names are case-sensitive"""
        response = client.post(
            "/activities/chess%20club/signup",  # lowercase
            params={"email": "student@mergington.edu"}
        )
        
        # Should fail because "chess club" doesn't exist (only "Chess Club")
        assert response.status_code == 404
    
    def test_activity_max_participants_tracking(self, client, reset_activities):
        """Test that activity max_participants is preserved"""
        response = client.get("/activities")
        
        for activity_info in response.json().values():
            assert isinstance(activity_info["max_participants"], int)
            assert activity_info["max_participants"] > 0
            assert len(activity_info["participants"]) <= activity_info["max_participants"]
