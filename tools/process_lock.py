import datetime
import multiprocessing
import time

import portalocker


class ProcessLock:
    INTERVAL_SECONDS = 1

    """Inter-process lock, allowing jobs to be queued"""
    def __init__(self):
        self.first_attempt_time = None
        self.num_intervals = 0
        self.lock = portalocker.BoundedSemaphore(1, 'smarthash')

    def acquire(self) -> None:
        if not self.first_attempt_time:
            self.first_attempt_time = time.time()
            self.num_intervals = 0

        while True:
            try:
                self.lock.acquire(fail_when_locked=True, timeout=0)
                self.first_attempt_time = None
                print(" "*100, end='\r')  # clear the prompt
                return

            except portalocker.AlreadyLocked:
                self.num_intervals += 1
                total_wait_time = self.num_intervals * ProcessLock.INTERVAL_SECONDS

                print(f"Queued for {total_wait_time} seconds...", end='\r')

                sleep_seconds = max(total_wait_time - time.time() + self.first_attempt_time, 0)
                time.sleep(sleep_seconds)

    def release(self) -> None:
        self.lock.release()
