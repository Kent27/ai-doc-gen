import os
import re
import json
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import shutil
import argparse
from .logging_utils import LOGS_DIR, WHATSAPP_LOGS_DIR, clean_old_logs

def list_phone_logs() -> List[str]:
    """
    List all phone numbers that have log files.
    
    Returns:
        List of phone numbers with log files
    """
    phone_logs = []
    
    # Check if directory exists
    if not WHATSAPP_LOGS_DIR.exists():
        return phone_logs
    
    # Get all log files
    for log_file in WHATSAPP_LOGS_DIR.glob("*.log"):
        # Extract phone number from filename
        phone_number = log_file.stem
        phone_logs.append(phone_number)
    
    return phone_logs

def parse_compact_log_line(line: str) -> Dict[str, Any]:
    """
    Parse a compact log line into a structured dictionary.
    
    Args:
        line: The log line to parse
        
    Returns:
        Dictionary with parsed log data
    """
    try:
        # Extract timestamp from log line
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            log_timestamp = timestamp_match.group(1)
            
            # Extract the rest of the line after the timestamp and log level
            content_match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} - INFO - (.*)', line)
            if content_match:
                content = content_match.group(1)
                
                # Check if it's the new compact format with pipe separators
                if '|' in content:
                    parts = content.split('|', 3)  # Split into max 4 parts
                    if len(parts) >= 3:
                        timestamp, direction, msg_type = parts[0:3]
                        data_str = parts[3] if len(parts) > 3 else "{}"
                        
                        try:
                            # Try to parse the data as JSON
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            # If not valid JSON, store as raw string
                            data = {"raw_data": data_str}
                        
                        return {
                            "timestamp": timestamp,
                            "direction": direction,
                            "type": msg_type,
                            "data": data,
                            "log_timestamp": log_timestamp
                        }
                
                # Handle legacy format (for backward compatibility)
                direction_match = re.search(r'(INCOMING|OUTGOING|SYSTEM) (\w+): ({.*})', content)
                if direction_match:
                    direction = direction_match.group(1)
                    msg_type = direction_match.group(2)
                    data_str = direction_match.group(3)
                    
                    try:
                        # Parse JSON data
                        data = json.loads(data_str)
                        
                        return {
                            "direction": direction,
                            "type": msg_type,
                            "data": data,
                            "log_timestamp": log_timestamp
                        }
                    except json.JSONDecodeError:
                        # If JSON parsing fails, add raw data
                        return {
                            "direction": direction,
                            "type": msg_type,
                            "raw_data": data_str,
                            "log_timestamp": log_timestamp
                        }
    except Exception as e:
        print(f"Error parsing log line: {e}")
    
    # Return empty dict if parsing fails
    return {"raw_line": line.strip()}

def get_logs_for_phone(phone_number: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get logs for a specific phone number for the last N days.
    
    Args:
        phone_number: The phone number to get logs for
        days: Number of days to look back
        
    Returns:
        List of log entries
    """
    # Sanitize phone number
    sanitized_phone = re.sub(r'[^\d]', '', phone_number)
    
    # Set up log file path
    log_file = WHATSAPP_LOGS_DIR / f"{sanitized_phone}.log"
    
    # Check if log file exists
    if not log_file.exists():
        return []
    
    # Calculate cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
    
    # Parse log file
    logs = []
    with open(log_file, "r") as f:
        for line in f:
            try:
                # Extract timestamp from log line
                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                    
                    # Skip if older than cutoff
                    if timestamp < cutoff_date:
                        continue
                    
                    # Parse the log line
                    log_entry = parse_compact_log_line(line)
                    if log_entry and len(log_entry) > 1:  # Ensure it's not just the raw line
                        logs.append(log_entry)
                        
            except Exception as e:
                print(f"Error processing log line: {e}")
                continue
    
    return logs

def search_logs(query: str, days: int = 7) -> Dict[str, List[Dict[str, Any]]]:
    """
    Search all logs for a specific query.
    
    Args:
        query: Text to search for
        days: Number of days to look back
        
    Returns:
        Dictionary mapping phone numbers to matching log entries
    """
    results = {}
    
    # Get all phone numbers
    phone_numbers = list_phone_logs()
    
    # Search logs for each phone number
    for phone in phone_numbers:
        logs = get_logs_for_phone(phone, days)
        
        # Filter logs by query
        matching_logs = []
        for log in logs:
            log_str = json.dumps(log)
            if query.lower() in log_str.lower():
                matching_logs.append(log)
        
        # Add to results if there are matches
        if matching_logs:
            results[phone] = matching_logs
    
    return results

def export_logs(phone_number: str, output_file: str, days: int = 30):
    """
    Export logs for a specific phone number to a file.
    
    Args:
        phone_number: The phone number to export logs for
        output_file: Path to output file
        days: Number of days to look back
    """
    # Get logs
    logs = get_logs_for_phone(phone_number, days)
    
    # Write to file
    with open(output_file, "w") as f:
        json.dump(logs, f, indent=2)
    
    print(f"Exported {len(logs)} log entries to {output_file}")

def force_cleanup(max_days: int = 30):
    """
    Force cleanup of old log files.
    
    Args:
        max_days: Maximum age of log files in days
    """
    clean_old_logs(max_days)
    print(f"Cleaned up log files older than {max_days} days")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WhatsApp Log Management Utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List phone numbers with logs")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get logs for a phone number")
    get_parser.add_argument("phone", help="Phone number to get logs for")
    get_parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search logs for a query")
    search_parser.add_argument("query", help="Text to search for")
    search_parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export logs for a phone number")
    export_parser.add_argument("phone", help="Phone number to export logs for")
    export_parser.add_argument("output", help="Output file path")
    export_parser.add_argument("--days", type=int, default=30, help="Number of days to look back")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Force cleanup of old log files")
    cleanup_parser.add_argument("--days", type=int, default=30, help="Maximum age of log files in days")
    
    args = parser.parse_args()
    
    if args.command == "list":
        phones = list_phone_logs()
        print(f"Found {len(phones)} phone numbers with logs:")
        for phone in phones:
            print(f"- {phone}")
    
    elif args.command == "get":
        logs = get_logs_for_phone(args.phone, args.days)
        print(f"Found {len(logs)} log entries for {args.phone} in the last {args.days} days:")
        for log in logs:
            print(json.dumps(log, indent=2))
    
    elif args.command == "search":
        results = search_logs(args.query, args.days)
        print(f"Found matches in logs for {len(results)} phone numbers:")
        for phone, logs in results.items():
            print(f"- {phone}: {len(logs)} matches")
            for log in logs:
                print(f"  {json.dumps(log, indent=2)}")
    
    elif args.command == "export":
        export_logs(args.phone, args.output, args.days)
    
    elif args.command == "cleanup":
        force_cleanup(args.days)
    
    else:
        parser.print_help() 