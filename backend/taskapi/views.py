from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Task
from .serializers import TaskSerializer
from .scoring.priority_engine import PriorityEngine, TaskValidator
from django.db import connection
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
        
class AnalyzeTasksViewV1(APIView):
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
class SuggestTasksViewV1(APIView):
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

class AnalyzeTasksView(APIView):
    def post(self, request):
        task_data = request.data
        
        # Validation: Empty list
        if not isinstance(task_data, list):
            return Response(
                {"error": "Request body must be a list of tasks"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(task_data) == 0:
            return Response({
                "message": "No tasks to analyze",
                "scored_tasks": [],
                "cyclic_task_ids": [],
                "warnings": []
            }, status=status.HTTP_200_OK)
        
        # Validate all tasks first
        validator = TaskValidator()
        validation_results = []
        all_errors = []
        valid_tasks_data = []
        
        for i, data in enumerate(task_data):
            is_valid, cleaned, errors = validator.validate_task_data(data)
            if is_valid:
                valid_tasks_data.append((i, cleaned))
            else:
                all_errors.append({
                    "task_index": i + 1,
                    "task_title": data.get("title", "Unknown"),
                    "errors": errors
                })
        
        # If ALL tasks are invalid, return error
        if not valid_tasks_data:
            return Response({
                "error": "All tasks failed validation",
                "invalid_tasks": all_errors,
                "message": "Fix validation errors and try again"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Phase 1: Create only VALID tasks
        created = []
        dep_map = {}
        original_to_new_index = {}  # Map original index to new task index
        all_warnings = []
        
        for idx, (original_idx, cleaned_data) in enumerate(valid_tasks_data):
            deps = cleaned_data.pop("dependencies", [])
            dep_map[idx] = deps
            original_to_new_index[original_idx] = idx
            
            serializer = TaskSerializer(data=cleaned_data)
            if serializer.is_valid():
                created.append(serializer.save())
            else:
                all_warnings.append(
                    f"Task {original_idx+1} serialization failed: {serializer.errors}"
                )
        
        if not created:
            return Response({
                "error": "No tasks could be created after validation",
                "invalid_tasks": all_errors,
                "warnings": all_warnings
            }, status=status.HTTP_400_BAD_REQUEST)
        
        index_map = {i: t for i, t in enumerate(created)}
        
        # Phase 2: Resolve dependencies with validation
        invalid_dependencies = []
        
        for i, deps in dep_map.items():
            resolved = []
            for d in deps:
                # Check for self-dependency
                if d == (i + 1):
                    invalid_dependencies.append(
                        f"Task {i+1} cannot depend on itself (dep: {d})"
                    )
                    continue
                
                # Check if dependency exists
                dep_index = d - 1
                if dep_index not in index_map:
                    invalid_dependencies.append(
                        f"Task {i+1} has non-existent dependency: {d}"
                    )
                    continue
                
                resolved.append(index_map[dep_index])
            
            index_map[i].dependencies.set(resolved)
        
        all_warnings.extend(invalid_dependencies)
        
        # Phase 3: Run scoring engine
        engine = PriorityEngine(created)
        scored, cycles = engine.run()
        
        # Add cycle warnings
        if cycles:
            all_warnings.append(
                f"Circular dependencies detected in tasks: {cycles}"
            )
        
        # Phase 4: Separate blocked vs unblocked
        def is_blocked(entry):
            return entry["task"].dependencies.exists()
        
        unblocked = [e for e in scored if not is_blocked(e)]
        blocked_tasks = [e for e in scored if is_blocked(e)]
        
        unblocked.sort(key=lambda x: x["score"], reverse=True)
        blocked_tasks.sort(key=lambda x: x["score"], reverse=True)
        
        ordered = unblocked + blocked_tasks
        
        # Phase 5: Format response with invalid task info
        response_data = {
            "scored_tasks": [
                {
                    "id": e["task"].id,
                    "title": e["task"].title,
                    "score": round(e["score"], 4),
                    "blocked": is_blocked(e),
                    "blocked_by": [dep.id for dep in e["task"].dependencies.all()],
                    "urgency": round(engine.urgency_score(e["task"]), 2),
                    "importance": round(engine.importance_score(e["task"]), 2),
                    "effort_factor": round(engine.effort_factor(e["task"]), 2)
                }
                for e in ordered
            ],
            "cyclic_task_ids": cycles,
            "stats": {
                "total_submitted": len(task_data),
                "valid_tasks": len(created),
                "invalid_tasks": len(all_errors),
                "blocked_tasks": len(blocked_tasks),
                "cyclic_tasks": len(cycles)
            }
        }
        
        # Include validation errors if any tasks were rejected
        if all_errors:
            response_data["invalid_tasks"] = all_errors
        
        # Include warnings if any
        if all_warnings:
            response_data["warnings"] = all_warnings
        
        return Response(response_data)

class SuggestTasksView(APIView):
    def get(self, request):
        tasks = Task.objects.all()
        
        if not tasks.exists():
            return Response({
                "message": "No tasks available to suggest",
                "top_tasks": [],
                "cyclic_task_ids": []
            })
        
        engine = PriorityEngine(tasks)
        scored, cycles = engine.run()
        
        if not scored:
            return Response({
                "message": "No valid tasks to suggest (all may be cyclic)",
                "top_tasks": [],
                "cyclic_task_ids": cycles
            })
        
        # Separate blocked vs unblocked
        def is_blocked(entry):
            return entry["task"].dependencies.exists()
        
        unblocked = [e for e in scored if not is_blocked(e)]
        blocked = [e for e in scored if is_blocked(e)]
        
        unblocked.sort(key=lambda x: x["score"], reverse=True)
        blocked.sort(key=lambda x: x["score"], reverse=True)
        
        ordered = unblocked + blocked
        top = ordered[:3]
        
        # Format response
        formatted = []
        for entry in top:
            t = entry["task"]
            formatted.append({
                "id": t.id,
                "title": t.title,
                "score": round(entry["score"], 4),
                "blocked": is_blocked(entry),
                "blocked_by": [dep.id for dep in t.dependencies.all()],
                "reason": {
                    "urgency": round(engine.urgency_score(t), 2),
                    "importance": round(engine.importance_score(t), 2),
                    "effort": round(engine.effort_score(t), 2),
                    "dependency": round(engine.dependency_score(t), 2)
                }
            })
        
        return Response({
            "top_tasks": formatted,
            "cyclic_task_ids": cycles,
            "total_available": len(scored)
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

    # def delete(self, request):
    #     # Delete all Task rows
    #     Task.objects.all().delete()

    #     return Response(
    #         {"message": "All tasks deleted. Database is clean."},
    #         status=status.HTTP_200_OK
    #     )
    
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
