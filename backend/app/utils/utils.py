import logging
import time
import os
import traceback
from functools import wraps
from datetime import datetime, timedelta

from pytz import timezone


def getfunc_log_msg(alias: str, request_id: str = ""):
    def log_msg(message: str, level: str = "info"):
        request_bracket = "" if not request_id else f"[{request_id}]"
        full_message = f'[{alias}]{request_bracket} ' + message
        if level == "debug":
            logging.debug(full_message)
        elif level == "info":
            logging.info(full_message)
        elif level == "warning":
            logging.warning(full_message)
        elif level == "error":
            logging.error(full_message)
        elif level == "critical":
            logging.critical(full_message)
    return log_msg

def get_traceback_error_msg(e: Exception):
    error_msg = f"Function failed: {str(e)}"
    tb = traceback.extract_tb(e.__traceback__)
    logging.error(f"[Monitor] {str(tb)}")
    if tb:
        last_frame = tb[-1]
        file_name = last_frame.filename
        relative_file_name = os.path.relpath(file_name, os.getcwd())
        line_number = last_frame.lineno
        error_msg = f"Function failed in {relative_file_name} at line {line_number}: {str(e)}"
    return error_msg
    

# Wrappers
def timer_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time-start_time
        logging.warning(f"[Monitor] Function {func.__name__} took: {elapsed_time}s to execute")
        return result
    return wrapper

def debug_decorator(sleep: int = 0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.warning(f"[Monitor] Execute function {func.__name__} with args: {args}, kwargs: {kwargs}")
            result = func(*args, **kwargs)
            logging.warning(f"[Monitor] Function {func.__name__} returned: {result}")
            time.sleep(sleep)
            return result
        return wrapper
    return decorator

def retry_decorator(max_retries: int, sleep: int = 0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            error = ""
            for i in range(1, max_retries+2):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error = e
                    if (i < max_retries+1):
                        logging.warning(f"[Monitor] Function {func.__name__} failed: {e}, retry #{i} in {sleep}s")
                        time.sleep(sleep)
            raise error
        return wrapper
    return decorator

# Time
def get_timestr_utc_hkt(days: int = 0):
    time_format_utc = '%Y-%m-%dT%H:%M:%SZ'
    time_format_hkt = '%Y-%m-%dT%H:%M:%S+08:00'
    utc = timezone('UTC')
    hkt = timezone('Asia/Hong_Kong')

    # start from current UTC time, then subtract days
    now_utc = datetime.now(utc)
    target_utc = now_utc - timedelta(days=days)

    time_str_utc = target_utc.strftime(time_format_utc)
    time_str_hkt = target_utc.astimezone(hkt).strftime(time_format_hkt)

    return time_str_utc, time_str_hkt