from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import (
    UltrasoundImage, 
    PelvicUltrasoundMeasurements,
    AbdominalUltrasoundMeasurements,
    BreastUltrasoundMeasurements,
    ThyroidUltrasoundMeasurements
)
import json

@require_http_methods(["GET", "POST"])
def exam_annotations(request, exam_id):
    image = get_object_or_404(UltrasoundImage, id=exam_id)
    
    if request.method == "GET":
        # Get the procedure type from query params
        procedure_type = request.GET.get('type')
        
        # Get measurements based on procedure type
        measurements = None
        if procedure_type:
            measurement_model = {
                'pelvic': PelvicUltrasoundMeasurements,
                'abdominal': AbdominalUltrasoundMeasurements,
                'breast': BreastUltrasoundMeasurements,
                'thyroid': ThyroidUltrasoundMeasurements
            }.get(procedure_type)
            
            if measurement_model:
                measurement_obj = measurement_model.objects.filter(ultrasound_image=image).first()
                if measurement_obj:
                    # Convert model instance to dictionary excluding certain fields
                    measurements = {
                        field.name: getattr(measurement_obj, field.name)
                        for field in measurement_obj._meta.fields
                        if field.name not in ['id', 'ultrasound_image', 'created_at', 'updated_at']
                        and getattr(measurement_obj, field.name) is not None
                    }
        
        return JsonResponse({
            'annotations': image.annotations if image.annotations else None,
            'measurements': measurements
        })
    
    elif request.method == "POST":
        try:
            data = json.loads(request.body)
            procedure_type = data.get('procedure_type')
            
            # Save annotations
            if not image.annotations:
                image.annotations = {}
            image.annotations = data.get('annotations')
            image.save()
            
            # Save measurements based on procedure type
            if procedure_type and data.get('measurements'):
                measurement_model = {
                    'pelvic': PelvicUltrasoundMeasurements,
                    'abdominal': AbdominalUltrasoundMeasurements,
                    'breast': BreastUltrasoundMeasurements,
                    'thyroid': ThyroidUltrasoundMeasurements
                }.get(procedure_type)
                
                if measurement_model:
                    # Get or create measurement object
                    measurement_obj, created = measurement_model.objects.get_or_create(
                        ultrasound_image=image
                    )
                    
                    # Update measurements
                    for field, value in data['measurements'].items():
                        if hasattr(measurement_obj, field):
                            setattr(measurement_obj, field, value)
                    
                    measurement_obj.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400) 