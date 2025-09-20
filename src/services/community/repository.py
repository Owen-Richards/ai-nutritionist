"""Repository layer for community data persistence."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional

from .models import (
    Crew, CrewMember, Reflection, PulseMetric, 
    Challenge, CrewType, MembershipStatus
)


class CommunityRepository:
    """In-memory implementation of community repository for development/testing."""
    
    def __init__(self):
        self._lock = Lock()
        self._crews: Dict[str, Crew] = {}
        self._members: Dict[str, CrewMember] = {}
        self._reflections: Dict[str, Reflection] = {}
        self._pulse_metrics: Dict[str, List[PulseMetric]] = {}
        self._challenges: Dict[str, Challenge] = {}
        self._user_memberships: Dict[str, Dict[str, str]] = {}  # user_id -> {crew_id: member_id}
        self._consent_log: List[Dict] = []
    
    def save_crew(self, crew: Crew) -> None:
        """Save a crew to storage."""
        with self._lock:
            self._crews[crew.crew_id] = copy.deepcopy(crew)
    
    def get_crew(self, crew_id: str) -> Optional[Crew]:
        """Retrieve crew by ID."""
        with self._lock:
            crew = self._crews.get(crew_id)
            return copy.deepcopy(crew) if crew else None
    
    def list_crews_by_type(self, crew_type: Optional[CrewType] = None) -> List[Crew]:
        """List all crews, optionally filtered by type."""
        with self._lock:
            crews = list(self._crews.values())
            if crew_type:
                crews = [crew for crew in crews if crew.crew_type == crew_type]
            return [copy.deepcopy(crew) for crew in crews if crew.is_active]
    
    def add_crew_member(self, member: CrewMember) -> None:
        """Add a member to a crew."""
        with self._lock:
            self._members[member.member_id] = copy.deepcopy(member)
            
            # Update user memberships index
            if member.user_id not in self._user_memberships:
                self._user_memberships[member.user_id] = {}
            self._user_memberships[member.user_id][member.crew_id] = member.member_id
    
    def get_crew_members(self, crew_id: str) -> List[CrewMember]:
        """Get all members of a crew."""
        with self._lock:
            return [
                copy.deepcopy(member) for member in self._members.values()
                if member.crew_id == crew_id and member.status == MembershipStatus.ACTIVE
            ]
    
    def get_crew_member_count(self, crew_id: str) -> int:
        """Get count of active members in a crew."""
        return len(self.get_crew_members(crew_id))
    
    def get_user_membership(self, user_id: str, crew_id: str) -> Optional[CrewMember]:
        """Get user's membership in a specific crew."""
        with self._lock:
            memberships = self._user_memberships.get(user_id, {})
            member_id = memberships.get(crew_id)
            if member_id and member_id in self._members:
                return copy.deepcopy(self._members[member_id])
            return None
    
    def get_user_crews(self, user_id: str) -> List[Crew]:
        """Get all crews a user belongs to."""
        with self._lock:
            memberships = self._user_memberships.get(user_id, {})
            crew_ids = []
            
            for crew_id, member_id in memberships.items():
                member = self._members.get(member_id)
                if member and member.status == MembershipStatus.ACTIVE:
                    crew_ids.append(crew_id)
            
            return [copy.deepcopy(self._crews[crew_id]) for crew_id in crew_ids if crew_id in self._crews]
    
    def save_reflection(self, reflection: Reflection) -> None:
        """Save a user reflection."""
        with self._lock:
            self._reflections[reflection.reflection_id] = copy.deepcopy(reflection)
    
    def get_crew_reflections(self, crew_id: str, since: Optional[datetime] = None, limit: int = 50) -> List[Reflection]:
        """Get recent reflections for a crew."""
        with self._lock:
            reflections = [
                reflection for reflection in self._reflections.values()
                if reflection.crew_id == crew_id
            ]
            
            if since:
                reflections = [r for r in reflections if r.created_at >= since]
            
            # Sort by creation time, most recent first
            reflections.sort(key=lambda r: r.created_at, reverse=True)
            
            return [copy.deepcopy(r) for r in reflections[:limit]]
    
    def save_pulse_metrics(self, user_id: str, metrics: List[PulseMetric]) -> None:
        """Save pulse metrics for a user."""
        with self._lock:
            if user_id not in self._pulse_metrics:
                self._pulse_metrics[user_id] = []
            
            self._pulse_metrics[user_id].extend([copy.deepcopy(m) for m in metrics])
    
    def get_crew_pulse_metrics(self, crew_id: str, since: Optional[datetime] = None) -> List[PulseMetric]:
        """Get pulse metrics for all crew members."""
        with self._lock:
            crew_members = self.get_crew_members(crew_id)
            user_ids = [member.user_id for member in crew_members]
            
            all_metrics = []
            for user_id in user_ids:
                user_metrics = self._pulse_metrics.get(user_id, [])
                if since:
                    user_metrics = [m for m in user_metrics if m.recorded_at >= since]
                all_metrics.extend(user_metrics)
            
            return [copy.deepcopy(m) for m in all_metrics]
    
    def save_challenge(self, challenge: Challenge) -> None:
        """Save a challenge."""
        with self._lock:
            self._challenges[challenge.challenge_id] = copy.deepcopy(challenge)
    
    def get_active_challenges(self, crew_id: str) -> List[Challenge]:
        """Get active challenges for a crew."""
        with self._lock:
            now = datetime.now(timezone.utc)
            active_challenges = [
                challenge for challenge in self._challenges.values()
                if (challenge.crew_id == crew_id and 
                    challenge.start_date <= now <= challenge.end_date)
            ]
            return [copy.deepcopy(c) for c in active_challenges]
    
    def update_member_status(self, member_id: str, status: MembershipStatus) -> bool:
        """Update member status."""
        with self._lock:
            if member_id in self._members:
                self._members[member_id].status = status
                return True
            return False
    
    def update_member_preferences(self, member_id: str, **kwargs) -> bool:
        """Update member preferences."""
        with self._lock:
            if member_id in self._members:
                member = self._members[member_id]
                for key, value in kwargs.items():
                    if hasattr(member, key):
                        setattr(member, key, value)
                return True
            return False
    
    def delete_user_data(self, user_id: str) -> bool:
        """Delete all user data (GDPR compliance)."""
        with self._lock:
            # Remove user memberships
            if user_id in self._user_memberships:
                member_ids = list(self._user_memberships[user_id].values())
                for member_id in member_ids:
                    if member_id in self._members:
                        del self._members[member_id]
                del self._user_memberships[user_id]
            
            # Remove user reflections
            reflections_to_remove = [
                refl_id for refl_id, reflection in self._reflections.items()
                if reflection.user_id == user_id
            ]
            for refl_id in reflections_to_remove:
                del self._reflections[refl_id]
            
            # Remove user pulse metrics
            if user_id in self._pulse_metrics:
                del self._pulse_metrics[user_id]
            
            return True
    
    def log_consent_change(self, user_id: str, crew_id: str, consent_type: str, new_value: bool) -> bool:
        """Log consent changes for audit trail."""
        with self._lock:
            log_entry = {
                "user_id": user_id,
                "crew_id": crew_id,
                "consent_type": consent_type,
                "new_value": new_value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            self._consent_log.append(log_entry)
            return True
