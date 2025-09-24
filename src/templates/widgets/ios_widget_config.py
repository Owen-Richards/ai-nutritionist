"""
iOS WidgetKit Configuration

Configuration templates and specifications for iOS WidgetKit widgets
consuming the AI Nutritionist gamification API.

Widget Types:
- Small (2x2): Adherence ring + streak count
- Medium (4x2): Ring + streak + challenge progress
- Large (4x4): Full dashboard with metrics and deep links

Author: AI Nutritionist Development Team
Date: September 2025
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class iOSWidgetConfiguration:
    """iOS WidgetKit configuration generator."""
    
    def __init__(self):
        self.deep_link_scheme = "ainutritionist"
        self.api_endpoint = "/v1/gamification/summary"
        self.refresh_interval_minutes = 15  # Maximum allowed by iOS
    
    def generate_small_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for small (2x2) iOS widget.
        
        Features:
        - Adherence ring (circular progress)
        - Streak count
        - Compact message
        - Tap to open app
        """
        return {
            "widget_type": "small",
            "size": "2x2",
            "family": "systemSmall",
            "display_name": "Adherence Ring",
            "description": "Track your daily nutrition adherence",
            
            # Data requirements
            "required_api_fields": [
                "adherence_ring.percentage",
                "adherence_ring.ring_color",
                "adherence_ring.level",
                "current_streak.current_count",
                "compact_message",
                "widget_deep_link"
            ],
            
            # Layout configuration
            "layout": {
                "background_color": "#FFFFFF",
                "corner_radius": 16,
                "padding": 12,
                "elements": [
                    {
                        "type": "circular_progress",
                        "id": "adherence_ring",
                        "frame": {"x": 0, "y": 0, "width": 80, "height": 80},
                        "data_binding": "adherence_ring.percentage",
                        "color_binding": "adherence_ring.ring_color",
                        "line_width": 8,
                        "animation": "spring"
                    },
                    {
                        "type": "text",
                        "id": "streak_count",
                        "frame": {"x": 90, "y": 10, "width": 60, "height": 30},
                        "data_binding": "current_streak.current_count",
                        "font": {"size": 24, "weight": "bold"},
                        "color": "#333333",
                        "format": "{value} day"
                    },
                    {
                        "type": "text",
                        "id": "compact_message",
                        "frame": {"x": 0, "y": 90, "width": 150, "height": 40},
                        "data_binding": "compact_message",
                        "font": {"size": 12, "weight": "medium"},
                        "color": "#666666",
                        "lines": 2,
                        "alignment": "center"
                    }
                ]
            },
            
            # Interaction configuration
            "interactions": {
                "tap_action": {
                    "type": "deep_link",
                    "url_binding": "widget_deep_link",
                    "fallback_url": f"{self.deep_link_scheme}://dashboard"
                }
            },
            
            # Update configuration
            "update_policy": {
                "refresh_interval_minutes": self.refresh_interval_minutes,
                "background_refresh": True,
                "cache_policy": "respect_etag",
                "retry_on_failure": True,
                "max_retries": 3
            }
        }
    
    def generate_medium_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for medium (4x2) iOS widget.
        
        Features:
        - Adherence ring
        - Streak information with motivation
        - Challenge progress bar
        - Multiple metrics
        """
        return {
            "widget_type": "medium",
            "size": "4x2",
            "family": "systemMedium",
            "display_name": "Nutrition Dashboard",
            "description": "Complete nutrition tracking overview",
            
            # Data requirements
            "required_api_fields": [
                "adherence_ring.percentage",
                "adherence_ring.ring_color",
                "adherence_ring.trend",
                "current_streak.current_count",
                "current_streak.motivation_message",
                "active_challenge.title",
                "active_challenge.progress",
                "primary_metric",
                "secondary_metrics",
                "widget_deep_link"
            ],
            
            # Layout configuration
            "layout": {
                "background_color": "#FFFFFF",
                "corner_radius": 16,
                "padding": 16,
                "sections": [
                    {
                        "id": "left_section",
                        "frame": {"x": 0, "y": 0, "width": 180, "height": 140},
                        "elements": [
                            {
                                "type": "circular_progress",
                                "id": "adherence_ring",
                                "frame": {"x": 20, "y": 10, "width": 60, "height": 60},
                                "data_binding": "adherence_ring.percentage",
                                "color_binding": "adherence_ring.ring_color",
                                "line_width": 6
                            },
                            {
                                "type": "text",
                                "id": "primary_metric",
                                "frame": {"x": 90, "y": 20, "width": 80, "height": 25},
                                "data_binding": "primary_metric",
                                "font": {"size": 16, "weight": "semibold"},
                                "color": "#333333"
                            },
                            {
                                "type": "text",
                                "id": "trend_indicator",
                                "frame": {"x": 90, "y": 45, "width": 80, "height": 20},
                                "data_binding": "adherence_ring.trend",
                                "font": {"size": 12, "weight": "medium"},
                                "color_map": {
                                    "up": "#00C851",
                                    "down": "#FF4444",
                                    "stable": "#666666"
                                },
                                "format": "Trend: {value}"
                            }
                        ]
                    },
                    {
                        "id": "right_section",
                        "frame": {"x": 180, "y": 0, "width": 180, "height": 140},
                        "elements": [
                            {
                                "type": "text",
                                "id": "streak_title",
                                "frame": {"x": 0, "y": 10, "width": 160, "height": 20},
                                "text": "Current Streak",
                                "font": {"size": 14, "weight": "medium"},
                                "color": "#666666"
                            },
                            {
                                "type": "text",
                                "id": "streak_count",
                                "frame": {"x": 0, "y": 30, "width": 160, "height": 30},
                                "data_binding": "current_streak.current_count",
                                "font": {"size": 28, "weight": "bold"},
                                "color": "#333333",
                                "format": "{value} days"
                            },
                            {
                                "type": "progress_bar",
                                "id": "challenge_progress",
                                "frame": {"x": 0, "y": 70, "width": 160, "height": 8},
                                "data_binding": "active_challenge.progress",
                                "background_color": "#E0E0E0",
                                "fill_color": "#39C0ED",
                                "corner_radius": 4,
                                "condition": "active_challenge != null"
                            },
                            {
                                "type": "text",
                                "id": "challenge_title",
                                "frame": {"x": 0, "y": 85, "width": 160, "height": 40},
                                "data_binding": "active_challenge.title",
                                "font": {"size": 11, "weight": "medium"},
                                "color": "#666666",
                                "lines": 2,
                                "condition": "active_challenge != null"
                            }
                        ]
                    }
                ]
            },
            
            # Interaction configuration
            "interactions": {
                "tap_action": {
                    "type": "deep_link",
                    "url_binding": "widget_deep_link"
                },
                "challenge_tap": {
                    "type": "deep_link",
                    "url": f"{self.deep_link_scheme}://challenges",
                    "element_id": "challenge_progress"
                }
            },
            
            # Update configuration
            "update_policy": {
                "refresh_interval_minutes": self.refresh_interval_minutes,
                "background_refresh": True,
                "cache_policy": "respect_etag",
                "low_data_mode": "compact_only"
            }
        }
    
    def generate_large_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for large (4x4) iOS widget.
        
        Features:
        - Complete dashboard layout
        - All metrics and trends
        - Challenge details
        - Multiple action buttons
        """
        return {
            "widget_type": "large",
            "size": "4x4",
            "family": "systemLarge",
            "display_name": "Nutrition Dashboard Pro",
            "description": "Complete nutrition tracking and gamification",
            
            # Data requirements (all fields)
            "required_api_fields": [
                "adherence_ring",
                "current_streak",
                "active_challenge",
                "total_points",
                "level",
                "primary_metric",
                "secondary_metrics",
                "widget_deep_link"
            ],
            
            # Layout configuration
            "layout": {
                "background_color": "#FFFFFF",
                "corner_radius": 16,
                "padding": 20,
                "sections": [
                    {
                        "id": "header",
                        "frame": {"x": 0, "y": 0, "width": 320, "height": 60},
                        "elements": [
                            {
                                "type": "text",
                                "id": "title",
                                "frame": {"x": 0, "y": 0, "width": 200, "height": 30},
                                "text": "Nutrition Dashboard",
                                "font": {"size": 20, "weight": "bold"},
                                "color": "#333333"
                            },
                            {
                                "type": "text",
                                "id": "level_badge",
                                "frame": {"x": 220, "y": 5, "width": 80, "height": 25},
                                "data_binding": "level",
                                "font": {"size": 14, "weight": "semibold"},
                                "color": "#FFFFFF",
                                "background_color": "#39C0ED",
                                "corner_radius": 12,
                                "format": "Level {value}",
                                "alignment": "center"
                            }
                        ]
                    },
                    {
                        "id": "main_metrics",
                        "frame": {"x": 0, "y": 70, "width": 320, "height": 100},
                        "elements": [
                            {
                                "type": "circular_progress",
                                "id": "main_ring",
                                "frame": {"x": 0, "y": 0, "width": 80, "height": 80},
                                "data_binding": "adherence_ring.percentage",
                                "color_binding": "adherence_ring.ring_color",
                                "line_width": 8,
                                "show_percentage": True
                            },
                            {
                                "type": "metric_grid",
                                "id": "metrics",
                                "frame": {"x": 100, "y": 0, "width": 220, "height": 80},
                                "columns": 2,
                                "spacing": 10,
                                "data_binding": "secondary_metrics",
                                "font": {"size": 12, "weight": "medium"},
                                "color": "#666666"
                            }
                        ]
                    },
                    {
                        "id": "streak_section",
                        "frame": {"x": 0, "y": 180, "width": 320, "height": 80},
                        "background_color": "#F8F9FA",
                        "corner_radius": 12,
                        "padding": 12,
                        "elements": [
                            {
                                "type": "text",
                                "id": "motivation",
                                "frame": {"x": 0, "y": 0, "width": 296, "height": 25},
                                "data_binding": "current_streak.motivation_message",
                                "font": {"size": 14, "weight": "medium"},
                                "color": "#333333"
                            },
                            {
                                "type": "streak_progress",
                                "id": "streak_bar",
                                "frame": {"x": 0, "y": 35, "width": 296, "height": 20},
                                "current_binding": "current_streak.current_count",
                                "next_milestone_binding": "current_streak.next_milestone",
                                "color": "#00C851"
                            }
                        ]
                    },
                    {
                        "id": "challenge_section",
                        "frame": {"x": 0, "y": 270, "width": 320, "height": 100},
                        "condition": "active_challenge != null",
                        "elements": [
                            {
                                "type": "challenge_card",
                                "id": "challenge",
                                "frame": {"x": 0, "y": 0, "width": 320, "height": 100},
                                "title_binding": "active_challenge.title",
                                "description_binding": "active_challenge.description",
                                "progress_binding": "active_challenge.progress",
                                "points_binding": "active_challenge.reward_points"
                            }
                        ]
                    }
                ]
            },
            
            # Interaction configuration
            "interactions": {
                "tap_action": {
                    "type": "deep_link",
                    "url_binding": "widget_deep_link"
                },
                "challenge_action": {
                    "type": "deep_link",
                    "url": f"{self.deep_link_scheme}://challenges",
                    "element_id": "challenge_card"
                },
                "streak_action": {
                    "type": "deep_link",
                    "url": f"{self.deep_link_scheme}://streaks",
                    "element_id": "streak_section"
                }
            },
            
            # Update configuration
            "update_policy": {
                "refresh_interval_minutes": self.refresh_interval_minutes,
                "background_refresh": True,
                "cache_policy": "respect_etag",
                "preload_content": True
            }
        }
    
    def generate_widget_intent_configuration(self) -> Dict[str, Any]:
        """
        Generate Siri Shortcuts and Widget intent configuration.
        
        Enables users to customize widget behavior and create shortcuts.
        """
        return {
            "intent_definition": {
                "class_name": "NutritionWidgetConfigurationIntent",
                "title": "Configure Nutrition Widget",
                "description": "Customize your nutrition tracking widget",
                
                "parameters": [
                    {
                        "name": "metricType",
                        "type": "enum",
                        "title": "Primary Metric",
                        "options": [
                            {"value": "adherence", "title": "Adherence %"},
                            {"value": "streak", "title": "Current Streak"},
                            {"value": "points", "title": "Total Points"},
                            {"value": "level", "title": "Current Level"}
                        ],
                        "default": "adherence"
                    },
                    {
                        "name": "showChallenge",
                        "type": "boolean",
                        "title": "Show Active Challenge",
                        "default": True
                    },
                    {
                        "name": "refreshFrequency",
                        "type": "enum",
                        "title": "Refresh Frequency",
                        "options": [
                            {"value": "5", "title": "Every 5 minutes"},
                            {"value": "15", "title": "Every 15 minutes"},
                            {"value": "30", "title": "Every 30 minutes"}
                        ],
                        "default": "15"
                    }
                ]
            },
            
            "shortcuts": [
                {
                    "title": "Check Nutrition Progress",
                    "subtitle": "View your current nutrition adherence",
                    "intent_class": "CheckProgressIntent",
                    "response_template": "Your adherence is {adherence_percentage}% with a {streak_count} day streak!"
                },
                {
                    "title": "View Current Challenge",
                    "subtitle": "See your active nutrition challenge",
                    "intent_class": "ViewChallengeIntent",
                    "response_template": "Your current challenge: {challenge_title}. Progress: {challenge_progress}%"
                }
            ]
        }


def generate_ios_widget_bundle() -> Dict[str, Any]:
    """Generate complete iOS widget bundle configuration."""
    config = iOSWidgetConfiguration()
    
    return {
        "bundle_info": {
            "identifier": "com.ainutritionist.widgets",
            "display_name": "AI Nutritionist Widgets",
            "version": "1.0",
            "min_ios_version": "14.0",
            "supported_families": ["systemSmall", "systemMedium", "systemLarge"]
        },
        
        "api_configuration": {
            "base_url": "https://api.ainutritionist.com",
            "endpoint": "/v1/gamification/summary",
            "authentication": "bearer_token",
            "cache_policy": "respect_etag",
            "timeout_seconds": 10,
            "retry_attempts": 3
        },
        
        "widget_configurations": {
            "small": config.generate_small_widget_config(),
            "medium": config.generate_medium_widget_config(),
            "large": config.generate_large_widget_config()
        },
        
        "intent_configuration": config.generate_widget_intent_configuration(),
        
        "localizations": {
            "en": {
                "widget_display_name": "AI Nutritionist",
                "widget_description": "Track your nutrition goals",
                "no_data_message": "Open app to start tracking",
                "error_message": "Unable to load data"
            },
            "es": {
                "widget_display_name": "Nutricionista IA",
                "widget_description": "Rastrea tus objetivos nutricionales",
                "no_data_message": "Abre la app para comenzar",
                "error_message": "No se pueden cargar los datos"
            }
        },
        
        "accessibility": {
            "adherence_ring": "Nutrition adherence ring showing {percentage} percent complete",
            "streak_count": "Current streak of {count} days",
            "challenge_progress": "Challenge progress at {percentage} percent complete"
        }
    }


# Save configuration to JSON file
if __name__ == "__main__":
    config = generate_ios_widget_bundle()
    
    with open("ios_widget_config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    
    print("iOS Widget configuration generated successfully!")
