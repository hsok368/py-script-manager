"""
Sample Bot Script
=================
Replace this template with your actual bot code.
This demo simulates a bot that processes tasks every 5 seconds.
"""
import time
import random

TASKS = ["Fetching data...", "Processing messages...", "Sending notifications...", "Checking updates..."]

print("=== Sample Bot Started ===")
print("Replace this file with your actual bot script.")
print()

iteration = 0
while True:
    iteration += 1
    task = random.choice(TASKS)
    print(f"[Iteration {iteration}] {task}")
    time.sleep(5)
