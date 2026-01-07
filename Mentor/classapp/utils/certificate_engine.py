from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from io import BytesIO
from django.utils import timezone

def generate_certificate_pdf_bytes(registration, name_text=None):
    # Set Deployment Environment: A4 Landscape for better "Award" display
    width, height = landscape(A4)
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))

    # --- 1. Architectural Border Node ---
    c.setStrokeColor(colors.HexColor("#6366f1")) # Figma Primary
    c.setLineWidth(10)
    c.rect(20, 20, width - 40, height - 40)
    
    c.setStrokeColor(colors.HexColor("#0f172a")) # Figma Text Main
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60)

    # --- 2. System Watermark Handshake ---
    c.setFont("Helvetica-Bold", 80)
    c.setFillColor(colors.HexColor("#f1f5f9")) # Slate 100
    c.drawCentredString(width / 2, height / 2 - 20, "MENTOR LMS")

    # --- 3. Header Handshake ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 34)
    c.drawCentredString(width / 2, height - 120, "CERTIFICATE OF ACHIEVEMENT")
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 150, "TECHNICAL PROFICIENCY VALIDATION")

    # --- 4. Identity Mapping ---
    c.setFont("Helvetica", 18)
    c.drawCentredString(width / 2, height / 2 + 60, "This node certifies that")
    
    c.setFillColor(colors.HexColor("#6366f1"))
    c.setFont("Helvetica-Bold", 42)
    name = name_text or (registration.user.get_full_name() if registration.user else "Authorized Guest")
    c.drawCentredString(width / 2, height / 2 + 10, name.upper())

    # --- 5. Curriculum Data Sync ---
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 16)
    event_title = registration.event.title
    date_str = registration.event.date.strftime("%B %d, %Y")
    c.drawCentredString(width / 2, height / 2 - 40, f"has successfully synchronized with the curriculum node:")
    
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height / 2 - 70, f"[{event_title}]")
    
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height / 2 - 100, f"Validated on System Date: {date_str}")

    # --- 6. Authority Signatures & Verification Handshake ---
    # Signature Line
    c.setLineWidth(1)
    c.line(100, 100, 300, 100)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(140, 85, "PROGRAM DIRECTOR")

    # Digital Handshake Stamp (Geometric Node)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(width - 250, 60, 150, 150, fill=0)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width - 175, 75, "VERIFY_ID: " + str(registration.id).zfill(8))
    
    # Placeholder for QR Node Logic
    c.drawCentredString(width - 175, 130, "[SECURE_QR_STAMP]")

    # --- Finalize Build ---
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()