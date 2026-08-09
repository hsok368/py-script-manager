"""Example script: Hello World (runs indefinitely, prints every 3 seconds)"""
import time

print("Hello World Bot started!")
count = 0
while True:
    count += 1
    print(f"[{count}] Hello from Python Script Manager — {time.strftime('%H:%M:%S')}")
    time.sleep(3)
