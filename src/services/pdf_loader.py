import re
from PyPDF2 import PdfReader

def load_pdf_smart_clauses(file_path):
    """
    Parse tenancy PDFs into main/sub-clauses (4(a), 4(b), …) and extract clean clause titles.
    Returns list[dict]: [{'label': '4(a)', 'title': 'Payment Of Property Tax', 'text': '...'}, …]
    """
    reader = PdfReader(file_path)
    text = " ".join([page.extract_text() for page in reader.pages if page.extract_text()])
    text = re.sub(r'\s+', ' ', text)  # normalize whitespace

    main_sections = re.split(r'(?=\b\d+\.\s)', text)
    results = []

    for section in main_sections:
        section = section.strip()
        if not section:
            continue

        # ---- Extract main clause number (e.g. "4.") ----
        main_match = re.match(r'(\d+)\.\s*(.*)', section)
        if not main_match:
            continue

        main_num = main_match.group(1)
        section_body = main_match.group(2)

        # ---- Split sub-clauses like (a), (b), (c) ----
        sub_clauses = re.split(r'(?=\([a-z]\)\s)', section_body)

        if len(sub_clauses) > 1:
            for sub in sub_clauses:
                sub = sub.strip()
                if not sub:
                    continue

                sub_match = re.match(r'\(([a-z])\)\s*(.*)', sub)
                if not sub_match:
                    continue
                sub_letter, sub_text = sub_match.groups()
                label = f"{main_num}({sub_letter})"

                # ---- Improved title extraction ----
                # Match uppercase words followed by punctuation or lowercase (end of heading)
                title_match = re.match(r'([A-Z][A-Z\s\-&,]+?)(?=\s+[A-Z][a-z])', sub_text)
                if title_match:
                    title = title_match.group(1).strip().title()
                    body = sub_text[len(title_match.group(0)):].strip()
                else:
                    title, body = None, sub_text.strip()

                results.append({
                    "label": label,
                    "title": title,
                    "text": body
                })
        else:
            # ---- Single-clause section ----
            title_match = re.match(r'([A-Z][A-Z\s\-&,]+?)(?=\s+[A-Z][a-z])', section_body)
            if title_match:
                title = title_match.group(1).strip().title()
                body = section_body[len(title_match.group(0)):].strip()
            else:
                title, body = None, section_body.strip()

            results.append({
                "label": main_num,
                "title": title,
                "text": body
            })

    print(f"⚙️ Parsed {len(results)} clauses/sub-clauses from {file_path}")
    return results