from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import UltrasoundExam
import json

@require_http_methods(["GET", "POST"])
def exam_annotations(request, exam_id):
    exam = get_object_or_404(UltrasoundExam, id=exam_id)
    
    if request.method == "GET":
        return JsonResponse({
            'annotations': exam.annotations if exam.annotations else None
        })
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            exam.annotations = data.get('annotations')
            exam.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400) 