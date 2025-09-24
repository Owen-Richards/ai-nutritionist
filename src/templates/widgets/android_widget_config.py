"""
Android AppWidget Configuration

Configuration templates and specifications for Android AppWidget widgets
consuming the AI Nutritionist gamification API.

Widget Types:
- Small (2x1): Adherence percentage + streak
- Medium (4x1): Ring + streak + challenge
- Large (4x2): Full dashboard with metrics

Author: AI Nutritionist Development Team
Date: September 2025
"""

import json
from typing import Dict, Any, List
from datetime import datetime


class AndroidWidgetConfiguration:
    """Android AppWidget configuration generator."""
    
    def __init__(self):
        self.deep_link_scheme = "ainutritionist"
        self.api_endpoint = "/v1/gamification/summary"
        self.update_interval_minutes = 15
        self.package_name = "com.ainutritionist.app"
    
    def generate_small_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for small (2x1) Android widget.
        
        Features:
        - Adherence percentage text
        - Streak count
        - Compact layout
        """
        return {
            "widget_type": "small",
            "size": "2x1",
            "cells": {"width": 2, "height": 1},
            "display_name": "Nutrition Progress",
            "description": "Quick view of your nutrition progress",
            
            # Widget provider configuration
            "provider_config": {
                "min_width": "110dp",
                "min_height": "40dp",
                "update_period_millis": self.update_interval_minutes * 60 * 1000,
                "resize_mode": "horizontal|vertical",
                "widget_category": "home_screen",
                "initial_layout": "@layout/widget_small_initial",
                "configure_activity": f"{self.package_name}.widgets.ConfigureActivity"
            },
            
            # Layout XML structure
            "layout": {
                "root": {
                    "type": "LinearLayout",
                    "orientation": "horizontal",
                    "background": "@drawable/widget_background",
                    "padding": "8dp",
                    "gravity": "center_vertical",
                    "children": [
                        {
                            "type": "TextView",
                            "id": "@+id/adherence_percentage",
                            "layout_width": "0dp",
                            "layout_height": "wrap_content",
                            "layout_weight": "1",
                            "text": "85%",
                            "textSize": "18sp",
                            "textStyle": "bold",
                            "textColor": "@color/primary_text",
                            "gravity": "center",
                            "data_binding": "adherence_ring.percentage",
                            "format": "{value:.0f}%"
                        },
                        {
                            "type": "View",
                            "layout_width": "1dp",
                            "layout_height": "match_parent",
                            "background": "@color/divider",
                            "layout_marginLeft": "4dp",
                            "layout_marginRight": "4dp"
                        },
                        {
                            "type": "LinearLayout",
                            "orientation": "vertical",
                            "layout_width": "0dp",
                            "layout_height": "wrap_content",
                            "layout_weight": "1",
                            "gravity": "center",
                            "children": [
                                {
                                    "type": "TextView",
                                    "id": "@+id/streak_count",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "text": "12",
                                    "textSize": "14sp",
                                    "textStyle": "bold",
                                    "textColor": "@color/primary_text",
                                    "data_binding": "current_streak.current_count"
                                },
                                {
                                    "type": "TextView",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "text": "days",
                                    "textSize": "10sp",
                                    "textColor": "@color/secondary_text"
                                }
                            ]
                        }
                    ]
                }
            },
            
            # Data binding configuration
            "data_bindings": {
                "@+id/adherence_percentage": {
                    "field": "adherence_ring.percentage",
                    "format": "{value:.0f}%",
                    "color_conditions": [
                        {"condition": "value >= 90", "color": "@color/excellent"},
                        {"condition": "value >= 70", "color": "@color/good"},
                        {"condition": "value >= 40", "color": "@color/fair"},
                        {"default": "@color/poor"}
                    ]
                },
                "@+id/streak_count": {
                    "field": "current_streak.current_count",
                    "format": "{value}"
                }
            },
            
            # Click actions
            "click_actions": {
                "root": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://dashboard",
                    "flags": ["FLAG_ACTIVITY_NEW_TASK"]
                }
            },
            
            # Update configuration
            "update_config": {
                "auto_update": True,
                "update_interval_minutes": self.update_interval_minutes,
                "retry_on_failure": True,
                "cache_duration_minutes": 10,
                "background_update": True
            }
        }
    
    def generate_medium_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for medium (4x1) Android widget.
        
        Features:
        - Circular progress view
        - Streak information
        - Challenge progress
        """
        return {
            "widget_type": "medium",
            "size": "4x1",
            "cells": {"width": 4, "height": 1},
            "display_name": "Nutrition Dashboard",
            "description": "Comprehensive nutrition tracking view",
            
            # Widget provider configuration
            "provider_config": {
                "min_width": "250dp",
                "min_height": "40dp",
                "update_period_millis": self.update_interval_minutes * 60 * 1000,
                "resize_mode": "horizontal|vertical",
                "widget_category": "home_screen",
                "initial_layout": "@layout/widget_medium_initial"
            },
            
            # Layout XML structure
            "layout": {
                "root": {
                    "type": "RelativeLayout",
                    "background": "@drawable/widget_background",
                    "padding": "12dp",
                    "children": [
                        {
                            "type": "ProgressBar",
                            "id": "@+id/adherence_ring",
                            "style": "@style/Widget.ProgressBar.Horizontal.Ring",
                            "layout_width": "48dp",
                            "layout_height": "48dp",
                            "layout_alignParentLeft": "true",
                            "layout_centerVertical": "true",
                            "max": "100",
                            "progress": "85",
                            "progressTint": "@color/ring_color",
                            "data_binding": "adherence_ring.percentage"
                        },
                        {
                            "type": "TextView",
                            "id": "@+id/adherence_text",
                            "layout_width": "wrap_content",
                            "layout_height": "wrap_content",
                            "layout_centerInParent": "true",
                            "layout_alignLeft": "@+id/adherence_ring",
                            "layout_alignRight": "@+id/adherence_ring",
                            "text": "85%",
                            "textSize": "10sp",
                            "textStyle": "bold",
                            "textColor": "@color/primary_text",
                            "gravity": "center",
                            "data_binding": "adherence_ring.percentage",
                            "format": "{value:.0f}%"
                        },
                        {
                            "type": "LinearLayout",
                            "orientation": "vertical",
                            "layout_width": "wrap_content",
                            "layout_height": "wrap_content",
                            "layout_toRightOf": "@+id/adherence_ring",
                            "layout_marginLeft": "12dp",
                            "layout_centerVertical": "true",
                            "children": [
                                {
                                    "type": "TextView",
                                    "id": "@+id/streak_title",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "text": "Streak",
                                    "textSize": "10sp",
                                    "textColor": "@color/secondary_text"
                                },
                                {
                                    "type": "TextView",
                                    "id": "@+id/streak_count",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "text": "12 days",
                                    "textSize": "14sp",
                                    "textStyle": "bold",
                                    "textColor": "@color/primary_text",
                                    "data_binding": "current_streak.current_count",
                                    "format": "{value} days"
                                }
                            ]
                        },
                        {
                            "type": "LinearLayout",
                            "orientation": "vertical",
                            "layout_width": "wrap_content",
                            "layout_height": "wrap_content",
                            "layout_alignParentRight": "true",
                            "layout_centerVertical": "true",
                            "visibility": "gone",
                            "id": "@+id/challenge_section",
                            "data_visibility": "active_challenge != null",
                            "children": [
                                {
                                    "type": "TextView",
                                    "id": "@+id/challenge_title",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "text": "Challenge",
                                    "textSize": "10sp",
                                    "textColor": "@color/secondary_text"
                                },
                                {
                                    "type": "ProgressBar",
                                    "id": "@+id/challenge_progress",
                                    "style": "@style/Widget.ProgressBar.Horizontal.Small",
                                    "layout_width": "60dp",
                                    "layout_height": "8dp",
                                    "max": "100",
                                    "progress": "67",
                                    "progressTint": "@color/challenge_color",
                                    "data_binding": "active_challenge.progress",
                                    "format": "{value * 100:.0f}"
                                }
                            ]
                        }
                    ]
                }
            },
            
            # Data binding configuration
            "data_bindings": {
                "@+id/adherence_ring": {
                    "field": "adherence_ring.percentage",
                    "type": "progress",
                    "color_field": "adherence_ring.ring_color"
                },
                "@+id/adherence_text": {
                    "field": "adherence_ring.percentage",
                    "format": "{value:.0f}%"
                },
                "@+id/streak_count": {
                    "field": "current_streak.current_count",
                    "format": "{value} days"
                },
                "@+id/challenge_progress": {
                    "field": "active_challenge.progress",
                    "format": "{value * 100:.0f}",
                    "type": "progress"
                },
                "@+id/challenge_section": {
                    "visibility_condition": "active_challenge != null"
                }
            },
            
            # Click actions
            "click_actions": {
                "root": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://dashboard"
                },
                "@+id/challenge_section": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://challenges"
                }
            }
        }
    
    def generate_large_widget_config(self) -> Dict[str, Any]:
        """
        Generate configuration for large (4x2) Android widget.
        
        Features:
        - Complete dashboard layout
        - Multiple metrics
        - Challenge card
        - Action buttons
        """
        return {
            "widget_type": "large",
            "size": "4x2",
            "cells": {"width": 4, "height": 2},
            "display_name": "Nutrition Dashboard Pro",
            "description": "Complete nutrition tracking dashboard",
            
            # Widget provider configuration
            "provider_config": {
                "min_width": "250dp",
                "min_height": "110dp",
                "update_period_millis": self.update_interval_minutes * 60 * 1000,
                "resize_mode": "horizontal|vertical",
                "widget_category": "home_screen",
                "initial_layout": "@layout/widget_large_initial"
            },
            
            # Layout XML structure
            "layout": {
                "root": {
                    "type": "LinearLayout",
                    "orientation": "vertical",
                    "background": "@drawable/widget_background",
                    "padding": "16dp",
                    "children": [
                        {
                            "type": "LinearLayout",
                            "orientation": "horizontal",
                            "layout_width": "match_parent",
                            "layout_height": "0dp",
                            "layout_weight": "1",
                            "children": [
                                {
                                    "type": "RelativeLayout",
                                    "layout_width": "0dp",
                                    "layout_height": "match_parent",
                                    "layout_weight": "1",
                                    "children": [
                                        {
                                            "type": "ProgressBar",
                                            "id": "@+id/main_ring",
                                            "style": "@style/Widget.ProgressBar.Horizontal.Ring.Large",
                                            "layout_width": "60dp",
                                            "layout_height": "60dp",
                                            "layout_centerInParent": "true",
                                            "max": "100",
                                            "progress": "85",
                                            "data_binding": "adherence_ring.percentage"
                                        },
                                        {
                                            "type": "TextView",
                                            "id": "@+id/main_percentage",
                                            "layout_width": "wrap_content",
                                            "layout_height": "wrap_content",
                                            "layout_centerInParent": "true",
                                            "text": "85%",
                                            "textSize": "14sp",
                                            "textStyle": "bold",
                                            "textColor": "@color/primary_text",
                                            "data_binding": "adherence_ring.percentage",
                                            "format": "{value:.0f}%"
                                        }
                                    ]
                                },
                                {
                                    "type": "GridLayout",
                                    "id": "@+id/metrics_grid",
                                    "layout_width": "0dp",
                                    "layout_height": "match_parent",
                                    "layout_weight": "2",
                                    "columnCount": "2",
                                    "rowCount": "2",
                                    "layout_marginLeft": "16dp",
                                    "children": [
                                        {
                                            "type": "TextView",
                                            "text": "Streak",
                                            "textSize": "10sp",
                                            "textColor": "@color/secondary_text"
                                        },
                                        {
                                            "type": "TextView",
                                            "text": "Level",
                                            "textSize": "10sp",
                                            "textColor": "@color/secondary_text"
                                        },
                                        {
                                            "type": "TextView",
                                            "id": "@+id/streak_value",
                                            "text": "12 days",
                                            "textSize": "12sp",
                                            "textStyle": "bold",
                                            "textColor": "@color/primary_text",
                                            "data_binding": "current_streak.current_count",
                                            "format": "{value} days"
                                        },
                                        {
                                            "type": "TextView",
                                            "id": "@+id/level_value",
                                            "text": "Level 3",
                                            "textSize": "12sp",
                                            "textStyle": "bold",
                                            "textColor": "@color/primary_text",
                                            "data_binding": "level",
                                            "format": "Level {value}"
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "LinearLayout",
                            "id": "@+id/challenge_card",
                            "orientation": "horizontal",
                            "layout_width": "match_parent",
                            "layout_height": "wrap_content",
                            "layout_marginTop": "8dp",
                            "padding": "8dp",
                            "background": "@drawable/challenge_card_background",
                            "visibility": "gone",
                            "data_visibility": "active_challenge != null",
                            "children": [
                                {
                                    "type": "LinearLayout",
                                    "orientation": "vertical",
                                    "layout_width": "0dp",
                                    "layout_height": "wrap_content",
                                    "layout_weight": "1",
                                    "children": [
                                        {
                                            "type": "TextView",
                                            "id": "@+id/challenge_title",
                                            "layout_width": "wrap_content",
                                            "layout_height": "wrap_content",
                                            "text": "Daily Goal Master",
                                            "textSize": "12sp",
                                            "textStyle": "bold",
                                            "textColor": "@color/primary_text",
                                            "data_binding": "active_challenge.title"
                                        },
                                        {
                                            "type": "ProgressBar",
                                            "id": "@+id/challenge_bar",
                                            "style": "@style/Widget.ProgressBar.Horizontal",
                                            "layout_width": "match_parent",
                                            "layout_height": "6dp",
                                            "layout_marginTop": "4dp",
                                            "max": "100",
                                            "progress": "67",
                                            "data_binding": "active_challenge.progress",
                                            "format": "{value * 100:.0f}"
                                        }
                                    ]
                                },
                                {
                                    "type": "TextView",
                                    "id": "@+id/challenge_points",
                                    "layout_width": "wrap_content",
                                    "layout_height": "wrap_content",
                                    "layout_gravity": "center_vertical",
                                    "layout_marginLeft": "8dp",
                                    "text": "+50",
                                    "textSize": "14sp",
                                    "textStyle": "bold",
                                    "textColor": "@color/points_color",
                                    "data_binding": "active_challenge.reward_points",
                                    "format": "+{value}"
                                }
                            ]
                        }
                    ]
                }
            },
            
            # Click actions with multiple targets
            "click_actions": {
                "root": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://dashboard"
                },
                "@+id/challenge_card": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://challenges"
                },
                "@+id/main_ring": {
                    "type": "deep_link",
                    "intent_action": "android.intent.action.VIEW",
                    "data_uri": "ainutritionist://adherence"
                }
            }
        }
    
    def generate_widget_manifest_config(self) -> Dict[str, Any]:
        """Generate Android manifest configuration for widgets."""
        return {
            "receivers": [
                {
                    "name": f"{self.package_name}.widgets.SmallWidgetProvider",
                    "exported": "true",
                    "intent_filters": [
                        {
                            "action": "android.appwidget.action.APPWIDGET_UPDATE"
                        }
                    ],
                    "meta_data": [
                        {
                            "name": "android.appwidget.provider",
                            "resource": "@xml/small_widget_info"
                        }
                    ]
                },
                {
                    "name": f"{self.package_name}.widgets.MediumWidgetProvider",
                    "exported": "true",
                    "intent_filters": [
                        {
                            "action": "android.appwidget.action.APPWIDGET_UPDATE"
                        }
                    ],
                    "meta_data": [
                        {
                            "name": "android.appwidget.provider",
                            "resource": "@xml/medium_widget_info"
                        }
                    ]
                },
                {
                    "name": f"{self.package_name}.widgets.LargeWidgetProvider",
                    "exported": "true",
                    "intent_filters": [
                        {
                            "action": "android.appwidget.action.APPWIDGET_UPDATE"
                        }
                    ],
                    "meta_data": [
                        {
                            "name": "android.appwidget.provider",
                            "resource": "@xml/large_widget_info"
                        }
                    ]
                }
            ],
            
            "permissions": [
                "android.permission.INTERNET",
                "android.permission.ACCESS_NETWORK_STATE",
                "android.permission.BIND_APPWIDGET"
            ],
            
            "intent_filters": [
                {
                    "action": "android.intent.action.VIEW",
                    "category": [
                        "android.intent.category.DEFAULT",
                        "android.intent.category.BROWSABLE"
                    ],
                    "data": {
                        "scheme": self.deep_link_scheme
                    }
                }
            ]
        }


def generate_android_widget_bundle() -> Dict[str, Any]:
    """Generate complete Android widget bundle configuration."""
    config = AndroidWidgetConfiguration()
    
    return {
        "bundle_info": {
            "package_name": config.package_name,
            "widget_provider_version": "1.0",
            "min_sdk_version": 16,
            "target_sdk_version": 34,
            "supports_adaptive_icon": True
        },
        
        "api_configuration": {
            "base_url": "https://api.ainutritionist.com",
            "endpoint": config.api_endpoint,
            "authentication_type": "bearer_token",
            "cache_policy": "respect_etag",
            "timeout_millis": 10000,
            "retry_policy": {
                "max_attempts": 3,
                "backoff_multiplier": 1.5,
                "initial_interval_millis": 1000
            }
        },
        
        "widget_configurations": {
            "small": config.generate_small_widget_config(),
            "medium": config.generate_medium_widget_config(),
            "large": config.generate_large_widget_config()
        },
        
        "manifest_configuration": config.generate_widget_manifest_config(),
        
        "resources": {
            "colors": {
                "primary_text": "#333333",
                "secondary_text": "#666666",
                "divider": "#E0E0E0",
                "excellent": "#00C851",
                "good": "#39C0ED",
                "fair": "#FF8800",
                "poor": "#FF4444",
                "challenge_color": "#9C27B0",
                "points_color": "#FF6B35"
            },
            
            "drawables": {
                "widget_background": {
                    "type": "shape",
                    "shape": "rectangle",
                    "solid_color": "#FFFFFF",
                    "corner_radius": "12dp",
                    "stroke": {
                        "width": "1dp",
                        "color": "#E0E0E0"
                    }
                },
                "challenge_card_background": {
                    "type": "shape",
                    "shape": "rectangle",
                    "solid_color": "#F8F9FA",
                    "corner_radius": "8dp"
                }
            },
            
            "dimensions": {
                "widget_padding": "12dp",
                "text_margin": "4dp",
                "progress_height": "8dp",
                "ring_size": "48dp",
                "ring_size_large": "60dp"
            }
        },
        
        "localization": {
            "strings": {
                "en": {
                    "widget_name_small": "Nutrition Progress",
                    "widget_name_medium": "Nutrition Dashboard",
                    "widget_name_large": "Nutrition Dashboard Pro",
                    "loading_message": "Loading...",
                    "error_message": "Unable to update",
                    "streak_label": "Streak",
                    "level_label": "Level",
                    "challenge_label": "Challenge"
                },
                "es": {
                    "widget_name_small": "Progreso Nutricional",
                    "widget_name_medium": "Panel Nutricional",
                    "widget_name_large": "Panel Nutricional Pro",
                    "loading_message": "Cargando...",
                    "error_message": "No se puede actualizar",
                    "streak_label": "Racha",
                    "level_label": "Nivel",
                    "challenge_label": "Desafío"
                }
            }
        }
    }


# Save configuration to JSON file
if __name__ == "__main__":
    config = generate_android_widget_bundle()
    
    with open("android_widget_config.json", "w") as f:
        json.dump(config, f, indent=2, default=str)
    
    print("Android Widget configuration generated successfully!")
