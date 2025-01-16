# src/utils/helpers.py
import json
from typing import Any, Dict, Optional
from datetime import datetime, date
from pandas import DataFrame
import pandas as pd

class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime and DataFrame objects"""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, DataFrame):
            return obj.to_dict(orient='records')
        return super().default(obj)

def safe_json_dumps(obj: Any) -> str:
    """Safely convert object to JSON string"""
    return json.dumps(obj, cls=CustomJSONEncoder)

def load_csv_safely(filepath: str, **kwargs) -> Optional[DataFrame]:
    """Safely load CSV file with error handling"""
    try:
        return pd.read_csv(filepath, **kwargs)
    except Exception as e:
        logger.error(f"Error loading CSV file {filepath}: {str(e)}")
        return None

def format_error_message(error: Exception) -> str:
    """Format error message for user response"""
    if isinstance(error, HTTPException):
        return str(error.detail)
    return "Se produjo un error interno. Por favor, inténtalo de nuevo más tarde."

def extract_store_info_from_query(query: str) -> Dict[str, Optional[str]]:
    """Extract store information from query using basic pattern matching"""
    import re
    
    # Look for store ID pattern (numbers 5-10 digits long)
    store_id_match = re.search(r'\b\d{5,10}\b', query)
    store_id = store_id_match.group(0) if store_id_match else None
    
    # Look for company name (words following common patterns)
    company_patterns = [
        r'empresa\s+(\w+)',
        r'comercio\s+de\s+(\w+)',
        r'tienda\s+(\w+)',
        r'en\s+(\w+)'
    ]
    
    company_name = None
    for pattern in company_patterns:
        match = re.search(pattern, query.lower())
        if match:
            company_name = match.group(1)
            break
    
    return {
        "company_name": company_name,
        "store_id": store_id
    }