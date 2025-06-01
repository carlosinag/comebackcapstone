from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.messages import add_message, INFO
from .models import (
    UltrasoundImage, 
    PelvicUltrasoundMeasurements,
    AbdominalUltrasoundMeasurements,
    BreastUltrasoundMeasurements,
    ThyroidUltrasoundMeasurements
)
import json
import logging
import base64
from django.core.files.base import ContentFile
from datetime import datetime

logger = logging.getLogger(__name__)

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
        
        # Get notes from annotations if they exist
        notes = None
        if image.annotations and isinstance(image.annotations, dict):
            notes = image.annotations.get('notes')
        
        return JsonResponse({
            'annotations': image.annotations if image.annotations else None,
            'measurements': measurements,
            'notes': notes
        })
    
    elif request.method == "POST":
        try:
            # Log incoming data for debugging
            logger.debug(f"Received data: {request.body.decode('utf-8')}")
            
            data = json.loads(request.body)
            procedure_type = data.get('procedure_type')
            
            if not procedure_type:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Procedure type is required'
                }, status=400)
            
            with transaction.atomic():
                # Save annotations and notes
                annotations = data.get('annotations')
                notes = data.get('notes')
                
                # If annotations is a dict, update it with notes
                if isinstance(annotations, dict):
                    annotations['notes'] = notes
                # If annotations is not a dict, create a new dict
                else:
                    annotations = {
                        'canvas': annotations,
                        'notes': notes
                    }
                
                image.annotations = annotations
                image.save()
                
                # Save measurements based on procedure type
                if data.get('measurements'):
                    measurement_model = {
                        'pelvic': PelvicUltrasoundMeasurements,
                        'abdominal': AbdominalUltrasoundMeasurements,
                        'breast': BreastUltrasoundMeasurements,
                        'thyroid': ThyroidUltrasoundMeasurements
                    }.get(procedure_type.lower())
                    
                    if not measurement_model:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Invalid procedure type: {procedure_type}'
                        }, status=400)
                    
                    try:
                        # Delete existing measurements for this image and type
                        measurement_model.objects.filter(ultrasound_image=image).delete()
                        
                        # Create new measurements
                        measurements = data.get('measurements')
                        measurement_obj = measurement_model(ultrasound_image=image)
                        
                        for field_name, value in measurements.items():
                            if hasattr(measurement_obj, field_name):
                                field = measurement_model._meta.get_field(field_name)
                                if isinstance(field, models.DecimalField) and value:
                                    try:
                                        # Extract numeric value from string (e.g., "5.2 cm" -> 5.2)
                                        numeric_value = ''.join(c for c in str(value) if c.isdigit() or c == '.')
                                        if numeric_value:
                                            value = float(numeric_value)
                                    except (ValueError, TypeError) as e:
                                        logger.warning(f"Error converting value '{value}' for field {field_name}: {str(e)}")
                                        continue
                                setattr(measurement_obj, field_name, value)
                        
                        # Validate before saving
                        measurement_obj.full_clean()
                        measurement_obj.save()
                    except ValidationError as e:
                        logger.error(f"Validation error: {str(e)}")
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Validation error: {str(e)}'
                        }, status=400)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Annotations, measurements, and notes saved successfully'
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': f'An unexpected error occurred: {str(e)}'
            }, status=500)

@require_http_methods(["POST"])
def save_annotation_preview(request, exam_id):
    image = get_object_or_404(UltrasoundImage, id=exam_id)
    
    try:
        data = json.loads(request.body)
        image_data = data.get('image_data')
        procedure_type = data.get('procedure_type')
        annotations = data.get('annotations')
        preview_html = data.get('preview_html')
        
        if not image_data or not procedure_type:
            return JsonResponse({
                'status': 'error',
                'message': 'Image data and procedure type are required'
            }, status=400)
        
        # Remove the data:image/png;base64 prefix
        image_data = image_data.split(',')[1]
        
        # Create a filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'annotated_{image.id}_{timestamp}.png'
        
        # Convert base64 to file
        image_content = ContentFile(base64.b64decode(image_data), name=filename)
        
        # Save the annotated image
        image.annotated_image = image_content
        image.annotations = annotations
        image.save()
        
        # Get patient ID for redirect
        patient_id = image.exam.patient.id
        
        return JsonResponse({
            'status': 'success',
            'message': 'Annotation preview saved successfully',
            'download_url': image.annotated_image.url if image.annotated_image else None,
            'patient_id': patient_id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Error saving annotation preview: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Error saving annotation preview'
        }, status=500) 