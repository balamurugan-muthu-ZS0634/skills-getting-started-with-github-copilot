import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app

client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint"""
    
    def test_root_redirect(self):
        """Test that root redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestGetActivities:
    """Test getting the list of activities"""
    
    def test_get_activities_success(self, reset_activities):
        """Test successfully retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
    
    def test_get_activities_contains_required_fields(self, reset_activities):
        """Test that activities contain all required fields"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Chess Club"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
    
    def test_get_activities_participants_list(self, reset_activities):
        """Test that participants list is correct"""
        response = client.get("/activities")
        data = response.json()
        
        chess_participants = data["Chess Club"]["participants"]
        assert isinstance(chess_participants, list)
        assert "michael@mergington.edu" in chess_participants
        assert "daniel@mergington.edu" in chess_participants


class TestSignupForActivity:
    """Test signing up for an activity"""
    
    def test_signup_success(self, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
    
    def test_signup_participant_added(self, reset_activities):
        """Test that participant is actually added to the activity"""
        # Sign up
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        # Verify participant was added
        response = client.get("/activities")
        data = response.json()
        assert "newstudent@mergington.edu" in data["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_already_registered(self, reset_activities):
        """Test signup for an activity already registered for"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_multiple_signups(self, reset_activities):
        """Test multiple different students signing up"""
        emails = [
            "student1@mergington.edu",
            "student2@mergington.edu",
            "student3@mergington.edu"
        ]
        
        for email in emails:
            response = client.post(
                f"/activities/Programming Class/signup?email={email}"
            )
            assert response.status_code == 200
        
        # Verify all were added
        response = client.get("/activities")
        data = response.json()
        participants = data["Programming Class"]["participants"]
        
        for email in emails:
            assert email in participants
    
    def test_signup_preserves_existing_participants(self, reset_activities):
        """Test that signup doesn't overwrite existing participants"""
        response = client.get("/activities")
        initial_data = response.json()
        initial_count = len(initial_data["Gym Class"]["participants"])
        
        # Sign up new student
        client.post("/activities/Gym Class/signup?email=newstudent@mergington.edu")
        
        # Verify initial participants still there
        response = client.get("/activities")
        data = response.json()
        assert "john@mergington.edu" in data["Gym Class"]["participants"]
        assert "olivia@mergington.edu" in data["Gym Class"]["participants"]
        assert len(data["Gym Class"]["participants"]) == initial_count + 1


class TestActivityValidation:
    """Test validation and business logic"""
    
    def test_max_participants_enforcement(self, reset_activities):
        """Test that max_participants field exists (validation would be future work)"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            assert activity["max_participants"] > 0
            assert len(activity["participants"]) <= activity["max_participants"]
    
    def test_email_validation_format(self, reset_activities):
        """Test that email addresses have expected format"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity in data.items():
            for email in activity["participants"]:
                assert "@" in email
                assert ".edu" in email
