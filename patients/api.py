from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.messages import add_message, INFO
from .models import (
    UltrasoundImage, 
#     PelvicUltrasoundMeasurements,
#     AbdominalUltrasoundMeasurements,
#     BreastUltrasoundMeasurements,
#     ThyroidUltrasoundMeasurements
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
        annotations = image.annotations
        measurements = None
        notes = None
        drawing_notes = None
        on_image_measurements = None

        if isinstance(annotations, dict):
            measurements = annotations.get('measurements')
            notes = annotations.get('notes')
            drawing_notes = annotations.get('drawing_notes')
            on_image_measurements = annotations.get('on_image_measurements')

        return JsonResponse({
            'annotations': annotations if annotations else None,
            'measurements': measurements,
            'notes': notes,
            'drawing_notes': drawing_notes,
            'on_image_measurements': on_image_measurements,
        })

    elif request.method == "POST":
        try:
            logger.debug(f"Received data: {request.body.decode('utf-8')}")
            data = json.loads(request.body)

            # We still accept procedure_type in the payload for compatibility,
            # but we no longer use it to choose any DB model.
            procedure_type = data.get('procedure_type')

            with transaction.atomic():
                raw_annotations = data.get('annotations') or {}
                notes = data.get('notes')
                measurement_data = data.get('measurements') or {}
                drawing_notes_data = data.get('drawing_notes') or {}
                on_image_measurements = data.get('on_image_measurements')

                # Ensure annotations is a dict we can enrich
                if not isinstance(raw_annotations, dict):
                    annotations = {
                        'canvas': raw_annotations,
                    }
                else:
                    annotations = raw_annotations

                # Attach all structured info into the annotations JSON
                annotations['notes'] = notes
                annotations['measurements'] = measurement_data
                annotations['drawing_notes'] = drawing_notes_data
                if on_image_measurements is not None:
                    annotations['on_image_measurements'] = on_image_measurements

                image.annotations = annotations
                image.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Annotations and notes saved successfully'
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
        procedure_type = data.get('procedure_type')  # still accepted but no longer required
        raw_annotations = data.get('annotations') or {}
        preview_html = data.get('preview_html')

        # Additional structured data (all stored in annotations JSON)
        notes = data.get('notes')
        drawing_notes_data = data.get('drawing_notes') or {}
        on_image_measurements = data.get('on_image_measurements') or []

        if not image_data:
            return JsonResponse({
                'status': 'error',
                'message': 'Image data is required'
            }, status=400)
        
        # Remove the data:image/png;base64 prefix
        image_data = image_data.split(',')[1]
        
        # Create a filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'annotated_{image.id}_{timestamp}.png'
        
        # Convert base64 to file
        image_content = ContentFile(base64.b64decode(image_data), name=filename)
        
        # Normalize annotations dict
        if not isinstance(raw_annotations, dict):
            annotations = {
                'canvas': raw_annotations,
            }
        else:
            annotations = raw_annotations

        # Enrich annotations with structured data
        annotations['notes'] = notes
        annotations['drawing_notes'] = drawing_notes_data
        annotations['on_image_measurements'] = on_image_measurements

        # Optionally keep preview_html inside annotations if you want it retrievable later
        if preview_html is not None:
            annotations['preview_html'] = preview_html

        # Save the annotated image and annotations JSON
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