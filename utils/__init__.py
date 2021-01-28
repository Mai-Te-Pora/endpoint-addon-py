import logging
import os
from typing import List, Optional
from utils.exception import *
import requests
import json

REQUEST_LOGGER = None

REQUEST_CONNECT_TIMEOUT = float(os.getenv("REQUEST_CONNECT_TIMEOUT_SEC")) if os.getenv("REQUEST_CONNECT_TIMEOUT_SEC") else 1.0
REQUEST_READ_TIMEOUT = float(os.getenv("REQUEST_READ_TIMEOUT_SEC")) if os.getenv("REQUEST_READ_TIMEOUT_SEC") else 1.0


def get_request_logger():
    global REQUEST_LOGGER
    if not REQUEST_LOGGER:
        REQUEST_LOGGER = get_file_logger("request")
    return REQUEST_LOGGER


def request_get(path: str, base_uri: str, params: dict = None, retries: int = 3, timeout=(REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT)):
    try:
        response = requests.get(base_uri + path, params=params, timeout=timeout, verify=False, stream=True)
        get_request_logger().debug(f"request done size: {len(response.content)} bytes")
        if not 200 <= response.status_code < 300:
            if response.status_code == 500 and response.content.decode("UTF-8").startswith("Node is catching up"):
                raise NodeIsCatchingUp("Node is catching up")
            elif response.status_code == 500 and response.content.decode("UTF-8").startswith('{"error":"delegation does not exist"}'):
                raise DelegationDoesNotExist("Delegation does not exist.")
            elif response.status_code == 500 and response.content.decode("UTF-8").startswith('{"error":"validator does not exist: '):
                raise ValidatorDoesNotExist("Validator does not exist.")
            else:
                get_request_logger().critical(f"Request {base_uri + path} params: {params}: {response.status_code} - {response.content}")
        return json.loads(response.content)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        if retries > 0:
            get_request_logger().debug(f"Request {base_uri + path} params: {params} timeout. Retry")
            return request_get(path, base_uri, params, retries-1)
        else:
            get_request_logger().debug(f"Request {base_uri + path} params: {params} timeout!!!!")
            raise RequestTimedOut(f"Request {base_uri + path} params: {params} timeout!!!!")


def get_file_logger(name: str,
                    terminal_log_level: Optional[str] = logging.INFO,
                    file_log_level: Optional[str] = logging.INFO):

    path: str = create_sub_dir(["database", "logs"])

    logger = logging.getLogger(name)
    logger.setLevel(terminal_log_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(terminal_log_level)

    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # add formatter to ch
    stream_handler.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(f"{path}/{name}.log")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_log_level)
    logger.addHandler(file_handler)

    return logger


def create_sub_dir(path_parts: List[str]):
    path: str = ""
    for sub_dir in path_parts:
        path = os.path.join(path, sub_dir)
        if not os.path.isdir(path):
            os.mkdir(path)
    return os.path.abspath(os.path.join(*path_parts))


def load_files(path: str, extension: Optional[str] = ".json"):
    if not os.path.isdir(path):
        raise NotADirectoryError(f"Directory not found: {path}")

    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    for filename in files:
        if extension and filename.endswith(filename):
            with open(filename, "r") as file:
                yield file.read()


def save_file(path: str, name: str, content: str):
    if os.path.isdir(path):
        path: str = os.path.join(path, name)
        with open(path, "w") as file:
            file.write(content)
