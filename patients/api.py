from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.messages import add_message, INFO
from .models import (
    UltrasoundImage,
    Appointment,
#     PelvicUltrasoundMeasurements,
#     AbdominalUltrasoundMeasurements,
#     BreastUltrasoundMeasurements,
#     ThyroidUltrasoundMeasurements
)
import json
import logging
import base64
from django.core.files.base import ContentFile
from datetime import datetime, date
from django.utils.dateparse import parse_date
from django.db.models import Count
import cv2
import numpy as np
from PIL import Image
import io
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

@require_http_methods(["GET", "POST"])
def exam_annotations(request, exam_id):
    image = get_object_or_404(UltrasoundImage, id=exam_id)

    if request.method == "GET":
        annotations = image.annotations
        measurements = None
        notes = None
        drawing_notes = None
        auto_annotation_notes = None
        on_image_measurements = None

        if isinstance(annotations, dict):
            measurements = annotations.get('measurements')
            notes = annotations.get('notes')
            drawing_notes = annotations.get('drawing_notes')
            auto_annotation_notes = annotations.get('auto_annotation_notes')
            on_image_measurements = annotations.get('on_image_measurements')

        return JsonResponse({
            'annotations': annotations if annotations else None,
            'measurements': measurements,
            'notes': notes,
            'drawing_notes': drawing_notes,
            'auto_annotation_notes': auto_annotation_notes,
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
                auto_annotation_notes_data = data.get('auto_annotation_notes') or {}
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
                annotations['auto_annotation_notes'] = auto_annotation_notes_data
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
        auto_annotation_notes_data = data.get('auto_annotation_notes') or {}
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
        annotations['auto_annotation_notes'] = auto_annotation_notes_data
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

@require_http_methods(["GET"])
def appointment_calendar_counts(request):
    """API endpoint to get appointment counts for a date range."""
    # Check authentication and staff status
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({
            'status': 'error',
            'message': 'Authentication required'
        }, status=403)
    
    try:
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if not start_date_str or not end_date_str:
            return JsonResponse({
                'status': 'error',
                'message': 'start_date and end_date parameters are required'
            }, status=400)
        
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
        
        if not start_date or not end_date:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }, status=400)
        
        # Get appointment counts grouped by date
        appointments = Appointment.objects.filter(
            appointment_date__gte=start_date,
            appointment_date__lte=end_date
        ).values('appointment_date').annotate(
            count=Count('id')
        ).order_by('appointment_date')
        
        # Convert to dictionary with date strings as keys
        counts = {}
        for item in appointments:
            date_str = item['appointment_date'].strftime('%Y-%m-%d')
            counts[date_str] = item['count']
        
        return JsonResponse({
            'status': 'success',
            'counts': counts
        })
        
    except Exception as e:
        logger.error(f'Error fetching calendar counts: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Error fetching appointment counts'
        }, status=500)

@require_http_methods(["POST"])
def auto_annotate_image(request, exam_id):
    """Auto-annotate ultrasound image using OpenCV, NumPy, and Pillow."""
    image = get_object_or_404(UltrasoundImage, id=exam_id)
    
    try:
        # Read the image file
        img = None
        try:
            image_path = image.image.path
            img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                logger.warning(f'cv2.imread returned None for path: {image_path}')
                # Try loading with PIL and converting
                pil_img = Image.open(image_path)
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2GRAY)
        except (ValueError, AttributeError, IOError) as e:
            logger.error(f'Error loading image from path: {str(e)}')
            return JsonResponse({
                'status': 'error',
                'message': f'Could not read image file: {str(e)}'
            }, status=400)
        
        if img is None or img.size == 0:
            return JsonResponse({
                'status': 'error',
                'message': 'Could not read image file. Image may be corrupted or inaccessible.'
            }, status=400)
        
        # Get image dimensions for coordinate mapping
        img_height, img_width = img.shape
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(img, (5, 5), 0)
        
        # Use multiple detection methods and combine results
        kernel = np.ones((3, 3), np.uint8)
        all_contours = []
        
        # Method 1: Use RETR_EXTERNAL to get only external contours (avoid nested)
        _, binary1 = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        binary1 = cv2.morphologyEx(binary1, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary1 = cv2.morphologyEx(binary1, cv2.MORPH_OPEN, kernel, iterations=1)
        contours1, _ = cv2.findContours(binary1, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours1)
        
        # Method 2: Adaptive thresholding for varying lighting
        binary2 = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        binary2 = cv2.morphologyEx(binary2, cv2.MORPH_CLOSE, kernel, iterations=1)
        contours2, _ = cv2.findContours(binary2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours2)
        
        # Method 3: Canny edges + findContours to detect boundaries
        edges = cv2.Canny(blurred, 30, 100)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        contours3, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        all_contours.extend(contours3)
        
        # Method 4: Mean shift or simple threshold variations
        mean_val = np.mean(blurred)
        std_val = np.std(blurred)
        # Try multiple threshold levels
        for threshold_factor in [0.6, 0.7, 0.8, 0.9]:
            _, binary4 = cv2.threshold(
                blurred, 
                mean_val * threshold_factor, 
                255, 
                cv2.THRESH_BINARY_INV
            )
            binary4 = cv2.morphologyEx(binary4, cv2.MORPH_CLOSE, kernel, iterations=1)
            contours4, _ = cv2.findContours(binary4, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            all_contours.extend(contours4)
        
        # Filter contours - focus on smaller, distinct regions
        min_area = (img_width * img_height) * 0.002  # Lowered to 0.2% - detect smaller structures
        max_area = (img_width * img_height) * 0.3    # Lowered to 30% - exclude large background
        
        contour_info = []
        seen_signatures = set()
        
        for contour in all_contours:
            area = cv2.contourArea(contour)
            
            # Filter by area
            if area < min_area or area > max_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            
            # Skip if too small
            if w < 25 or h < 25:
                continue
            
            # Create signature to avoid exact duplicates
            center_x = x + w // 2
            center_y = y + h // 2
            signature = (center_x // 15, center_y // 15, w // 10, h // 10)
            
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            
            contour_info.append({
                'contour': contour,
                'area': area,
                'bbox': (x, y, w, h)
            })
        
        # Sort by area (smaller first) to prioritize distinct structures
        contour_info.sort(key=lambda c: c['area'])
        
        regions = []
        pixel_to_mm = 0.1  # Conversion factor (adjust based on your calibration)
        selected_regions = []  # Track selected regions for overlap checking
        
        for info in contour_info:
            contour = info['contour']
            area = info['area']
            x, y, w, h = info['bbox']
            
            # Check overlap with already selected regions
            overlaps_significantly = False
            for selected in selected_regions:
                sel_x, sel_y, sel_w, sel_h = selected['bbox']
                
                # Calculate intersection
                inter_x = max(x, sel_x)
                inter_y = max(y, sel_y)
                inter_w = min(x + w, sel_x + sel_w) - inter_x
                inter_h = min(y + h, sel_y + sel_h) - inter_y
                
                if inter_w > 0 and inter_h > 0:
                    inter_area = inter_w * inter_h
                    # If overlap is more than 30% of either region, skip
                    overlap_ratio1 = inter_area / area
                    overlap_ratio2 = inter_area / selected['area']
                    if overlap_ratio1 > 0.3 or overlap_ratio2 > 0.3:
                        overlaps_significantly = True
                        break
            
            if overlaps_significantly:
                continue
            
            # Calculate compactness (how circular/compact the region is)
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                compactness = (4 * np.pi * area) / (perimeter * perimeter)
            else:
                compactness = 0
            
            # Very lenient compactness filter - accept most shapes
            if compactness < 0.02:  # Even more lenient
                continue
            
            # Exclude regions at the very edge (likely UI elements or borders)
            edge_threshold = 0.02  # 2% of image dimension
            is_at_very_edge = (
                (x < edge_threshold * img_width and (x + w) < 0.1 * img_width) or
                (y < edge_threshold * img_height and (y + h) < 0.1 * img_height) or
                ((x + w) > (1 - edge_threshold) * img_width and x > 0.9 * img_width) or
                ((y + h) > (1 - edge_threshold) * img_height and y > 0.9 * img_height)
            )
            
            if is_at_very_edge:
                continue
            
            # Add to selected regions
            selected_regions.append({
                'bbox': (x, y, w, h),
                'area': area
            })
            
            # Calculate measurements
            length_mm = max(w, h) * pixel_to_mm
            area_mm2 = area * pixel_to_mm * pixel_to_mm
            diameter_mm = 2 * np.sqrt(area / np.pi) * pixel_to_mm
            
            # Get contour points for outline
            # Simplify contour to reduce points
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert to list of [x, y] coordinates
            outline_points = [[int(point[0][0]), int(point[0][1])] for point in approx]
            
            regions.append({
                'index': len(regions) + 1,
                'bbox': {
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h)
                },
                'center': {
                    'x': int(x + w / 2),
                    'y': int(y + h / 2)
                },
                'measurements': {
                    'length': round(length_mm, 1),
                    'area': round(area_mm2, 1),
                    'diameter': round(diameter_mm, 1),
                    'width': round(w * pixel_to_mm, 1),
                    'height': round(h * pixel_to_mm, 1)
                },
                'outline': outline_points,
                'compactness': round(compactness, 3)
            })
        
        # Sort by area (largest first) and limit to top 10 distinct regions
        regions.sort(key=lambda r: r['bbox']['width'] * r['bbox']['height'], reverse=True)
        regions = regions[:10]  # Allow up to 10 regions
        
        # Debug information
        total_contours = len(all_contours)
        filtered_contours = len(contour_info)
        final_regions = len(regions)
        
        return JsonResponse({
            'status': 'success',
            'regions': regions,
            'image_width': img_width,
            'image_height': img_height,
            'pixel_to_mm': pixel_to_mm,
            'debug': {
                'total_contours_found': total_contours,
                'filtered_contours': filtered_contours,
                'final_regions': final_regions,
                'min_area_threshold': int(min_area),
                'max_area_threshold': int(max_area),
                'image_size': f'{img_width}x{img_height}'
            }
        })
        
    except Exception as e:
        logger.error(f'Error in auto-annotation: {str(e)}', exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'Error during auto-annotation: {str(e)}'
        }, status=500)