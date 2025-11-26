import datetime

class PriorityEngine:
    def __init__(self, tasks):
        self.tasks = tasks
        self.today = datetime.date.today()

    # ---------------- CIRCULAR DEPENDENCY DETECTION ----------------
    def detect_cycles(self):
        visited = set()
        stack = set()

        def dfs(task):
            if task.id in stack:
                return True  # cycle detected
            if task.id in visited:
                return False

            visited.add(task.id)
            stack.add(task.id)

            for dep in task.dependencies.all():
                if dfs(dep):
                    return True

            stack.remove(task.id)
            return False

        cyclic_tasks = []
        for task in self.tasks:
            if dfs(task):
                cyclic_tasks.append(task.id)

        return cyclic_tasks

    # ---------------- PRIORITY SCORE CALCULATION ----------------
    def urgency_score(self, task):
        if not task.due_date:
            return 0

        delta = (task.due_date - self.today).days

        if delta < 0:
            return 10  # past due = max urgency
        if delta == 0:
            return 9
        if delta <= 3:
            return 8
        if delta <= 7:
            return 6
        return 3

    def importance_score(self, task):
        return task.importance

    def effort_score(self, task):
        # lower hours = higher priority
        if task.estimated_hours <= 1:
            return 8
        if task.estimated_hours <= 3:
            return 6
        if task.estimated_hours <= 5:
            return 4
        return 2

    def dependency_score(self, task):
        # tasks that unblock many others should rank higher
        count = 0
        for t in self.tasks:
            if task in t.dependencies.all():
                count += 1

        return min(count * 2, 10)

    def calculate_score(self, task):
        return (
            self.urgency_score(task)
            + self.importance_score(task)
            + self.effort_score(task)
            + self.dependency_score(task)
        )

    def run(self):
        cyclic = self.detect_cycles()
        valid_tasks = [t for t in self.tasks if t.id not in cyclic]

        scored = []
        for task in valid_tasks:
            scored.append({
                "task": task,
                "score": self.calculate_score(task)
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored, cyclic
