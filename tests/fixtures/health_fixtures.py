"""Health data and wearable integration test fixtures"""

import pytest
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from uuid import uuid4
import random

from src.models.user import WearableIntegration


class HealthMetricsFactory:
    """Factory for creating health metrics data"""
    
    @staticmethod
    def create_basic_metrics(
        user_id: str = None,
        date_recorded: date = None
    ) -> Dict[str, Any]:
        if user_id is None:
            user_id = str(uuid4())
        if date_recorded is None:
            date_recorded = date.today()
        
        return {
            'user_id': user_id,
            'date': date_recorded.isoformat(),
            'weight_lbs': round(random.uniform(140, 200), 1),
            'body_fat_percentage': round(random.uniform(15, 35), 1),
            'muscle_mass_lbs': round(random.uniform(50, 80), 1),
            'resting_heart_rate': random.randint(60, 80),
            'blood_pressure_systolic': random.randint(110, 140),
            'blood_pressure_diastolic': random.randint(70, 90),
            'energy_level': random.randint(1, 10),
            'sleep_hours': round(random.uniform(6, 9), 1),
            'stress_level': random.randint(1, 10),
            'hydration_glasses': random.randint(4, 12),
            'recorded_at': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def weight_loss_progression(
        user_id: str = None,
        start_weight: float = 180.0,
        target_weight: float = 160.0,
        weeks: int = 12
    ) -> List[Dict[str, Any]]:
        """Generate weight loss progression over time"""
        if user_id is None:
            user_id = str(uuid4())
        
        metrics = []
        weight_loss_per_week = (start_weight - target_weight) / weeks
        
        for week in range(weeks + 1):
            current_date = date.today() - timedelta(weeks=weeks-week)
            current_weight = start_weight - (weight_loss_per_week * week)
            # Add some realistic variation
            current_weight += random.uniform(-1.5, 1.5)
            
            metrics.append({
                'user_id': user_id,
                'date': current_date.isoformat(),
                'weight_lbs': round(current_weight, 1),
                'body_fat_percentage': round(30 - (week * 0.5), 1),
                'energy_level': min(10, 6 + week // 2),  # Energy improves over time
                'recorded_at': datetime.combine(current_date, datetime.min.time()).isoformat()
            })
        
        return metrics
    
    @staticmethod
    def diabetic_monitoring(
        user_id: str = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate diabetic monitoring data"""
        if user_id is None:
            user_id = str(uuid4())
        
        metrics = []
        for day in range(days):
            current_date = date.today() - timedelta(days=days-day-1)
            
            # Multiple readings per day for diabetes monitoring
            for reading_time, base_glucose in [("morning", 95), ("post_meal", 140), ("evening", 110)]:
                glucose_variation = random.uniform(-15, 25)
                glucose_reading = max(70, base_glucose + glucose_variation)
                
                metrics.append({
                    'user_id': user_id,
                    'date': current_date.isoformat(),
                    'reading_time': reading_time,
                    'blood_glucose_mg_dl': round(glucose_reading, 0),
                    'carbs_consumed_g': random.randint(20, 60) if reading_time == "post_meal" else 0,
                    'insulin_units': random.randint(2, 8) if reading_time == "post_meal" else 0,
                    'recorded_at': datetime.combine(current_date, datetime.min.time()).isoformat()
                })
        
        return metrics


class ExerciseDataFactory:
    """Factory for creating exercise and activity data"""
    
    @staticmethod
    def create_workout(
        user_id: str = None,
        workout_date: date = None,
        workout_type: str = "strength_training"
    ) -> Dict[str, Any]:
        if user_id is None:
            user_id = str(uuid4())
        if workout_date is None:
            workout_date = date.today()
        
        workout_types = {
            "strength_training": {
                "duration_minutes": random.randint(45, 90),
                "calories_burned": random.randint(200, 400),
                "exercises": ["squats", "deadlifts", "bench_press", "rows"],
                "sets_completed": random.randint(12, 20)
            },
            "cardio": {
                "duration_minutes": random.randint(20, 60),
                "calories_burned": random.randint(150, 500),
                "distance_miles": round(random.uniform(2, 8), 2),
                "avg_heart_rate": random.randint(140, 170)
            },
            "yoga": {
                "duration_minutes": random.randint(30, 90),
                "calories_burned": random.randint(100, 300),
                "flexibility_score": random.randint(6, 10),
                "poses_completed": random.randint(15, 30)
            }
        }
        
        base_data = {
            'user_id': user_id,
            'workout_id': str(uuid4()),
            'date': workout_date.isoformat(),
            'type': workout_type,
            'completed': True,
            'recorded_at': datetime.combine(workout_date, datetime.min.time()).isoformat()
        }
        
        base_data.update(workout_types.get(workout_type, workout_types["cardio"]))
        return base_data
    
    @staticmethod
    def weekly_activity_summary(
        user_id: str = None,
        week_start: date = None
    ) -> Dict[str, Any]:
        if user_id is None:
            user_id = str(uuid4())
        if week_start is None:
            week_start = date.today() - timedelta(days=date.today().weekday())
        
        workouts = []
        total_calories = 0
        total_minutes = 0
        
        # Generate 3-5 workouts per week
        for day in range(random.randint(3, 5)):
            workout_date = week_start + timedelta(days=day)
            workout_type = random.choice(["strength_training", "cardio", "yoga"])
            workout = ExerciseDataFactory.create_workout(user_id, workout_date, workout_type)
            workouts.append(workout)
            total_calories += workout.get("calories_burned", 0)
            total_minutes += workout.get("duration_minutes", 0)
        
        return {
            'user_id': user_id,
            'week_start': week_start.isoformat(),
            'workouts': workouts,
            'total_workouts': len(workouts),
            'total_calories_burned': total_calories,
            'total_minutes_exercised': total_minutes,
            'average_workout_duration': round(total_minutes / len(workouts), 1) if workouts else 0
        }
    
    @staticmethod
    def daily_steps_data(
        user_id: str = None,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Generate daily steps data"""
        if user_id is None:
            user_id = str(uuid4())
        
        steps_data = []
        for day in range(days):
            current_date = date.today() - timedelta(days=days-day-1)
            
            # Vary steps based on day of week (weekends might be different)
            is_weekend = current_date.weekday() >= 5
            base_steps = 8000 if not is_weekend else 12000
            variation = random.randint(-2000, 4000)
            daily_steps = max(2000, base_steps + variation)
            
            steps_data.append({
                'user_id': user_id,
                'date': current_date.isoformat(),
                'steps': daily_steps,
                'distance_miles': round(daily_steps * 0.0005, 2),  # Rough conversion
                'calories_burned': round(daily_steps * 0.04, 0),  # Rough conversion
                'active_minutes': random.randint(30, 120),
                'floors_climbed': random.randint(5, 25),
                'recorded_at': datetime.combine(current_date, datetime.min.time()).isoformat()
            })
        
        return steps_data


class WearableDataFactory:
    """Factory for creating wearable device sync data"""
    
    @staticmethod
    def create_fitbit_integration(user_id: str = None) -> WearableIntegration:
        if user_id is None:
            user_id = str(uuid4())
        
        return WearableIntegration(
            device_type="fitbit",
            device_id=f"fitbit_{random.randint(100000, 999999)}",
            connected_at=datetime.utcnow() - timedelta(days=30),
            last_sync=datetime.utcnow() - timedelta(hours=2),
            sync_frequency_hours=4,
            permissions_granted=["steps", "heart_rate", "sleep", "calories"],
            auto_sync=True
        )
    
    @staticmethod
    def create_apple_watch_integration(user_id: str = None) -> WearableIntegration:
        if user_id is None:
            user_id = str(uuid4())
        
        return WearableIntegration(
            device_type="apple_watch",
            device_id=f"apple_{random.randint(100000, 999999)}",
            connected_at=datetime.utcnow() - timedelta(days=15),
            last_sync=datetime.utcnow() - timedelta(minutes=30),
            sync_frequency_hours=1,
            permissions_granted=["steps", "heart_rate", "workouts", "calories", "sleep"],
            auto_sync=True
        )
    
    @staticmethod
    def create_sync_data(
        device_type: str = "fitbit",
        user_id: str = None,
        sync_date: datetime = None
    ) -> Dict[str, Any]:
        if user_id is None:
            user_id = str(uuid4())
        if sync_date is None:
            sync_date = datetime.utcnow()
        
        base_data = {
            'user_id': user_id,
            'device_type': device_type,
            'sync_timestamp': sync_date.isoformat(),
            'sync_status': 'success',
            'data_points_synced': random.randint(50, 200)
        }
        
        if device_type == "fitbit":
            base_data.update({
                'steps_today': random.randint(5000, 15000),
                'calories_burned_today': random.randint(1800, 2500),
                'active_minutes_today': random.randint(30, 120),
                'resting_heart_rate': random.randint(60, 80),
                'sleep_hours_last_night': round(random.uniform(6, 9), 1)
            })
        elif device_type == "apple_watch":
            base_data.update({
                'steps_today': random.randint(6000, 18000),
                'calories_burned_today': random.randint(2000, 3000),
                'stand_hours_today': random.randint(8, 12),
                'exercise_minutes_today': random.randint(0, 60),
                'heart_rate_zones': {
                    'resting': random.randint(60, 80),
                    'fat_burn': random.randint(100, 120),
                    'cardio': random.randint(140, 160),
                    'peak': random.randint(170, 190)
                }
            })
        
        return base_data


# Pytest fixtures
@pytest.fixture
def health_metrics_factory():
    """Factory fixture for creating health metrics"""
    return HealthMetricsFactory


@pytest.fixture
def exercise_factory():
    """Factory fixture for creating exercise data"""
    return ExerciseDataFactory


@pytest.fixture
def wearable_factory():
    """Factory fixture for creating wearable data"""
    return WearableDataFactory


@pytest.fixture
def create_health_metrics():
    """Create basic health metrics"""
    return HealthMetricsFactory.create_basic_metrics()


@pytest.fixture
def create_exercise_data():
    """Create exercise data"""
    return ExerciseDataFactory.create_workout()


@pytest.fixture
def create_wearable_sync_data():
    """Create wearable sync data"""
    return WearableDataFactory.create_sync_data()


@pytest.fixture
def weight_loss_journey():
    """Create weight loss progression data"""
    user_id = str(uuid4())
    return HealthMetricsFactory.weight_loss_progression(
        user_id=user_id,
        start_weight=185.0,
        target_weight=165.0,
        weeks=16
    )


@pytest.fixture
def diabetic_monitoring_data():
    """Create diabetic monitoring data"""
    user_id = str(uuid4())
    return HealthMetricsFactory.diabetic_monitoring(user_id=user_id, days=30)


@pytest.fixture
def weekly_workout_summary():
    """Create weekly workout summary"""
    return ExerciseDataFactory.weekly_activity_summary()


@pytest.fixture
def daily_steps_history():
    """Create daily steps history"""
    return ExerciseDataFactory.daily_steps_data(days=30)


@pytest.fixture
def wearable_integrations():
    """Collection of wearable integrations"""
    user_id = str(uuid4())
    return {
        'fitbit': WearableDataFactory.create_fitbit_integration(user_id),
        'apple_watch': WearableDataFactory.create_apple_watch_integration(user_id)
    }


@pytest.fixture
def health_data_collection():
    """Complete health data collection for testing"""
    user_id = str(uuid4())
    return {
        'basic_metrics': HealthMetricsFactory.create_basic_metrics(user_id),
        'weight_loss_data': HealthMetricsFactory.weight_loss_progression(user_id),
        'exercise_summary': ExerciseDataFactory.weekly_activity_summary(user_id),
        'steps_data': ExerciseDataFactory.daily_steps_data(user_id, 30),
        'fitbit_sync': WearableDataFactory.create_sync_data("fitbit", user_id),
        'apple_watch_sync': WearableDataFactory.create_sync_data("apple_watch", user_id)
    }
