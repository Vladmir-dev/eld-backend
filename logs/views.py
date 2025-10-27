from rest_framework import viewsets
from .models import DailyLog, LogEntry
from .serializers import DailyLogSerializer, LogEntrySerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.http import FileResponse
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime


class DailyLogViewSet(viewsets.ModelViewSet):
    queryset = DailyLog.objects.all()
    serializer_class = DailyLogSerializer
    permission_classes = [IsAuthenticated]

class LogEntryViewSet(viewsets.ModelViewSet):
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer
    permission_classes = [IsAuthenticated]


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_log_pdf(request, pk):
    try:
        # NOTE: You need to import DailyLog from your models file
        # Example: from .models import DailyLog 
        log = DailyLog.objects.get(pk=pk)
    except Exception: # DailyLog.DoesNotExist:
        return Response({"error": "Log not found"}, status=404)

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    margin = 1.0 * inch
    
    # ----------------------------------------------
    # 1. Define Vertical Anchors
    # ----------------------------------------------
    
    # Header Area
    y_header_top = height - 1.0 * inch 
    
    # Mileage Box
    y_mileage_box = height - 2.3 * inch
    
    # HOS Grid
    y_grid_start = height - 3.2 * inch
    y_grid_height = 4 * 0.5 * inch # 4 activity rows * 0.5 inch height
    y_grid_end = y_grid_start - y_grid_height
    
    # Signature/Footer (Fixed reference point near the bottom)
    y_signature_block = 0.7 * inch 


    # ───────────── HEADER ─────────────
    p.setFont("Helvetica-Bold", 16)
    p.drawString(margin, y_header_top, "Driver’s Daily Log")

    p.setFont("Helvetica", 10)
    p.drawString(margin, y_header_top - 0.3 * inch, f"Date: {log.date.strftime('%Y-%m-%d')}")
    p.drawString(4 * inch, y_header_top - 0.3 * inch, f"Driver: {log.trip.user.first_name} {log.trip.user.last_name}")
    p.drawString(7 * inch, y_header_top - 0.3 * inch, f"Carrier: {log.carrier_name or 'N/A'}")

    # Trip Details
    p.drawString(margin, y_header_top - 0.6 * inch, f"From: {log.trip.pickup_location}")
    p.drawString(4 * inch, y_header_top - 0.6 * inch, f"To: {log.trip.dropoff_location}")
    p.drawString(7 * inch, y_header_top - 0.6 * inch, f"Manifest No: {log.manifest_number or 'N/A'}")

    # ───────────── MILEAGE TABLE ─────────────
    p.rect(margin, y_mileage_box, 2 * inch, 0.4 * inch)
    p.drawString(margin + 0.1 * inch, y_mileage_box + 0.2 * inch, f"Total Miles Today: {log.total_miles_driven}")

    p.rect(3.2 * inch, y_mileage_box, 2 * inch, 0.4 * inch)
    p.drawString(3.3 * inch, y_mileage_box + 0.2 * inch, f"Total Mileage: {log.total_mileage_today}")

    # ───────────── HOS GRID ─────────────
    p.setFont("Helvetica", 9)
    grid_x_start = margin
    grid_x_end = width - margin
    grid_width = grid_x_end - grid_x_start

    # Keys (Database Values) and Labels (Display Text)
    activity_keys = ["off_duty", "sleeper", "driving", "on_duty"]
    grid_labels = ["Off Duty", "Sleeper", "Driving", "On Duty"]

    # Draw horizontal lines and labels
    for i, act_label in enumerate(grid_labels):
        y = y_grid_start - i * 0.5 * inch
        p.drawString(0.6 * inch, y + 0.15 * inch, act_label)
        p.line(grid_x_start, y, grid_x_end, y)

    # Draw vertical hour lines (0–24)
    for h in range(25):
        x = grid_x_start + (grid_width / 24) * h
        p.line(x, y_grid_start, x, y_grid_end)
    
    # Draw final horizontal line to close the grid
    p.line(grid_x_start, y_grid_end, grid_x_end, y_grid_end)

    # Draw lines representing each activity entry
    entries = log.entries.all().order_by("start_hour")
    for entry in entries:
        try:
            # FIX: Use the key list to find the index of the database value
            y_index = activity_keys.index(entry.activity_type)
        except ValueError:
            continue

        y_pos = y_grid_start - y_index * 0.5 * inch
        x_start = grid_x_start + (grid_width / 24) * entry.start_hour
        x_end = grid_x_start + (grid_width / 24) * entry.end_hour
        
        p.setStrokeColor(colors.blue)
        p.setLineWidth(3)
        p.line(x_start, y_pos, x_end, y_pos)

    p.setStrokeColor(colors.black)
    p.setLineWidth(1)

    # ----------------------------------------------
    # 2. Sequential Content (Fixed Truncation)
    # ----------------------------------------------
    
    # ───────────── REMARKS ─────────────
    # Start 0.3 inch below the grid end
    y_remarks_start = y_grid_end - 0.3 * inch 

    p.setFont("Helvetica", 10)
    p.drawString(margin, y_remarks_start, "Remarks:")
    p.setFont("Helvetica", 9)
    # text object starts below the label
    text = p.beginText(margin, y_remarks_start - 0.2 * inch) 
    text.textLines(log.remarks or "—")
    p.drawText(text)
    
    # Calculate where the remarks section ended (assuming max 3 lines for brevity)
    # A more robust solution involves checking text.getY() after drawText, 
    # but for simplicity, we'll use a fixed drop.
    y_after_remarks = y_remarks_start - 0.2 * inch - (3 * 0.15 * inch)
    
    
    # ───────────── SHIPPING & COMMODITY ─────────────
    # Start 0.3 inch below where the remarks ended
    y_shipping_start = y_after_remarks - 0.3 * inch

    p.setFont("Helvetica", 10)
    p.drawString(margin, y_shipping_start, "Shipping Documents:")
    p.drawString(3.2 * inch, y_shipping_start, f"{log.manifest_number or '—'}")

    p.drawString(margin, y_shipping_start - 0.3 * inch, "Shipper & Commodity:")
    # FIX: Using the correct model field name: log.shipper_and_commodity
    p.drawString(3.2 * inch, y_shipping_start - 0.3 * inch, f"{log.shipper_and_commodity or '—'}")

    
    # ───────────── RECAP ─────────────
    # Start 0.6 inch below the shipping info
    y_recap_start = y_shipping_start - 0.6 * inch 

    p.setFont("Helvetica-Bold", 10)
    p.drawString(margin, y_recap_start, "Recap:")
    p.setFont("Helvetica", 9)
    
    # NOTE: You must replace 'N/A' placeholders with actual calculations/model properties
    recap_text = f"Total hours today: {log.total_driving_hours + log.total_on_duty_hours} | Last 7 days: {'N/A'} | Available: {'N/A'}"
    p.drawString(margin, y_recap_start - 0.2 * inch, recap_text)


    # ───────────── DRIVER CERTIFICATION/SIGNATURE ─────────────
    # This is positioned relative to the bottom margin (y_signature_block)

    p.setFont("Helvetica", 9)
    y_sig = y_signature_block + 0.3 * inch

    # Draw line for signature
    p.line(margin, y_sig, 4 * inch, y_sig)
    p.drawString(margin, y_sig - 0.15 * inch, "Driver Signature / Certification")

    # Date of Certification
    p.line(5 * inch, y_sig, 8 * inch, y_sig)
    p.drawString(5 * inch, y_sig - 0.15 * inch, "Date & Time Certified")


    p.showPage()
    p.save()
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename=f"log_{log.id}.pdf")
