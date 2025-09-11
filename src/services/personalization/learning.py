"""
Learning Algorithms Service

Implements machine learning algorithms for user preference learning,
recommendation improvement, and adaptive personalization.

Consolidates functionality from:
- machine_learning_service.py
- recommendation_engine_service.py
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
import numpy as np
from collections import defaultdict, Counter
import statistics

logger = logging.getLogger(__name__)


class AlgorithmType(Enum):
    """Types of learning algorithms."""
    COLLABORATIVE_FILTERING = "collaborative_filtering"
    CONTENT_BASED = "content_based"
    HYBRID = "hybrid"
    REINFORCEMENT_LEARNING = "reinforcement_learning"
    CLUSTERING = "clustering"
    CLASSIFICATION = "classification"


class RecommendationType(Enum):
    """Types of recommendations."""
    MEAL_PLAN = "meal_plan"
    RECIPE = "recipe"
    INGREDIENT = "ingredient"
    COOKING_METHOD = "cooking_method"
    CUISINE = "cuisine"
    NUTRITION_GOAL = "nutrition_goal"
    TIMING = "timing"


@dataclass
class LearningFeature:
    """Feature used in machine learning models."""
    name: str
    feature_type: str  # numerical, categorical, binary
    value: Any
    weight: float = 1.0
    importance: float = 0.5
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ModelPrediction:
    """Prediction result from ML model."""
    prediction_id: str
    model_type: AlgorithmType
    recommendation_type: RecommendationType
    predicted_value: Any
    confidence_score: float
    feature_contributions: Dict[str, float]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserProfile:
    """User profile for ML algorithms."""
    user_id: str
    features: Dict[str, LearningFeature]
    preferences_vector: List[float]
    similarity_scores: Dict[str, float]
    cluster_id: Optional[str]
    last_training: datetime
    model_version: str


@dataclass
class RecommendationResult:
    """Complete recommendation with explanations."""
    item_id: str
    item_type: RecommendationType
    score: float
    confidence: float
    explanation: str
    reasoning: List[str]
    similar_items: List[str]
    predicted_rating: float
    features_used: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class LearningAlgorithmsService:
    """
    Advanced machine learning service for personalized nutrition recommendations.
    
    Features:
    - Multiple ML algorithms (collaborative filtering, content-based, hybrid)
    - Real-time preference learning and model adaptation
    - Feature engineering from user interactions and preferences
    - Similarity computation and user clustering
    - Explainable AI for recommendation transparency
    - A/B testing framework for algorithm optimization
    """

    def __init__(self):
        self.user_profiles: Dict[str, UserProfile] = {}
        self.item_features: Dict[str, Dict[str, Any]] = {}
        self.interaction_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self.model_cache: Dict[str, Any] = {}
        self.similarity_cache: Dict[Tuple[str, str], float] = {}

    def learn_user_preferences(
        self,
        user_id: str,
        interactions: List[Dict[str, Any]],
        feedback_data: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Learn and update user preferences from interactions and feedback.
        
        Args:
            user_id: User identifier
            interactions: List of user interaction data
            feedback_data: Optional explicit feedback data
            
        Returns:
            Success status
        """
        try:
            # Extract features from interactions
            features = self._extract_user_features(interactions, feedback_data)
            
            # Update or create user profile
            if user_id in self.user_profiles:
                profile = self.user_profiles[user_id]
                profile.features.update(features)
                profile.last_training = datetime.utcnow()
            else:
                profile = UserProfile(
                    user_id=user_id,
                    features=features,
                    preferences_vector=self._create_preferences_vector(features),
                    similarity_scores={},
                    cluster_id=None,
                    last_training=datetime.utcnow(),
                    model_version="1.0"
                )
                self.user_profiles[user_id] = profile
            
            # Update interaction matrix for collaborative filtering
            self._update_interaction_matrix(user_id, interactions)
            
            # Recompute similarity scores
            self._compute_user_similarities(user_id)
            
            # Update cluster assignment
            self._update_user_cluster(user_id)
            
            logger.info(f"Updated preferences for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error learning user preferences: {e}")
            return False

    def generate_recommendations(
        self,
        user_id: str,
        recommendation_type: str,
        count: int = 10,
        algorithm: str = "hybrid",
        context: Optional[Dict[str, Any]] = None
    ) -> List[RecommendationResult]:
        """
        Generate personalized recommendations using specified algorithm.
        
        Args:
            user_id: User identifier
            recommendation_type: Type of recommendations
            count: Number of recommendations
            algorithm: Algorithm to use
            context: Additional context for recommendations
            
        Returns:
            List of personalized recommendations
        """
        try:
            rec_type = RecommendationType(recommendation_type)
            algo_type = AlgorithmType(algorithm)
            
            # Get user profile
            profile = self.user_profiles.get(user_id)
            if not profile:
                logger.warning(f"No profile found for user {user_id}, using default recommendations")
                return self._get_default_recommendations(rec_type, count)
            
            # Generate recommendations based on algorithm
            if algo_type == AlgorithmType.COLLABORATIVE_FILTERING:
                recommendations = self._collaborative_filtering_recommendations(
                    user_id, rec_type, count, context
                )
            elif algo_type == AlgorithmType.CONTENT_BASED:
                recommendations = self._content_based_recommendations(
                    user_id, rec_type, count, context
                )
            elif algo_type == AlgorithmType.HYBRID:
                recommendations = self._hybrid_recommendations(
                    user_id, rec_type, count, context
                )
            else:
                recommendations = self._get_default_recommendations(rec_type, count)
            
            # Apply post-processing filters
            recommendations = self._apply_recommendation_filters(
                user_id, recommendations, context
            )
            
            # Sort by score and limit count
            recommendations.sort(key=lambda x: x.score, reverse=True)
            final_recommendations = recommendations[:count]
            
            logger.info(f"Generated {len(final_recommendations)} recommendations for {user_id}")
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []

    def compute_item_similarity(
        self,
        item1_id: str,
        item2_id: str,
        similarity_type: str = "content"
    ) -> float:
        """
        Compute similarity between two items.
        
        Args:
            item1_id: First item identifier
            item2_id: Second item identifier
            similarity_type: Type of similarity computation
            
        Returns:
            Similarity score (0.0-1.0)
        """
        try:
            cache_key = (item1_id, item2_id, similarity_type)
            if cache_key in self.similarity_cache:
                return self.similarity_cache[cache_key]
            
            # Get item features
            features1 = self.item_features.get(item1_id, {})
            features2 = self.item_features.get(item2_id, {})
            
            if not features1 or not features2:
                return 0.0
            
            if similarity_type == "content":
                similarity = self._compute_content_similarity(features1, features2)
            elif similarity_type == "collaborative":
                similarity = self._compute_collaborative_similarity(item1_id, item2_id)
            else:
                similarity = 0.0
            
            # Cache result
            self.similarity_cache[cache_key] = similarity
            
            return similarity
            
        except Exception as e:
            logger.error(f"Error computing item similarity: {e}")
            return 0.0

    def predict_user_rating(
        self,
        user_id: str,
        item_id: str,
        features: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, float]:
        """
        Predict user rating for an item.
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            features: Optional item features
            
        Returns:
            Tuple of (predicted_rating, confidence)
        """
        try:
            profile = self.user_profiles.get(user_id)
            if not profile:
                return 3.0, 0.1  # Default neutral rating with low confidence
            
            # Get or create item features
            if features:
                self.item_features[item_id] = features
            item_features = self.item_features.get(item_id, {})
            
            if not item_features:
                return 3.0, 0.2
            
            # Compute prediction using multiple methods
            predictions = []
            confidences = []
            
            # Content-based prediction
            content_pred, content_conf = self._predict_content_based_rating(
                profile, item_features
            )
            predictions.append(content_pred)
            confidences.append(content_conf)
            
            # Collaborative filtering prediction
            if len(self.interaction_matrix) > 1:
                collab_pred, collab_conf = self._predict_collaborative_rating(
                    user_id, item_id
                )
                predictions.append(collab_pred)
                confidences.append(collab_conf)
            
            # Weighted average
            if predictions:
                weights = np.array(confidences)
                if weights.sum() > 0:
                    weights = weights / weights.sum()
                    final_prediction = np.average(predictions, weights=weights)
                    final_confidence = np.mean(confidences)
                else:
                    final_prediction = np.mean(predictions)
                    final_confidence = 0.3
            else:
                final_prediction = 3.0
                final_confidence = 0.1
            
            # Ensure rating is in valid range (1-5)
            final_prediction = max(1.0, min(5.0, final_prediction))
            
            return final_prediction, final_confidence
            
        except Exception as e:
            logger.error(f"Error predicting user rating: {e}")
            return 3.0, 0.1

    def cluster_users(self, num_clusters: int = 5) -> Dict[str, List[str]]:
        """
        Cluster users based on preferences and behavior.
        
        Args:
            num_clusters: Number of clusters to create
            
        Returns:
            Dictionary mapping cluster_id to list of user_ids
        """
        try:
            if len(self.user_profiles) < num_clusters:
                # Not enough users for clustering
                return {"default": list(self.user_profiles.keys())}
            
            # Extract feature vectors for clustering
            user_vectors = {}
            for user_id, profile in self.user_profiles.items():
                user_vectors[user_id] = profile.preferences_vector
            
            # Simple k-means clustering (in production, use proper ML library)
            clusters = self._simple_kmeans_clustering(user_vectors, num_clusters)
            
            # Update cluster assignments in user profiles
            for cluster_id, user_ids in clusters.items():
                for user_id in user_ids:
                    if user_id in self.user_profiles:
                        self.user_profiles[user_id].cluster_id = cluster_id
            
            logger.info(f"Clustered {len(self.user_profiles)} users into {len(clusters)} clusters")
            return clusters
            
        except Exception as e:
            logger.error(f"Error clustering users: {e}")
            return {"default": list(self.user_profiles.keys())}

    def explain_recommendation(
        self,
        user_id: str,
        item_id: str,
        recommendation: RecommendationResult
    ) -> Dict[str, Any]:
        """
        Provide explanation for why an item was recommended.
        
        Args:
            user_id: User identifier
            item_id: Item identifier
            recommendation: Recommendation result
            
        Returns:
            Detailed explanation
        """
        try:
            explanation = {
                "recommendation_id": recommendation.item_id,
                "score": recommendation.score,
                "confidence": recommendation.confidence,
                "primary_reasons": recommendation.reasoning,
                "feature_contributions": {},
                "similar_liked_items": recommendation.similar_items,
                "user_preference_match": {},
                "explanation_text": recommendation.explanation
            }
            
            # Add feature contribution details
            profile = self.user_profiles.get(user_id)
            if profile:
                for feature_name, contribution in recommendation.features_used:
                    if feature_name in profile.features:
                        feature = profile.features[feature_name]
                        explanation["feature_contributions"][feature_name] = {
                            "value": feature.value,
                            "weight": feature.weight,
                            "importance": feature.importance,
                            "contribution": contribution
                        }
            
            # Add preference matching details
            item_features = self.item_features.get(item_id, {})
            if profile and item_features:
                explanation["user_preference_match"] = self._compute_preference_match_details(
                    profile, item_features
                )
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error explaining recommendation: {e}")
            return {"error": str(e)}

    def _extract_user_features(
        self,
        interactions: List[Dict[str, Any]],
        feedback_data: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, LearningFeature]:
        """Extract machine learning features from user data."""
        features = {}
        
        # Interaction frequency features
        interaction_counts = Counter(i.get('type') for i in interactions)
        for interaction_type, count in interaction_counts.items():
            features[f"interaction_{interaction_type}_frequency"] = LearningFeature(
                name=f"interaction_{interaction_type}_frequency",
                feature_type="numerical",
                value=count,
                weight=1.0,
                importance=0.6
            )
        
        # Time-based features
        if interactions:
            timestamps = [datetime.fromisoformat(i['timestamp']) for i in interactions if 'timestamp' in i]
            if timestamps:
                hours = [ts.hour for ts in timestamps]
                avg_hour = statistics.mean(hours)
                features["avg_interaction_hour"] = LearningFeature(
                    name="avg_interaction_hour",
                    feature_type="numerical",
                    value=avg_hour,
                    weight=0.8,
                    importance=0.4
                )
        
        # Feedback features
        if feedback_data:
            ratings = [f.get('rating', 3) for f in feedback_data if 'rating' in f]
            if ratings:
                avg_rating = statistics.mean(ratings)
                features["avg_feedback_rating"] = LearningFeature(
                    name="avg_feedback_rating",
                    feature_type="numerical",
                    value=avg_rating,
                    weight=1.2,
                    importance=0.9
                )
        
        return features

    def _create_preferences_vector(self, features: Dict[str, LearningFeature]) -> List[float]:
        """Create numerical preference vector from features."""
        vector = []
        
        # Standard feature order for consistency
        feature_names = [
            "avg_feedback_rating",
            "interaction_meal_plan_frequency",
            "interaction_recipe_frequency",
            "avg_interaction_hour",
            "interaction_feedback_frequency"
        ]
        
        for name in feature_names:
            if name in features:
                value = features[name].value
                if isinstance(value, (int, float)):
                    vector.append(float(value))
                else:
                    vector.append(0.0)
            else:
                vector.append(0.0)
        
        # Pad or truncate to fixed length (20)
        while len(vector) < 20:
            vector.append(0.0)
        return vector[:20]

    def _update_interaction_matrix(self, user_id: str, interactions: List[Dict[str, Any]]) -> None:
        """Update interaction matrix for collaborative filtering."""
        for interaction in interactions:
            item_id = interaction.get('item_id')
            rating = interaction.get('rating', 1.0)
            
            if item_id:
                self.interaction_matrix[user_id][item_id] = rating

    def _compute_user_similarities(self, user_id: str) -> None:
        """Compute similarities with other users."""
        if user_id not in self.user_profiles:
            return
        
        user_vector = self.user_profiles[user_id].preferences_vector
        similarities = {}
        
        for other_user_id, other_profile in self.user_profiles.items():
            if other_user_id != user_id:
                similarity = self._cosine_similarity(user_vector, other_profile.preferences_vector)
                similarities[other_user_id] = similarity
        
        self.user_profiles[user_id].similarity_scores = similarities

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0.0 or magnitude2 == 0.0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)

    def _update_user_cluster(self, user_id: str) -> None:
        """Update user cluster assignment."""
        # Simple cluster assignment based on highest similarity
        if user_id not in self.user_profiles:
            return
        
        similarities = self.user_profiles[user_id].similarity_scores
        if similarities:
            most_similar_user = max(similarities.items(), key=lambda x: x[1])[0]
            most_similar_cluster = self.user_profiles[most_similar_user].cluster_id
            if most_similar_cluster:
                self.user_profiles[user_id].cluster_id = most_similar_cluster

    def _collaborative_filtering_recommendations(
        self,
        user_id: str,
        rec_type: RecommendationType,
        count: int,
        context: Optional[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Generate recommendations using collaborative filtering."""
        recommendations = []
        
        # Find similar users
        profile = self.user_profiles[user_id]
        similar_users = sorted(
            profile.similarity_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]  # Top 10 similar users
        
        # Get items liked by similar users
        item_scores = defaultdict(float)
        for similar_user_id, similarity in similar_users:
            if similar_user_id in self.interaction_matrix:
                for item_id, rating in self.interaction_matrix[similar_user_id].items():
                    if item_id not in self.interaction_matrix[user_id]:  # User hasn't seen this item
                        item_scores[item_id] += similarity * rating
        
        # Convert to recommendations
        for item_id, score in sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:count]:
            recommendations.append(RecommendationResult(
                item_id=item_id,
                item_type=rec_type,
                score=score,
                confidence=0.7,
                explanation=f"Users similar to you liked this {rec_type.value}",
                reasoning=["collaborative_filtering", "similar_users"],
                similar_items=[],
                predicted_rating=min(5.0, max(1.0, score)),
                features_used=["user_similarity"]
            ))
        
        return recommendations

    def _content_based_recommendations(
        self,
        user_id: str,
        rec_type: RecommendationType,
        count: int,
        context: Optional[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Generate recommendations using content-based filtering."""
        recommendations = []
        profile = self.user_profiles[user_id]
        
        # Score items based on feature similarity
        for item_id, item_features in self.item_features.items():
            if item_id not in self.interaction_matrix.get(user_id, {}):
                score = self._compute_content_score(profile, item_features)
                if score > 0.3:  # Minimum threshold
                    recommendations.append(RecommendationResult(
                        item_id=item_id,
                        item_type=rec_type,
                        score=score,
                        confidence=0.6,
                        explanation=f"Matches your preferences for {rec_type.value}",
                        reasoning=["content_based", "feature_matching"],
                        similar_items=[],
                        predicted_rating=score * 5.0,
                        features_used=list(item_features.keys())[:3]
                    ))
        
        return recommendations

    def _hybrid_recommendations(
        self,
        user_id: str,
        rec_type: RecommendationType,
        count: int,
        context: Optional[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Generate recommendations using hybrid approach."""
        # Get recommendations from both methods
        collab_recs = self._collaborative_filtering_recommendations(user_id, rec_type, count * 2, context)
        content_recs = self._content_based_recommendations(user_id, rec_type, count * 2, context)
        
        # Combine and reweight
        combined_scores = defaultdict(float)
        all_recs = {}
        
        # Weight collaborative filtering recommendations
        for rec in collab_recs:
            combined_scores[rec.item_id] += rec.score * 0.6
            all_recs[rec.item_id] = rec
        
        # Weight content-based recommendations
        for rec in content_recs:
            combined_scores[rec.item_id] += rec.score * 0.4
            if rec.item_id not in all_recs:
                all_recs[rec.item_id] = rec
        
        # Create final recommendations
        final_recommendations = []
        for item_id, combined_score in sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:count]:
            rec = all_recs[item_id]
            rec.score = combined_score
            rec.confidence = 0.8  # Higher confidence for hybrid
            rec.explanation = f"Recommended based on similar users and your preferences"
            rec.reasoning = ["hybrid", "collaborative_filtering", "content_based"]
            final_recommendations.append(rec)
        
        return final_recommendations

    def _get_default_recommendations(self, rec_type: RecommendationType, count: int) -> List[RecommendationResult]:
        """Generate default recommendations for new users."""
        defaults = {
            RecommendationType.MEAL_PLAN: ["healthy_breakfast", "balanced_lunch", "protein_dinner"],
            RecommendationType.RECIPE: ["chicken_salad", "vegetable_stir_fry", "quinoa_bowl"],
            RecommendationType.CUISINE: ["mediterranean", "asian", "american"]
        }
        
        default_items = defaults.get(rec_type, ["default_item"])
        recommendations = []
        
        for i, item_id in enumerate(default_items[:count]):
            recommendations.append(RecommendationResult(
                item_id=item_id,
                item_type=rec_type,
                score=0.5 - (i * 0.05),  # Decreasing scores
                confidence=0.3,
                explanation=f"Popular {rec_type.value} for new users",
                reasoning=["default", "popularity"],
                similar_items=[],
                predicted_rating=3.5,
                features_used=[]
            ))
        
        return recommendations

    def _apply_recommendation_filters(
        self,
        user_id: str,
        recommendations: List[RecommendationResult],
        context: Optional[Dict[str, Any]]
    ) -> List[RecommendationResult]:
        """Apply post-processing filters to recommendations."""
        # Remove duplicates
        seen_items = set()
        filtered = []
        
        for rec in recommendations:
            if rec.item_id not in seen_items:
                seen_items.add(rec.item_id)
                filtered.append(rec)
        
        # Apply context filters if provided
        if context:
            # Filter by dietary restrictions
            if 'dietary_restrictions' in context:
                restrictions = context['dietary_restrictions']
                filtered = [r for r in filtered if self._meets_dietary_restrictions(r.item_id, restrictions)]
            
            # Filter by time of day
            if 'time_of_day' in context:
                time_filter = context['time_of_day']
                filtered = [r for r in filtered if self._appropriate_for_time(r.item_id, time_filter)]
        
        return filtered

    def _compute_content_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Compute content-based similarity between items."""
        common_features = set(features1.keys()) & set(features2.keys())
        if not common_features:
            return 0.0
        
        similarities = []
        for feature in common_features:
            val1, val2 = features1[feature], features2[feature]
            
            if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                # Numerical similarity
                max_val = max(abs(val1), abs(val2), 1)
                sim = 1.0 - abs(val1 - val2) / max_val
                similarities.append(sim)
            elif isinstance(val1, str) and isinstance(val2, str):
                # String similarity (exact match)
                similarities.append(1.0 if val1.lower() == val2.lower() else 0.0)
        
        return statistics.mean(similarities) if similarities else 0.0

    def _compute_collaborative_similarity(self, item1_id: str, item2_id: str) -> float:
        """Compute collaborative filtering similarity between items."""
        # Find users who rated both items
        common_users = []
        for user_id, user_ratings in self.interaction_matrix.items():
            if item1_id in user_ratings and item2_id in user_ratings:
                common_users.append((user_ratings[item1_id], user_ratings[item2_id]))
        
        if len(common_users) < 2:
            return 0.0
        
        # Compute correlation
        ratings1, ratings2 = zip(*common_users)
        try:
            correlation = statistics.correlation(ratings1, ratings2)
            return max(0.0, correlation)  # Only positive correlations
        except statistics.StatisticsError:
            return 0.0

    def _predict_content_based_rating(
        self,
        profile: UserProfile,
        item_features: Dict[str, Any]
    ) -> Tuple[float, float]:
        """Predict rating using content-based approach."""
        score = self._compute_content_score(profile, item_features)
        rating = 1.0 + (score * 4.0)  # Scale to 1-5
        confidence = 0.6 if score > 0.5 else 0.3
        return rating, confidence

    def _predict_collaborative_rating(self, user_id: str, item_id: str) -> Tuple[float, float]:
        """Predict rating using collaborative filtering."""
        if user_id not in self.user_profiles:
            return 3.0, 0.1
        
        profile = self.user_profiles[user_id]
        similar_users = profile.similarity_scores
        
        if not similar_users:
            return 3.0, 0.2
        
        # Weighted average of similar users' ratings
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for similar_user_id, similarity in similar_users.items():
            if similar_user_id in self.interaction_matrix:
                user_ratings = self.interaction_matrix[similar_user_id]
                if item_id in user_ratings:
                    weighted_sum += similarity * user_ratings[item_id]
                    weight_sum += similarity
        
        if weight_sum > 0:
            predicted_rating = weighted_sum / weight_sum
            confidence = min(0.8, weight_sum / len(similar_users))
        else:
            predicted_rating = 3.0
            confidence = 0.1
        
        return predicted_rating, confidence

    def _compute_content_score(self, profile: UserProfile, item_features: Dict[str, Any]) -> float:
        """Compute content-based similarity score."""
        if not profile.features or not item_features:
            return 0.0
        
        scores = []
        
        # Compare relevant features
        for feature_name, feature in profile.features.items():
            if feature_name.endswith('_preference') and feature_name.replace('_preference', '') in item_features:
                item_value = item_features[feature_name.replace('_preference', '')]
                user_pref = feature.value
                
                if isinstance(user_pref, (int, float)) and isinstance(item_value, (int, float)):
                    # Numerical comparison
                    normalized_diff = abs(user_pref - item_value) / max(user_pref, item_value, 1)
                    score = (1.0 - normalized_diff) * feature.weight
                    scores.append(score)
        
        return statistics.mean(scores) if scores else 0.3

    def _simple_kmeans_clustering(self, user_vectors: Dict[str, List[float]], k: int) -> Dict[str, List[str]]:
        """Simple k-means clustering implementation."""
        if len(user_vectors) < k:
            return {"cluster_0": list(user_vectors.keys())}
        
        # Initialize centroids randomly
        user_ids = list(user_vectors.keys())
        centroids = {}
        for i in range(k):
            centroids[f"cluster_{i}"] = user_vectors[user_ids[i % len(user_ids)]].copy()
        
        # Assign users to clusters (simplified)
        clusters = {cluster_id: [] for cluster_id in centroids.keys()}
        
        for user_id, vector in user_vectors.items():
            best_cluster = min(
                centroids.keys(),
                key=lambda c: sum((a - b) ** 2 for a, b in zip(vector, centroids[c]))
            )
            clusters[best_cluster].append(user_id)
        
        return clusters

    def _compute_preference_match_details(
        self,
        profile: UserProfile,
        item_features: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute detailed preference matching information."""
        matches = {}
        
        for feature_name, feature in profile.features.items():
            if feature_name.endswith('_preference'):
                item_attr = feature_name.replace('_preference', '')
                if item_attr in item_features:
                    matches[feature_name] = {
                        "user_preference": feature.value,
                        "item_value": item_features[item_attr],
                        "match_strength": self._compute_match_strength(
                            feature.value, item_features[item_attr]
                        )
                    }
        
        return matches

    def _compute_match_strength(self, user_pref: Any, item_value: Any) -> float:
        """Compute match strength between user preference and item value."""
        if isinstance(user_pref, (int, float)) and isinstance(item_value, (int, float)):
            max_val = max(abs(user_pref), abs(item_value), 1)
            return 1.0 - abs(user_pref - item_value) / max_val
        elif isinstance(user_pref, str) and isinstance(item_value, str):
            return 1.0 if user_pref.lower() == item_value.lower() else 0.0
        else:
            return 0.5

    def _meets_dietary_restrictions(self, item_id: str, restrictions: List[str]) -> bool:
        """Check if item meets dietary restrictions."""
        # Placeholder implementation
        return True

    def _appropriate_for_time(self, item_id: str, time_of_day: str) -> bool:
        """Check if item is appropriate for time of day."""
        # Placeholder implementation
        return True
