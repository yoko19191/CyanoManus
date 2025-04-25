

from typing import Literal
from dotenv import load_dotenv, find_dotenv
import os

_ = load_dotenv(find_dotenv())



def e2b_run_command(
    sandbox_id: str,
    command: str,
    timeout: float = 120
    ):
    """Run a command in a sandboxed environment.

    Args:
        sandbox_id (str): The ID of an existing sandbox, if not provided, a new sandbox will be created.
        command (str): The command to execute in the sandbox environment.
        timeout (float): The lifetime of the sandbox in seconds, 120 seconds by default.

    Returns:
        _type_: _description_
    """
    return None 


def e2b_run_code(
    sandbox_id : str, 
    code : str,
    code_lang : Literal['python', 'javascript'],
    timeout : float
):
    """Run a snippet of Python code in a sandboxed environment.

    Args:
        sandbox_id (str): The ID of an existing sandbox, if not provided, a new sandbox will be created.
        code (str): The code to execute in the sandbox environment, it can be Python or JavaScript.
        code_lang (Literal[&#39;python&#39;, &#39;javascript&#39;]): The language of the code, Python or JavaScript.
        timeout (float): The lifetime of the sandbox in seconds, 120 seconds by default.

    Returns:
        _type_: _description_
    """
    return None


def e2b_upload_files(
    sandbox_id: str, 
    file,
    file_path : str,
    ):
    """Upload a file to a sandboxed environment.

    Args:
        sandbox_id (str): The ID of an existing sandbox.
        file (_type_): The file to upload
        file_path (str): The file to upload

    Returns:
        _type_: _description_
    """

    return None 


def e2b_download_file(
    sandbox_id: str, 
    file_path: str
    ):
    """Download a file from a sandboxed environmen

    Args:
        sandbox_id (str): The ID of an existing sandbox.
        file_path (str): The path of the file to download

    Returns:
        _type_: _description_
    """
    return None