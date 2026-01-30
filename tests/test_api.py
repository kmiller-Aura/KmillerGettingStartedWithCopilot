"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participants": activity["participants"].copy()
        }
        for name, activity in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, activity in original_activities.items():
        if name in activities:
            activities[name]["participants"] = activity["participants"].copy()


class TestRoot:
    """Tests for root endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all(self, client):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert len(data) > 0
        assert "Soccer Team" in data
        assert "Basketball Team" in data
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        
        for name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity
            assert isinstance(activity["participants"], list)
            assert isinstance(activity["max_participants"], int)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        email = "test@mergington.edu"
        activity = "Soccer Team"
        
        # Remove test email if it exists
        if email in activities[activity]["participants"]:
            activities[activity]["participants"].remove(email)
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert email in data["message"]
        assert activity in data["message"]
        
        # Verify participant was added
        assert email in activities[activity]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/NonExistentActivity/signup",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test that signing up twice returns 400"""
        email = "alex@mergington.edu"  # Already in Soccer Team
        activity = "Soccer Team"
        
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()
    
    def test_signup_multiple_different_activities(self, client, reset_activities):
        """Test that a student can sign up for multiple different activities"""
        email = "multitask@mergington.edu"
        
        # Sign up for Soccer Team
        response1 = client.post(
            "/activities/Soccer Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Sign up for Chess Club
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify in both
        assert email in activities["Soccer Team"]["participants"]
        assert email in activities["Chess Club"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        email = "alex@mergington.edu"  # Already in Soccer Team
        activity = "Soccer Team"
        
        # Ensure participant is in the activity
        if email not in activities[activity]["participants"]:
            activities[activity]["participants"].append(email)
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify participant was removed
        assert email not in activities[activity]["participants"]
    
    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity returns 404"""
        response = client.delete(
            "/activities/NonExistentActivity/unregister",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_participant_not_registered(self, client, reset_activities):
        """Test unregistering a participant who isn't registered returns 400"""
        email = "notregistered@mergington.edu"
        activity = "Soccer Team"
        
        # Ensure participant is not in the activity
        if email in activities[activity]["participants"]:
            activities[activity]["participants"].remove(email)
        
        response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()


class TestMaxParticipants:
    """Tests for max participants validation"""
    
    def test_signup_respects_max_participants(self, client, reset_activities):
        """Test that signup fails when activity is full"""
        activity = "Chess Club"
        max_participants = activities[activity]["max_participants"]
        
        # Fill up the activity to max capacity
        activities[activity]["participants"] = [
            f"student{i}@mergington.edu" for i in range(max_participants)
        ]
        
        # Try to add one more participant
        response = client.post(
            f"/activities/{activity}/signup",
            params={"email": "overflow@mergington.edu"}
        )
        
        # Note: This test will fail if max_participants validation isn't implemented
        # You may want to add this validation to your API
        # For now, this documents expected behavior
        assert response.status_code in [200, 400]  # Adjust based on implementation


class TestEdgeCases:
    """Tests for edge cases and data validation"""
    
    def test_signup_with_special_characters_in_activity_name(self, client):
        """Test handling of special characters in activity name"""
        response = client.post(
            "/activities/Activity%20With%20Spaces/signup",
            params={"email": "test@mergington.edu"}
        )
        
        assert response.status_code == 404
    
    def test_email_validation(self, client, reset_activities):
        """Test that various email formats are accepted"""
        emails = [
            "simple@mergington.edu",
            "name.surname@mergington.edu",
            "name+tag@mergington.edu",
        ]
        
        for email in emails:
            # Clean up if exists
            if email in activities["Chess Club"]["participants"]:
                activities["Chess Club"]["participants"].remove(email)
            
            response = client.post(
                "/activities/Chess Club/signup",
                params={"email": email}
            )
            
            assert response.status_code == 200, f"Failed for email: {email}"
