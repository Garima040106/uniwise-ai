from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Avg, Q
from datetime import timedelta
from analytics.models import StudySession, CognitiveLoadSnapshot
from quizzes.models import Question


class CognitiveLoadCalculator:
    """
    Calculates cognitive load based on multiple signals:
    - Time of day (circadian rhythm)
    - Day of week
    - Session duration
    - Recent quiz performance
    - Frustration indicators
    """

    # Circadian rhythm attention capacity by hour (0-23)
    # Based on typical cognitive performance patterns
    ATTENTION_CURVE = {
        6: 0.4,   # Early morning
        7: 0.6,
        8: 0.85,
        9: 1.0,   # Morning peak
        10: 1.0,
        11: 1.0,
        12: 0.9,  # Noon
        13: 0.6,  # Post-lunch dip begins
        14: 0.5,
        15: 0.55, # Afternoon low
        16: 0.65,
        17: 0.7,  # Afternoon recovery
        18: 0.8,
        19: 0.75,
        20: 0.65,
        21: 0.5,  # Evening decline
        22: 0.35,
        23: 0.25, # Late night
        0: 0.2,   # Midnight and beyond
        1: 0.15,
        2: 0.1,
        3: 0.1,
        4: 0.15,
        5: 0.2,
    }

    # How day of week affects cognitive capacity (Monday=1.0, Sunday=0.7)
    DAY_OF_WEEK_MULTIPLIERS = {
        0: 0.9,   # Monday - slight fatigue from weekend
        1: 1.0,   # Tuesday - peak week
        2: 1.0,   # Wednesday - peak week
        3: 0.95,  # Thursday - slight decline
        4: 0.85,  # Friday - end of week fatigue
        5: 0.75,  # Saturday - weekend, less structured
        6: 0.70,  # Sunday - anticipatory fatigue
    }

    def __init__(self, user_id):
        """Initialize calculator for a specific user."""
        self.user_id = user_id
        self.user = None
        self.now = timezone.now()
        self.signals = {}

    def calculate(self):
        """
        Main calculation method.
        
        Returns:
            dict with keys:
                - cognitive_load (0.0-1.0)
                - signals (dict of individual signal values)
                - recommendation (deep_learning/review_mode/break_required)
                - time_of_day (hour)
                - day_of_week (0-6)
        """
        try:
            self.user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            return {
                "error": f"User {self.user_id} not found",
                "cognitive_load": 0.5,
                "recommendation": "break_required",
            }

        # Collect all signals
        self._collect_signals()

        # Compute overall load
        load = self._compute_load()

        # Get recommendation
        recommendation = self._get_recommendation(load)

        # Save snapshot
        self._save_snapshot(load, recommendation)

        return {
            "cognitive_load": round(load, 3),
            "signals": self.signals,
            "recommendation": recommendation,
            "time_of_day": self.now.hour,
            "day_of_week": self.now.weekday(),
        }

    def _collect_signals(self):
        """
        Collect cognitive load signals from various sources.
        Populates self.signals dict.
        """
        # 1. Circadian rhythm signal
        hour = self.now.hour
        circadian_load = 1.0 - self.ATTENTION_CURVE.get(hour, 0.5)
        self.signals["circadian_load"] = round(circadian_load, 3)

        # 2. Day of week signal
        day_of_week = self.now.weekday()
        day_multiplier = self.DAY_OF_WEEK_MULTIPLIERS.get(day_of_week, 0.8)
        day_of_week_load = 1.0 - day_multiplier
        self.signals["day_of_week_load"] = round(day_of_week_load, 3)

        # 3. Session duration signal
        session_duration = self._get_session_duration()
        self.signals["session_duration_minutes"] = session_duration
        # Load increases with longer sessions (diminishing returns)
        if session_duration > 0:
            session_load = min(0.8, session_duration / 120.0)  # 120 min = 0.8 load
        else:
            session_load = 0.0
        self.signals["session_load"] = round(session_load, 3)

        # 4. Recent quiz performance signal
        quiz_avg = self._get_recent_quiz_score()
        self.signals["recent_quiz_avg"] = round(quiz_avg, 3) if quiz_avg else None
        # Lower scores = higher load (struggling more)
        if quiz_avg is not None:
            quiz_load = 1.0 - (quiz_avg / 100.0)
            quiz_load = max(0.0, min(0.7, quiz_load))  # Cap at 0.7
        else:
            quiz_load = 0.0
        self.signals["quiz_load"] = round(quiz_load, 3)

        # 5. Frustration signal
        frustration = self._detect_frustration()
        self.signals["frustration_score"] = round(frustration, 3)

    def _compute_load(self):
        """
        Combines signals into overall cognitive load (0.0 to 1.0).
        Uses weighted average of signals.
        """
        weights = {
            "circadian_load": 0.25,
            "day_of_week_load": 0.10,
            "session_load": 0.25,
            "quiz_load": 0.20,
            "frustration_score": 0.20,
        }

        total_load = 0.0
        total_weight = 0.0

        for signal_name, weight in weights.items():
            if signal_name in self.signals:
                value = self.signals[signal_name]
                if value is not None:
                    total_load += value * weight
                    total_weight += weight

        if total_weight == 0:
            return 0.5  # Default neutral load

        final_load = total_load / total_weight
        return max(0.0, min(1.0, final_load))  # Clamp to [0, 1]

    def _get_session_duration(self):
        """
        Get current study session duration in minutes.
        Queries the most recent ongoing StudySession for the user.
        """
        try:
            recent_session = StudySession.objects.filter(
                user=self.user,
                ended_at__isnull=True,  # Ongoing session
            ).order_by("-started_at").first()

            if recent_session:
                duration = (self.now - recent_session.started_at).total_seconds() / 60
                return max(0, int(duration))
            return 0
        except Exception:
            return 0

    def _get_recent_quiz_score(self):
        """
        Get average score from recent quizzes (last 7 days).
        Returns average as percentage (0-100), or None if no quizzes.
        """
        try:
            seven_days_ago = self.now - timedelta(days=7)

            # Query questions from quizzes taken by this user in last 7 days
            avg_score = Question.objects.filter(
                quiz__created_by=self.user,
                quiz__created_at__gte=seven_days_ago,
            ).aggregate(
                avg_correct=Avg(
                    Q(correct_answer__isnull=False).then(100),
                    default=0,
                )
            )

            score = avg_score.get("avg_correct")
            return float(score) if score else None
        except Exception:
            return None

    def _detect_frustration(self):
        """
        Detect frustration signals:
        - Repeated questions (asking same question multiple times)
        - Declining quiz scores
        - Long sessions without breaks
        
        Returns frustration score (0.0-1.0).
        """
        frustration = 0.0

        try:
            # Signal 1: Check for repeated questions in recent AIRequests
            from ai_engine.models import AIRequest

            one_hour_ago = self.now - timedelta(hours=1)
            recent_requests = AIRequest.objects.filter(
                requested_by=self.user,
                created_at__gte=one_hour_ago,
                request_type="ask",
            ).values_list("prompt", flat=True)

            if recent_requests.count() > 0:
                prompts = list(recent_requests)
                # Check for similar prompts (simple check: identical)
                if len(prompts) != len(set(prompts)):
                    frustration += 0.3

            # Signal 2: Declining performance (last 3 quizzes)
            try:
                last_three_scores = Question.objects.filter(
                    quiz__created_by=self.user,
                ).order_by("-quiz__created_at")[:30]  # Get ~last 3 quizzes

                if last_three_scores.count() >= 9:
                    scores = list(
                        Question.objects.filter(
                            quiz__created_by=self.user,
                        ).order_by("-quiz__created_at").values_list(
                            "question_text", flat=True
                        )[:9]
                    )
                    # Simplified check: if no recent correct answers
                    correct_count = sum(
                        1 for s in scores if s
                    )
                    if correct_count < 3:  # Less than 33% correct
                        frustration += 0.25
            except Exception:
                pass

            # Signal 3: Long session without a break
            session_duration = self._get_session_duration()
            if session_duration > 120:  # More than 2 hours
                frustration += min(0.2, (session_duration - 120) / 300)

        except Exception:
            pass

        return min(1.0, frustration)  # Cap at 1.0

    def _get_recommendation(self, cognitive_load):
        """
        Return learning mode recommendation based on cognitive load.
        
        Args:
            cognitive_load: float between 0.0 and 1.0
            
        Returns:
            str: one of 'deep_learning', 'review_mode', 'break_required'
        """
        frustration = self.signals.get("frustration_score", 0.0)
        session_duration = self.signals.get("session_duration_minutes", 0)

        # If high frustration or very high load, force break
        if frustration > 0.6 or cognitive_load > 0.85:
            return "break_required"

        # If session is very long, recommend break
        if session_duration > 150:  # > 2.5 hours
            return "break_required"

        # If load is high, recommend review mode
        if cognitive_load > 0.65:
            return "review_mode"

        # Otherwise, deep learning mode is okay
        return "deep_learning"

    def _save_snapshot(self, cognitive_load, recommendation):
        """
        Save cognitive load snapshot to database.
        
        Args:
            cognitive_load: float (0.0-1.0)
            recommendation: str
        """
        try:
            hour = self.now.hour
            day_of_week = self.now.weekday()
            session_duration = self.signals.get("session_duration_minutes", 0)
            recent_quiz_avg = self.signals.get("recent_quiz_avg")
            frustration_score = self.signals.get("frustration_score", 0.0)

            CognitiveLoadSnapshot.objects.create(
                user=self.user,
                cognitive_load=cognitive_load,
                time_of_day=hour,
                day_of_week=day_of_week,
                session_duration_minutes=session_duration,
                recent_quiz_avg=recent_quiz_avg,
                frustration_score=frustration_score,
                recommended_mode=recommendation,
            )
        except Exception as e:
            # Silently fail - don't break the calculation if saving fails
            pass
