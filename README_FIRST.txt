MSME AI FINANCIAL INTELLIGENCE ENGINE — VERSION 1

HOW TO USE THIS PACK
1. Stop Streamlit with Ctrl+C.
2. Copy app.py, database.py, dashboard.py, upload.py and sample_data.py
   into your existing MSME_AI_Project folder.
3. Replace the old files when Windows asks.
4. Keep your existing venv folder.
5. Run:
      python -m streamlit run app.py

FIRST TEST
1. Open "Demo Data".
2. Click "Load synthetic demo invoices".
3. Open "Dashboard".
4. Open "Invoice Records".
5. Open "Add Invoice", upload an image/PDF, enter verified values and save.
6. Upload the same file again to demonstrate duplicate detection.

VERSION 1 FEATURES
- SQLite invoice database
- Safe database migration
- Image/PDF storage
- Duplicate detection by vendor/invoice number and SHA-256 file hash
- Dashboard metrics
- Monthly expense chart
- Category chart
- Vendor analysis
- Explainable prototype financial-health score
- Three-month baseline expense forecast
- Searchable invoice table
- CSV export
- Synthetic demo data

OCR is intentionally not included yet. It is the next development phase.
