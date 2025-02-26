#!/usr/bin/env python
"""
Utility script to manage chat statuses in the Google Sheet.

Usage:
    python -m app.utils.manage_chat_status list
    python -m app.utils.manage_chat_status set <phone_number> <status>
    python -m app.utils.manage_chat_status clear <phone_number>
    python -m app.utils.manage_chat_status get <phone_number>
"""

import os
import sys
import asyncio
from pathlib import Path
import argparse
from .google_sheets import check_customer_exists, set_chat_status

async def list_chat_statuses():
    """List all customers with their chat statuses"""
    # We need to get all customers from the sheet
    # This is a simplified approach - in a real implementation, 
    # you would want to get all customers from the sheet
    print("Customers with chat statuses:")
    print("-----------------------------")
    print("Phone Number | Chat Status")
    print("-----------------------------")
    
    # This is a placeholder - you would need to implement a function to get all customers
    # For now, we'll just print a message
    print("This feature is not implemented yet. Please check the Google Sheet directly.")

async def set_customer_chat_status(phone_number, status):
    """Set the chat status for a customer"""
    # Check if customer exists
    customer = await check_customer_exists(phone_number)
    if not customer:
        print(f"Error: Customer with phone number {phone_number} not found")
        return False
    
    # Set the chat status
    success = await set_chat_status(phone_number, status)
    if success:
        print(f"Chat status for {phone_number} set to '{status}'")
        return True
    else:
        print(f"Error: Failed to update chat status for {phone_number}")
        return False

async def clear_customer_chat_status(phone_number):
    """Clear the chat status for a customer"""
    return await set_customer_chat_status(phone_number, "")

async def get_customer_chat_status(phone_number):
    """Get the chat status for a customer"""
    # Check if customer exists
    customer = await check_customer_exists(phone_number)
    if not customer:
        print(f"Error: Customer with phone number {phone_number} not found")
        return False
    
    # Print the chat status
    status = customer.get('chat_status', '')
    print(f"Chat status for {phone_number}: '{status}'")
    return True

def main():
    parser = argparse.ArgumentParser(description="Manage chat statuses in the Google Sheet")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all customers with their chat statuses")
    
    # Set command
    set_parser = subparsers.add_parser("set", help="Set the chat status for a customer")
    set_parser.add_argument("phone_number", help="Phone number of the customer")
    set_parser.add_argument("status", help="Status to set (e.g., 'Live Chat')")
    
    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear the chat status for a customer")
    clear_parser.add_argument("phone_number", help="Phone number of the customer")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get the chat status for a customer")
    get_parser.add_argument("phone_number", help="Phone number of the customer")
    
    args = parser.parse_args()
    
    if args.command == "list":
        asyncio.run(list_chat_statuses())
    elif args.command == "set":
        asyncio.run(set_customer_chat_status(args.phone_number, args.status))
    elif args.command == "clear":
        asyncio.run(clear_customer_chat_status(args.phone_number))
    elif args.command == "get":
        asyncio.run(get_customer_chat_status(args.phone_number))
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 