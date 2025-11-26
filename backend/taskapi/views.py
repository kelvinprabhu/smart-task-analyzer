from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Task
from .serializers import TaskSerializer
from .scoring.priority_engine import PriorityEngine

class AnalyzeTasksView(APIView):
    def post(self, request):
        serializer = TaskSerializer(data=request.data, many=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        tasks = serializer.save()  # create in DB

        engine = PriorityEngine(tasks)
        scored, cycles = engine.run()

        output = []
        for item in scored:
            output.append({
                "id": item["task"].id,
                "title": item["task"].title,
                "score": item["score"]
            })

        return Response({
            "scored_tasks": output,
            "cyclic_task_ids": cycles
        })
        

class SuggestTasksView(APIView):
    def get(self, request):
        tasks = Task.objects.all()
        engine = PriorityEngine(tasks)
        scored, cycles = engine.run()

        top = scored[:3]

        formatted = []
        for entry in top:
            t = entry["task"]
            formatted.append({
                "id": t.id,
                "title": t.title,
                "score": entry["score"],
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
