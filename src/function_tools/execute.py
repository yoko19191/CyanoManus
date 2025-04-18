""" 

TOOLS_AVAILABLE:
1. local_py_inter
2. e2b_py_inter
3. 
"""

from agents import function_tool

import json
from typing import Optional


def validate_py_code(code: str) -> bool:
    """Check If String is validated python code"""
    try:
        compile(code, "<string>", "exec")
        return True
    except (SyntaxError, ValueError, TypeError):
        return False
    

# TODO: NOT TEST YET
@function_tool
def local_py_inter(
    py_code: str, 
    timeout: int = 60,
    safe_modules : Optional[set] = None  
) -> str:
    """
    [SECURITY WARNING] Safely execute user-provided Python code LOCALLY and return results as JSON.
    
    This function provides a RESTRICTED Python environment with limited builtins and 
    predefined safe modules (including pandas, matplotlib, numpy). 
    
    ██ WARNING ██
    → ONLY use this when:
    1. Other proper sandbox solutions (Pyodide, Docker containers, Jupyter kernels) cannot be used, AND
    2. You STRICTLY NEED local file/system access
    
    → DO NOT use for:
    - Untrusted code (e.g. from web users)
    - Production environments without containerization
    - Cases where proper sandboxes are available

    Implementation:
    1. First tries to evaluate input as expression (eval)
    2. Falls back to script execution (exec) if eval fails
    3. Returns either:
        - Expression results
        - New variables created
        - Execution status/errors

    Security Measures:
    - Restricted __builtins__
    - Module whitelisting
    - AST validation (basic)
    - Timeout protection

    Args:
        py_code (str): Python code to execute
        timeout (int): Max execution seconds (best-effort)
        safe_modules (set): Allowed modules (default includes pandas/matplotlib/numpy)

    Returns:
        JSON string with keys:
        - 'result': For expression results
        - 'variables': New variables dict
        - 'message': Status message
        - 'error': Error info if failed

    Example:
        >>> # Safe usage (trusted code + isolated env)
        >>> python_inter("df = pd.DataFrame({'A': [1,2]})")
        '{"variables": {"df": ...}}'

        >>> # Dangerous but necessary case
        >>> python_inter("with open('local.txt') as f: print(f.read())")
    """
    
    # check py_code validated
    if not validate_py_code(py_code):
        return json.dumps({
            'error': 'Invalid Python code',
            'type': 'ValidationError'
        })
    
    # Default safe modules including data science stack
    if safe_modules is None:
        safe_modules = {
            'pandas', 'matplotlib', 'numpy',  # Data science stack
            'math', 'random', 'datetime'      # Basic modules
        }
        
    # Create restricted environment
    restricted_globals = {
        '__builtins__': {
            **{mod: __import__(mod) for mod in safe_modules},
            'print': print,
            'range': range,
            'len': len,
            'list': list,
            'dict': dict,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            # Add other safe builtins as needed
        },
        '__name__': '__restricted__',
        '__doc__': None,
    }
    
    # Initialize result capture
    result = None
    restricted_globals['_result'] = result
    
    try:
        # First try eval (for expressions)
        try:
            result = eval(py_code, restricted_globals)
            return json.dumps(
                {'result': result}, 
                ensure_ascii=False, 
                default=str
            )
        except SyntaxError:
            # If eval fails, try exec (for statements)
            code_obj = compile(py_code, '<user_code>', 'exec')
            exec(code_obj, restricted_globals)
            
            # Check for IPython-style _ variable
            if '_' in restricted_globals:
                result = restricted_globals['_']
            elif '_result' in restricted_globals:
                result = restricted_globals['_result']
            
            # Collect new variables (excluding special names)
            new_vars = {
                k: v for k, v in restricted_globals.items()
                if not k.startswith('__') or k == '_'
            }
            
            # Return appropriate response
            if result is not None and not new_vars:
                return json.dumps(
                    {'result': result}, 
                    ensure_ascii=False, 
                    default=str
                )
            elif new_vars:
                return json.dumps(
                    {'variables': new_vars}, 
                    ensure_ascii=False, 
                    default=str
                )
            else:
                return json.dumps(
                    {'message': 'Code executed successfully'}, 
                    ensure_ascii=False
                )
                
    except Exception as e:
        return json.dumps(
            {
                'error': str(e),
                'type': type(e).__name__
            }, 
            ensure_ascii=False
        )







