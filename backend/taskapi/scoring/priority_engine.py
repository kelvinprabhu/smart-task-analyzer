import datetime
from collections import defaultdict
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from math import log1p
import datetime
import holidays   # pip install holidays
from collections import defaultdict


def working_days_between(d1, d2):
    days = 0
    for i in range((d2 - d1).days + 1):
        day = d1 + datetime.timedelta(days=i)
        if day.weekday() < 5 and day not in holidays.country_holidays("IN"):
            days += 1
    return days - 1




class PriorityEngine:
    """
    PriorityEngine V4 – Stable Graph-Aware Scheduler
    ------------------------------------------------
    Includes:
    - Cycle detection
    - Direct dependency boost
    - Graph centrality propagation
    - Depth-based discount (critical fix)
    - Balanced urgency/importance
    - Safe defaults for bad data
    """

    # CONFIGURABLE WEIGHTS
    U_MAX = 10 # days for max urgency
    W_URGENCY = 0.7 # weight for urgency
    W_IMPORTANCE = 0.8 # weight for importance
    ALPHA = 0.6 # weight for direct dependency boost
    LAMBDA = 0.35 # weight for centrality propagation
    CENTRALITY_ITER = 12 # number of iterations for centrality calculation

    def __init__(self, tasks):
        self.tasks = tasks
        self.today = datetime.date.today()

    
    #  EFFORT SCORE FOR API RESPONSE
    
    def effort_score(self, task):
        hours = getattr(task, "estimated_hours", None)
        if hours is None:
            hours = getattr(task, "effort", None)
        if hours is None or hours <= 0:
            return 0.0
        return float(self.effort_factor(task))

    
    #  DIRECT DEPENDENCY COUNT FOR API RESPONSE
    
    def dependency_score(self, task):
        count = 0
        for t in self.tasks:
            if task in t.dependencies.all():
                count += 1
        return self.direct_dependency_factor(task, {task.id: count})

    
    #  CYCLE DETECTION
    
    def detect_cycles(self):
        visited = set()
        stack = set()
        cyclic = set()

        def dfs(task):
            if task.id in stack:
                cyclic.add(task.id)
                return True
            if task.id in visited:
                return False

            visited.add(task.id)
            stack.add(task.id)

            for dep in task.dependencies.all():
                if dfs(dep):
                    cyclic.add(task.id)

            stack.remove(task.id)
            return False

        for t in self.tasks:
            if t.id not in visited:
                dfs(t)

        return list(cyclic)

    
    #  URGENCY, IMPORTANCE, EFFORT
    
    def urgency_score(self, task):
        if not task.due_date:
            return 0.5

        delta = working_days_between(self.today, task.due_date)

        if delta < 0:
            overdue = abs(delta)
            return 2.0 + min(overdue / 7.0, 1.0)

        clamped = max(0, self.U_MAX - delta)
        return 1.0 + (clamped / self.U_MAX)

    def importance_score(self, task):
        imp = getattr(task, "importance", 5)
        if imp is None:
            imp = 5
        imp = max(1, min(10, imp))
        return imp / 10.0

    def effort_factor(self, task):
        hours = getattr(task, "estimated_hours", None)
        if hours is None:
            hours = getattr(task, "effort", 2.0)
        if hours is None or hours <= 0:
            hours = 1.0
        hours = max(hours, 0.1)
        return min(1.0 / hours, 10.0)

    
    #  DIRECT DEPENDENCY BOOST
    
    def direct_dependency_factor(self, task, dependents_count):
        c = dependents_count.get(task.id, 0)
        return 1.0 + (self.ALPHA * c)

    
    #  DEPTH CALCULATION (CRITICAL FIX)
    # ------------------------------------------------------------
    #  Depth = how many tasks are above this one in chain
    #  More depth => bigger discount => lower priority
    
    def compute_depth(self, task, memo):
        if task.id in memo:
            return memo[task.id]

        deps = task.dependencies.all()
        if not deps:
            memo[task.id] = 0
            return 0

        depth = 1 + max(self.compute_depth(dep, memo) for dep in deps)
        memo[task.id] = depth
        return depth

    
    #  GRAPH CENTRALITY USING KATZ PROPAGATION
    
    def compute_centrality(self, dependents):
        if not self.tasks:
            return {}

        beta = 1.0
        C = {t.id: beta for t in self.tasks}

        for _ in range(self.CENTRALITY_ITER):
            new_C = {}
            for t in self.tasks:
                score = beta
                for child in dependents.get(t.id, []):
                    score += self.LAMBDA * C.get(child, beta)
                new_C[t.id] = score
            C = new_C

        max_val = max(C.values())
        for tid in C:
            C[tid] /= max_val

        return C

    
    #  FINAL SCORE CALCULATION (NOW WITH DEPTH DISCOUNT)
    
    def calculate_score(self, task, dependents_count, centrality_map, depth_map):
        urgency = self.urgency_score(task)
        importance = self.importance_score(task)
        effort = self.effort_factor(task)

        value = urgency * self.W_URGENCY + importance * self.W_IMPORTANCE
        dependency_factor = self.direct_dependency_factor(task, dependents_count)
        centrality_factor = centrality_map.get(task.id, 1.0)

        # ---- CRITICAL DISCOUNT ----
        depth = depth_map.get(task.id, 0)
        discount = 1.0 / (1.0 + depth)

        final_score = (
            value *
            dependency_factor *
            centrality_factor *
            effort *
            discount
        )
        # Normalize final score
        # max_score = max(final_score, 1.0)
        final_score = log1p(final_score)
        # range the score to 0-100
        final_score = (final_score / log1p(1 + 1000)) * 100

        return float(final_score)

    
    #  RUN ENGINE
    
    def run(self):
        if not self.tasks:
            return [], []

        # Detect cycles
        cyclic = self.detect_cycles()
        valid = [t for t in self.tasks if t.id not in cyclic]

        if not valid:
            return [], cyclic

        # Build dependency graph
        dependents_count = defaultdict(int)
        adjacency = defaultdict(list)

        for t in valid:
            for dep in t.dependencies.all():
                if dep.id not in cyclic:
                    dependents_count[dep.id] += 1
                    adjacency[dep.id].append(t.id)

        # Depth computation
        depth_map = {}
        for t in valid:
            depth_map[t.id] = self.compute_depth(t, depth_map)

        # Centrality
        centrality_map = self.compute_centrality(adjacency)

        # Scoring
        scored = []
        for task in valid:
            score = self.calculate_score(task, dependents_count, centrality_map, depth_map)
            scored.append({"task": task, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored, cyclic



# VALIDATION UTILITIES

class TaskValidator:
    """Validates and sanitizes task input data."""
    
    @staticmethod
    def validate_task_data(data):
        """
        Validates a single task dict. Returns (is_valid, cleaned_data, errors).
        """
        errors = []
        cleaned = {}
        
        # Required: title
        title = data.get("title", "").strip()
        if not title:
            errors.append("Title is required and cannot be empty")
            return False, cleaned, errors
        else:
            cleaned["title"] = title
        
        # Optional: due_date (REJECT past dates)
        due_date = data.get("due_date")
        if due_date:
            try:
                if isinstance(due_date, str):
                    parsed = datetime.datetime.strptime(due_date, "%Y-%m-%d").date()
                else:
                    parsed = due_date
                
                # Check if date is in the past
                today = datetime.date.today()
                if parsed < today:
                    errors.append(f"due_date cannot be in the past: {parsed}")
                    return False, cleaned, errors
                
                cleaned["due_date"] = parsed
            except (ValueError, TypeError):
                errors.append(f"Invalid due_date format: {due_date}. Expected YYYY-MM-DD")
                return False, cleaned, errors
        
        # Optional: estimated_hours (REJECT negative or zero)
        hours = data.get("estimated_hours")
        if hours is not None:
            try:
                hours_float = float(hours)
                if hours_float < 0:
                    errors.append(f"estimated_hours cannot be negative: {hours}")
                    return False, cleaned, errors
                elif hours_float == 0:
                    errors.append("estimated_hours cannot be zero")
                    return False, cleaned, errors
                else:
                    cleaned["estimated_hours"] = hours_float
            except (ValueError, TypeError):
                errors.append(f"Invalid estimated_hours: {hours}")
                return False, cleaned, errors
        else:
            cleaned["estimated_hours"] = 2.0  # Default if missing
        
        # Optional: importance (REJECT out of range)
        importance = data.get("importance")
        if importance is not None:
            try:
                imp_int = int(importance)
                if imp_int < 1 or imp_int > 10:
                    errors.append(f"importance must be between 1-10, got: {imp_int}")
                    return False, cleaned, errors
                cleaned["importance"] = imp_int
            except (ValueError, TypeError):
                errors.append(f"Invalid importance: {importance}")
                return False, cleaned, errors
        else:
            cleaned["importance"] = 5  # Default
        
        # Dependencies (will be resolved later)
        deps = data.get("dependencies", [])
        if not isinstance(deps, list):
            errors.append(f"dependencies must be a list, got: {type(deps)}")
            return False, cleaned, errors
        else:
            cleaned["dependencies"] = deps
        
        is_valid = len(errors) == 0
        return is_valid, cleaned, errors

