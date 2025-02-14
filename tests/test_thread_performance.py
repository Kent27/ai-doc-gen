import asyncio
import time
from statistics import mean, median, stdev
import os
from dotenv import load_dotenv
from app.services.openai_service import OpenAIAssistantService

async def measure_thread_creation(iterations: int = 10):
    """Measure thread creation performance over multiple iterations."""
    service = OpenAIAssistantService()
    times = []
    successes = 0
    failures = 0

    print(f"\nStarting performance test for {iterations} iterations...")
    print("-" * 50)

    for i in range(iterations):
        start_time = time.time()
        try:
            response = await service.create_thread()
            end_time = time.time()
            
            if response.status == "success":
                duration = end_time - start_time
                times.append(duration)
                successes += 1
                print(f"Iteration {i+1}: {duration:.2f}s (Thread ID: {response.thread_id})")
            else:
                failures += 1
                print(f"Iteration {i+1}: Failed - {response.message}")
        
        except Exception as e:
            failures += 1
            print(f"Iteration {i+1}: Error - {str(e)}")

    print("\nResults:")
    print("-" * 50)
    print(f"Successful calls: {successes}")
    print(f"Failed calls: {failures}")
    
    if times:
        print("\nTiming Statistics (seconds):")
        print(f"Average: {mean(times):.2f}")
        print(f"Median: {median(times):.2f}")
        print(f"Min: {min(times):.2f}")
        print(f"Max: {max(times):.2f}")
        if len(times) > 1:
            print(f"Std Dev: {stdev(times):.2f}")

async def main():
    # Load environment variables
    load_dotenv()
    
    # Get iterations from environment variable
    iterations = int(os.getenv("TEST_ITERATIONS", "10"))
    
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables")
        return

    # Run the performance test
    await measure_thread_creation(iterations)

if __name__ == "__main__":
    asyncio.run(main())
