MSME AI FINANCIAL INTELLIGENCE ENGINE — VERSION 2 OCR

WHAT VERSION 2 ADDS
- Local RapidOCR invoice recognition
- Image and PDF OCR (up to the first 3 PDF pages)
- OCR confidence and processing-time display
- Automatic suggestions for vendor, invoice number, date, GST,
  subtotal, tax, total and category
- Human verification before saving
- Correction-driven recurring-vendor memory
- OCR coverage and confidence metrics on the dashboard
- Rule-based financial recommendations
- Duplicate detection by invoice identity and exact file hash

INSTALLATION
1. Stop Streamlit using Ctrl+C.
2. Back up your MSME_AI_Project folder.
3. Copy all Version 2 files into your existing project folder.
4. Replace files when Windows asks.
5. Do NOT delete:
      venv
      database\finance.db
6. Double-click install_ocr.bat.
7. Wait for "OCR installation successful".
8. Double-click run_app.bat.

FIRST OCR TEST
1. Open AI Invoice Capture.
2. Upload sample_invoice.png.
3. Click "Run OCR and suggest invoice fields".
4. Review the confidence table and recognised text.
5. Correct any uncertain fields.
6. Click "Save verified invoice".
7. Open Dashboard, Invoice Records and Vendor Memory.
8. Upload the same invoice again to demonstrate duplicate detection.

HONEST TECHNICAL DESCRIPTION
- RapidOCR performs local document-text detection and recognition.
- Regular-expression and keyword rules suggest invoice fields.
- Users verify all fields before saving.
- Vendor memory is database-driven correction adaptation in this MVP.
- The financial-health score and recommendations are explainable
  prototype rules, not a bank credit score or proof of fraud.
