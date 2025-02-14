import asyncio
import time
from statistics import mean, median, stdev
import os
from dotenv import load_dotenv
from app.services.openai_service import OpenAIAssistantService

async def run_single_operation(operation_func, *args):
    """Run a single operation and measure its execution time"""
    start_time = time.time()
    try:
        result = await operation_func(*args)
        success = result.status == "success"
    except Exception as e:
        success = False
    duration = time.time() - start_time
    return success, duration

async def run_concurrent_test(operation_name: str, operation_func, concurrent_users: int, *args):
    """Run concurrent tests for a specific operation"""
    print(f"\nTesting {operation_name} with {concurrent_users} concurrent users")
    print("-" * 50)
    
    start_time = time.time()
    tasks = [run_single_operation(operation_func, *args) for _ in range(concurrent_users)]
    results = await asyncio.gather(*tasks)
    total_time = time.time() - start_time
    
    # Analyze results
    successes = [r[0] for r in results]
    durations = [r[1] for r in results]
    
    print("\nResults:")
    print(f"Total time: {total_time:.2f}s")
    print(f"Successful operations: {sum(successes)}/{len(successes)}")
    print("\nTiming Statistics (seconds):")
    print(f"Average: {mean(durations):.2f}")
    print(f"Median: {median(durations):.2f}")
    print(f"Min: {min(durations):.2f}")
    print(f"Max: {max(durations):.2f}")
    if len(durations) > 1:
        print(f"Std Dev: {stdev(durations):.2f}")
    print(f"Requests per second: {concurrent_users/total_time:.2f}")
    
    return total_time, successes, durations

async def main():
    load_dotenv()
    service = OpenAIAssistantService()
    
    # Test configurations
    concurrent_users = [5, 10, 20]  # Test with different numbers of concurrent users
    
    for users in concurrent_users:
        # Test thread creation
        await run_concurrent_test(
            "Thread Creation",
            service.create_thread,
            users
        )
        
        # Optional: Add delay between tests
        await asyncio.sleep(2)
        
        # Example: Test chat with a simple message
        # First create a test thread and assistant for chat tests
        thread_resp = await service.create_thread()
        assistant_config = {
            "name": "Test Assistant",
            "instructions": "You are a test assistant",
            "model": "gpt-4-1106-preview"
        }
        assistant_resp = await service.create_assistant(assistant_config)
        
        if thread_resp.status == "success" and assistant_resp.status == "success":
            # Test chat functionality
            from app.models.assistant_models import ChatRequest, ChatMessage
            chat_request = ChatRequest(
                assistant_id=assistant_resp.assistant_id,
                thread_id=thread_resp.thread_id,
                messages=[ChatMessage(role="user", content="Hello")]
            )
            await run_concurrent_test(
                "Chat Messages",
                service.chat,
                users,
                chat_request
            )

if __name__ == "__main__":
    asyncio.run(main())
