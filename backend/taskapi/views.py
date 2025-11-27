from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Task
from .serializers import TaskSerializer
from .scoring.priority_engine import PriorityEngine
from django.db import connection
# class AnalyzeTasksView(APIView):
#     def post(self, request):
#         serializer = TaskSerializer(data=request.data, many=True)

#         if not serializer.is_valid():
#             return Response(serializer.errors, status=400)

#         tasks = serializer.save()  # create in DB

#         engine = PriorityEngine(tasks)
#         scored, cycles = engine.run()

#         output = []
#         for item in scored:
#             output.append({
#                 "id": item["task"].id,
#                 "title": item["task"].title,
#                 "score": item["score"]
#             })

#         return Response({
#             "scored_tasks": output,
#             "cyclic_task_ids": cycles
#         })
        
class AnalyzeTasksView(APIView):
    def post(self, request):
        task_data = request.data
        
        # Phase 1: create tasks without dependencies
        created = []
        dep_map = {}
        for i, data in enumerate(task_data):
            deps = data.pop("dependencies", [])
            dep_map[i] = deps
            
            serializer = TaskSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            created.append(serializer.save())
        
        index_map = {i: t for i, t in enumerate(created)}
        
        # Phase 2: resolve dependencies
        for i, deps in dep_map.items():
            resolved = []
            for d in deps:
                if (d - 1) in index_map:
                    resolved.append(index_map[d - 1])
            index_map[i].dependencies.set(resolved)
        
        # scoring
        engine = PriorityEngine(created)
        scored, cycles = engine.run()
        
        # dependency-aware ordering
        def blocked(e):
            return e["task"].dependencies.exists()

        unblocked = [e for e in scored if not blocked(e)]
        blocked_tasks = [e for e in scored if blocked(e)]

        unblocked.sort(key=lambda x: x["score"], reverse=True)
        blocked_tasks.sort(key=lambda x: x["score"], reverse=True)

        ordered = unblocked + blocked_tasks
        
        response = [
            {
                "id": e["task"].id,
                "title": e["task"].title,
                "score": e["score"],
                "blocked_by": [dep.id for dep in e["task"].dependencies.all()]
            }
            for e in ordered
        ]

        return Response({
            "scored_tasks": response,
            "cyclic_task_ids": cycles
        })

# class SuggestTasksView(APIView):
#     def get(self, request):
#         tasks = Task.objects.all()
#         engine = PriorityEngine(tasks)
#         scored, cycles = engine.run()

#         top = scored[:3]

#         formatted = []
#         for entry in top:
#             t = entry["task"]
#             formatted.append({
#                 "id": t.id,
#                 "title": t.title,
#                 "score": entry["score"],
#                 "reason": {
#                     "urgency": engine.urgency_score(t),
#                     "importance": engine.importance_score(t),
#                     "effort": engine.effort_score(t),
#                     "dependency": engine.dependency_score(t)
#                 }
#             })

#         return Response({
#             "top_tasks": formatted,
#             "cyclic_task_ids": cycles
#         })
class SuggestTasksView(APIView):
    def get(self, request):
        tasks = Task.objects.all()
        engine = PriorityEngine(tasks)
        scored, cycles = engine.run()

        
        # 1. Determine blocked vs unblocked
        
        def is_blocked(entry):
            task = entry["task"]
            return task.dependencies.exists()

        unblocked = [e for e in scored if not is_blocked(e)]
        blocked = [e for e in scored if is_blocked(e)]

        
        # 2. Sort each group by score
        
        unblocked.sort(key=lambda x: x["score"], reverse=True)
        blocked.sort(key=lambda x: x["score"], reverse=True)

        
        # 3. Merge: unblocked first, then blocked
        
        ordered = unblocked + blocked

        # take top 3
        top = ordered[:3]

        
        # 4. Format response
        
        formatted = []
        for entry in top:
            t = entry["task"]
            formatted.append({
                "id": t.id,
                "title": t.title,
                "score": entry["score"],
                "blocked": t.dependencies.exists(),
                "blocked_by": [dep.id for dep in t.dependencies.all()],
                "reason": {
                    "urgency": engine.urgency_score(t),
                    "importance": engine.importance_score(t),
                    "effort": engine.effort_score(t),
                    "dependency": engine.dependency_score(t)
                }
            })

        return Response({
            "top_tasks": formatted,
            "cyclic_task_ids": cycles
        })

class ResetTasksView(APIView):
    def delete(self, request):
        # Delete all tasks
        Task.objects.all().delete()

        # Reset ID auto-increment for SQLite or Postgres
        with connection.cursor() as cursor:
            vendor = connection.vendor

            if vendor == 'sqlite':
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='taskapi_task';")

            elif vendor == 'postgresql':
                cursor.execute("ALTER SEQUENCE taskapi_task_id_seq RESTART WITH 1;")

        return Response(
            {"message": "Tasks wiped. ID counter reset to 1."},
            status=status.HTTP_200_OK
        )
    """
    Safely reset the Task table so test cases can be run repeatedly.
    """

    def delete(self, request):
        # Delete all Task rows
        Task.objects.all().delete()

        return Response(
            {"message": "All tasks deleted. Database is clean."},
            status=status.HTTP_200_OK
        )
    
class ListTasksView(APIView):
    """
    Returns all tasks currently stored in the database,
    including dependency IDs for verification.
    """
    def get(self, request):
        tasks = Task.objects.all().order_by("id")

        data = []
        for t in tasks:
            data.append({
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date,
                "estimated_hours": t.estimated_hours,
                "importance": t.importance,
                "dependencies": [dep.id for dep in t.dependencies.all()]
            })

        return Response({"tasks": data}, status=200)
