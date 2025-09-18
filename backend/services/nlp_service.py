# File: backend/services/nlp_service.py
import re

class NLPService:
    def classify_context(self, text: str) -> str:
        """
        A simple keyword-based classifier to determine the ticket's context.
        """
        text_lower = text.lower()
        
        invoice_keywords = ["invoice", "inv", "billing", "payment", "remittance"]
        po_keywords = ["purchase order", "po", "procurement", "vendor", "supplier"]
        
        if any(keyword in text_lower for keyword in invoice_keywords):
            return "AP.Invoice"
        if any(keyword in text_lower for keyword in po_keywords):
            return "PO.Creation"
            
        return "General.Inquiry"

    def extract_entities(self, text: str) -> dict:
        """
        Extracts key entities from text using more robust regular expressions.
        """
        entities = {}
        
        # Define more flexible regex patterns.
        patterns = {
            # FIX: Now looks for "invoice id", "inv id", or just "ID".
            # It also handles different separators (space, colon, dash).
            "Invoice ID": r"(?:invoice\s*id|inv\s*id|id)\s*[:\s-]*(\b[A-Z0-9-]+\b)",
            
            # FIX: Now handles words like "is" or "of" between the keyword and the value.
            # It also better handles comma-separated thousands.
            "Amount": r"\b(amount|total)\b\s*(?:is|of|:)?\s*\$?((?:\d{1,3},)*\d{1,3}\.\d{2})\b",
            
            # This pattern is for common date formats.
            "Invoice Date": r"(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s\d{1,2},\s\d{4})",
            
            "PO Number": r"(?:po\s*(?:number|#))\s*[:\s]*(\b[A-Z0-9-]+\b)",
            
            "Vendor Name": r"(?:vendor|supplier)\s*[:\s]*([A-Za-z\s,]+(?:Inc\.|Corp\.|Ltd\.))"
        }

        for entity_name, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # The actual value is in the last captured group.
                value = match.groups()[-1]
                entities[entity_name] = value.strip()
                
        return entities

