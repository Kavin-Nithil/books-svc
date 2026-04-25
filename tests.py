import requests
import concurrent.futures
import time
from datetime import datetime

url = "http://localhost:9003/books"

payload = {}
headers = {
    'Accept': 'application/json',
    'Cookie': 'bbc=bsLDxaMQGugXO9uLUeRZ7mpdyxwaf1kx; tenant=devpeibeta'
}


def make_request(request_id):
    """Make a single API request"""
    try:
        start_time = time.time()
        response = requests.request("GET", url, headers=headers, data=payload, timeout=5)
        end_time = time.time()

        return {
            'request_id': request_id,
            'status_code': response.status_code,
            'response_time': end_time - start_time,
            'success': True,
            'response_text': response.text[:200]  # First 200 chars for preview
        }
    except Exception as e:
        return {
            'request_id': request_id,
            'success': False,
            'error': str(e)
        }


def call_api_10_times_in_one_second():
    """Execute 10 API calls within 1 second"""
    print(f"Starting 10 API calls at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    start_total = time.time()

    # Use ThreadPoolExecutor for concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all 10 requests
        futures = [executor.submit(make_request, i) for i in range(10)]

        # Collect results as they complete
        results = []
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())

    end_total = time.time()
    total_time = end_total - start_total

    # Print results
    print(f"\n{'=' * 60}")
    print(f"Completed in {total_time:.4f} seconds")
    print(f"{'=' * 60}\n")

    # Display individual results
    successful_requests = 0
    for result in results:
        if result['success']:
            successful_requests += 1
            print(f"Request {result['request_id']}: "
                  f"Status {result['status_code']}, "
                  f"Time: {result['response_time']:.4f}s")
            # Optional: print response preview
            # print(f"  Response preview: {result['response_text']}")
        else:
            print(f"Request {result['request_id']}: FAILED - {result['error']}")

    print(f"\n{'=' * 60}")
    print(f"Summary: {successful_requests}/10 requests successful")
    print(f"Total execution time: {total_time:.4f} seconds")

    if total_time > 1.0:
        print(f"⚠️  Warning: Took {total_time:.4f}s, which is > 1 second")
    else:
        print(f"✅ Success: All 10 requests completed within 1 second!")

    return results


# Alternative: Using asyncio for even better performance
import aiohttp
import asyncio


async def make_async_request(session, request_id):
    """Async version of the request"""
    url = "http://localhost:9003/books"
    headers = {
        'Accept': 'application/json',
        'Cookie': 'bbc=bsLDxaMQGugXO9uLUeRZ7mpdyxwaf1kx; tenant=devpeibeta'
    }

    try:
        start_time = time.time()
        async with session.get(url, headers=headers) as response:
            text = await response.text()
            end_time = time.time()

            return {
                'request_id': request_id,
                'status_code': response.status,
                'response_time': end_time - start_time,
                'success': True,
                'response_text': text[:200]
            }
    except Exception as e:
        return {
            'request_id': request_id,
            'success': False,
            'error': str(e)
        }


async def call_api_10_times_async():
    """Async version - most efficient for I/O bound tasks"""
    print(f"\n{'=' * 60}")
    print(f"ASYNC VERSION")
    print(f"Starting 10 API calls at {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
    start_total = time.time()

    async with aiohttp.ClientSession() as session:
        tasks = [make_async_request(session, i) for i in range(10)]
        results = await asyncio.gather(*tasks)

    end_total = time.time()
    total_time = end_total - start_total

    # Display results
    successful_requests = 0
    for result in results:
        if result['success']:
            successful_requests += 1
            print(f"Request {result['request_id']}: "
                  f"Status {result['status_code']}, "
                  f"Time: {result['response_time']:.4f}s")
        else:
            print(f"Request {result['request_id']}: FAILED - {result['error']}")

    print(f"\nSummary: {successful_requests}/10 requests successful")
    print(f"Total execution time: {total_time:.4f} seconds")

    if total_time > 1.0:
        print(f"⚠️  Warning: Took {total_time:.4f}s, which is > 1 second")
    else:
        print(f"✅ Success: All 10 requests completed within 1 second!")

    return results


if __name__ == "__main__":
    # Run threaded version
    print("THREADED VERSION (using ThreadPoolExecutor)")
    threaded_results = call_api_10_times_in_one_second()