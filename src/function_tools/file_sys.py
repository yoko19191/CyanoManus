""" 
CyanoManus File System Tools
A module of tools that allow LLM operate filesystem.

TOOLS_AVAILABLE:
1. read_file: Read file contents
2. read_multiple_files: Read multiple files simultaneously
3. write_file: Create or overwrite file
4. edit_file: Edit file contents
5. create_directory: Create directory
6. list_directory: List directory contents
7. move_file: Move or rename files/directories
8. search_files: Recursively search files/directories
9. get_file_info: Get file/directory metadata
10. list_allowed_directories: List allowed directories for access
"""

from agents import function_tool

import os
import shutil
import fnmatch
import difflib
from pathlib import Path
from typing import List, Dict, Union, Optional, Any, Tuple
from datetime import datetime
import re


############# UTILS FUNCTIONS #############
def normalize_path(path_str: str) -> str:
    """
    Normalize a file path for consistent handling.
    
    Args:
        path_str: The file path to normalize
        
    Returns:
        Normalized path string
    """
    return os.path.normpath(path_str)


def expand_home(path_str: str) -> str:
    """
    Expand the tilde (~) in a path to the user's home directory.
    
    Args:
        path_str: The file path that may contain a tilde
        
    Returns:
        Path with tilde expanded to home directory
    """
    if path_str.startswith('~/') or path_str == '~':
        return os.path.join(os.path.expanduser('~'), path_str[1:] if path_str.startswith('~') else '')
    return path_str


def validate_path(requested_path: str, allowed_directories: List[str]) -> str:
    """
    Validate that a path is within allowed directories.
    
    Args:
        requested_path: The path to validate
        allowed_directories: List of allowed directory paths
        
    Returns:
        The validated absolute path
        
    Raises:
        ValueError: If the path is outside allowed directories
    """
    expanded_path = expand_home(requested_path)
    absolute_path = os.path.abspath(expanded_path)
    normalized_requested = normalize_path(absolute_path)
    
    # Check if path is within allowed directories
    is_allowed = any(normalized_requested.startswith(dir_path) for dir_path in allowed_directories)
    if not is_allowed:
        raise ValueError(f"Access denied - path outside allowed directories: {absolute_path} not in {', '.join(allowed_directories)}")
    
    # Handle symlinks by checking their real path
    try:
        real_path = os.path.realpath(absolute_path)
        normalized_real = normalize_path(real_path)
        is_real_path_allowed = any(normalized_real.startswith(dir_path) for dir_path in allowed_directories)
        if not is_real_path_allowed:
            raise ValueError("Access denied - symlink target outside allowed directories")
        return real_path
    except FileNotFoundError:
        # For new files that don't exist yet, verify parent directory
        parent_dir = os.path.dirname(absolute_path)
        try:
            real_parent_path = os.path.realpath(parent_dir)
            normalized_parent = normalize_path(real_parent_path)
            is_parent_allowed = any(normalized_parent.startswith(dir_path) for dir_path in allowed_directories)
            if not is_parent_allowed:
                raise ValueError("Access denied - parent directory outside allowed directories")
            return absolute_path
        except FileNotFoundError:
            raise ValueError(f"Parent directory does not exist: {parent_dir}")


def normalize_line_endings(text: str) -> str:
    """
    Normalize line endings to \n.
    
    Args:
        text: The text to normalize
        
    Returns:
        Text with normalized line endings
    """
    return text.replace('\r\n', '\n')

############# End of UTILS FUNCTIONS #############


############# Read FILE #############
@function_tool
def read_file(path: str) -> str:
    """
    Read complete contents of a file.
    
    Args:
        path: The path to the file to read
        
    Returns:
        The complete contents of the file with UTF-8 encoding
        
    Raises:
        FileNotFoundError: If the file does not exist
        PermissionError: If the file cannot be read due to permissions
    """
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()
    
############# End of READ FILE #############


############# READ  MULTIPLE FILES  #############

def format_multiple_files_result(results: Dict[str, str]) -> str:
    """
    Format the results of reading multiple files into a LLM-friendly string.
    
    Args:
        results: Dictionary mapping file paths to either their contents or error messages
        
    Returns:
        Formatted string with file contents or error messages
    """
    formatted_output = []
    
    for file_path, content in results.items():
        formatted_output.append(f"File: {file_path}")
        formatted_output.append("-" * 40)
        
        if content.startswith("Error"):
            formatted_output.append(f"[ERROR] {content}")
        else:
            formatted_output.append(content)
        
        formatted_output.append("\n")
    
    return "\n".join(formatted_output)

@function_tool
def read_multiple_files(paths: List[str]) -> str:
    """
    Read multiple files simultaneously.
    
    Args:
        paths: List of file paths to read
        
    Returns:
        Formatted string with file contents or error messages
    """
    results = {}
    
    for file_path in paths:
        try:
            results[file_path] = read_file(file_path)
        except Exception as e:
            results[file_path] = f"Error - {str(e)}"
    
    return format_multiple_files_result(results)

############# End of READ  MULTIPLE FILES  #############


############# WRITE FILE  #############
@function_tool
def write_file(path: str, content: str) -> str:
    """
    Create new file or overwrite existing file with content.
    
    Args:
        path: File location to write to
        content: Content to write to the file
        
    Returns:
        Success message
        
    Raises:
        PermissionError: If the file cannot be written due to permissions
    """
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)
    
    return f"Successfully wrote to {path}"
############# End of WRITE FILE  #############

############# EDIT FILE  #############
def create_unified_diff(original_content: str, new_content: str, filepath: str = 'file') -> str:
    """
    Create a unified diff between original and new content.
    
    Args:
        original_content: Original file content
        new_content: Modified file content
        filepath: Name of the file for the diff header
        
    Returns:
        Unified diff as a string
    """
    # Ensure consistent line endings for diff
    normalized_original = normalize_line_endings(original_content)
    normalized_new = normalize_line_endings(new_content)
    
    # Split content into lines for difflib
    original_lines = normalized_original.splitlines()
    new_lines = normalized_new.splitlines()
    
    # Generate unified diff
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"{filepath} (original)",
        tofile=f"{filepath} (modified)",
        lineterm=''
    )
    
    return '\n'.join(diff)


def apply_file_edits(path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """
    Make selective edits using advanced pattern matching and formatting.
    
    Features:
    - Line-based and multi-line content matching
    - Whitespace normalization with indentation preservation
    - Multiple simultaneous edits with correct positioning
    - Indentation style detection and preservation
    - Git-style diff output with context
    - Preview changes with dry run mode
    
    Args:
        path: File to edit
        edits: List of edit operations, each containing 'oldText' and 'newText'
        dry_run: Preview changes without applying (default: False)
        
    Returns:
        Detailed diff and match information
        
    Raises:
        ValueError: If an edit cannot be applied
        FileNotFoundError: If the file does not exist
    """
    # Read file content and normalize line endings
    with open(path, 'r', encoding='utf-8') as file:
        content = normalize_line_endings(file.read())
    
    # Apply edits sequentially
    modified_content = content
    for edit in edits:
        normalized_old = normalize_line_endings(edit['oldText'])
        normalized_new = normalize_line_endings(edit['newText'])
        
        # If exact match exists, use it
        if normalized_old in modified_content:
            modified_content = modified_content.replace(normalized_old, normalized_new)
            continue
        
        # Otherwise, try line-by-line matching with flexibility for whitespace
        old_lines = normalized_old.split('\n')
        content_lines = modified_content.split('\n')
        match_found = False
        
        for i in range(len(content_lines) - len(old_lines) + 1):
            potential_match = content_lines[i:i + len(old_lines)]
            
            # Compare lines with normalized whitespace
            is_match = all(old_line.strip() == content_line.strip() 
                          for old_line, content_line in zip(old_lines, potential_match))
            
            if is_match:
                # Preserve original indentation of first line
                original_indent_match = re.match(r'^\s*', content_lines[i])
                original_indent = original_indent_match.group(0) if original_indent_match else ''
                
                new_lines = []
                for j, line in enumerate(normalized_new.split('\n')):
                    if j == 0:
                        # For first line, preserve original indentation
                        new_lines.append(original_indent + line.lstrip())
                    else:
                        # For subsequent lines, try to preserve relative indentation
                        if j < len(old_lines):
                            old_indent_match = re.match(r'^\s*', old_lines[j])
                            old_indent = old_indent_match.group(0) if old_indent_match else ''
                            
                            new_indent_match = re.match(r'^\s*', line)
                            new_indent = new_indent_match.group(0) if new_indent_match else ''
                            
                            if old_indent and new_indent:
                                relative_indent = len(new_indent) - len(old_indent)
                                new_lines.append(original_indent + ' ' * max(0, relative_indent) + line.lstrip())
                            else:
                                new_lines.append(line)
                        else:
                            new_lines.append(line)
                
                # Replace the matched lines with the new lines
                content_lines[i:i + len(old_lines)] = new_lines
                modified_content = '\n'.join(content_lines)
                match_found = True
                break
        
        if not match_found:
            raise ValueError(f"Could not find exact match for edit:\n{edit['oldText']}")
    
    # Create unified diff
    diff = create_unified_diff(content, modified_content, path)
    
    # Format diff with appropriate number of backticks
    num_backticks = 3
    while '`' * num_backticks in diff:
        num_backticks += 1
    formatted_diff = f"{'`' * num_backticks}diff\n{diff}{'`' * num_backticks}\n\n"
    
    if not dry_run:
        with open(path, 'w', encoding='utf-8') as file:
            file.write(modified_content)
    
    return formatted_diff

@function_tool
def edit_file(path: str, edits: List[Dict[str, str]], dry_run: bool = False) -> str:
    """
    Make selective edits using advanced pattern matching and formatting.
    
    This is a wrapper around apply_file_edits that provides a simpler interface.
    
    Args:
        path: File to edit
        edits: List of edit operations, each containing 'oldText' and 'newText'
        dry_run: Preview changes without applying (default: False)
        
    Returns:
        Detailed diff and match information
    """
    return apply_file_edits(path, edits, dry_run)
############# End of EDIT FILE  #############


############# CREATE DIRECTORY  #############
@function_tool
def create_directory(path: str) -> str:
    """
    Create new directory or ensure it exists.
    
    Args:
        path: Directory path to create
        
    Returns:
        Success message
        
    Raises:
        PermissionError: If the directory cannot be created due to permissions
    """
    os.makedirs(path, exist_ok=True)
    return f"Successfully created directory {path}"
############# End of CREATE DIRECTORY  #############

############# LIST DIRECTORY  #############
@function_tool
def list_directory(path: str) -> str:
    """
    List directory contents with [FILE] or [DIR] prefixes.
    
    Args:
        path: Directory path to list
        
    Returns:
        Formatted string with directory contents
        
    Raises:
        FileNotFoundError: If the directory does not exist
        NotADirectoryError: If the path is not a directory
    """
    entries = os.listdir(path)
    formatted_entries = []
    
    for entry in entries:
        entry_path = os.path.join(path, entry)
        if os.path.isdir(entry_path):
            formatted_entries.append(f"[DIR] {entry}")
        else:
            formatted_entries.append(f"[FILE] {entry}")
    
    return '\n'.join(formatted_entries)

############# End of LIST DIRECTORY  #############

############# MOVE FILE  #############
@function_tool
def move_file(source: str, destination: str) -> str:
    """
    Move or rename files and directories.
    
    Args:
        source: Source file or directory path
        destination: Destination file or directory path
        
    Returns:
        Success message
        
    Raises:
        FileNotFoundError: If the source does not exist
        FileExistsError: If the destination already exists
    """
    if os.path.exists(destination):
        raise FileExistsError(f"Destination already exists: {destination}")
    
    shutil.move(source, destination)
    return f"Successfully moved {source} to {destination}"
############# End of MOVE FILE  #############

############# SEARCH FILES  #############
def format_search_results(results: List[str]) -> str:
    """
    Format search results into a LLM-friendly string.
    
    Args:
        results: List of file paths found in the search
        
    Returns:
        Formatted string with search results
    """
    if not results:
        return "No files or directories found matching the pattern."
    
    formatted_output = [f"Found {len(results)} matches:"]
    
    for i, path in enumerate(results, 1):
        formatted_output.append(f"{i}. {path}")
    
    return "\n".join(formatted_output)

@function_tool
def search_files(path: str, pattern: str, exclude_patterns: List[str] = None) -> str:
    """
    Recursively search for files/directories.
    
    Args:
        path: Starting directory
        pattern: Search pattern
        exclude_patterns: Exclude any patterns. Glob formats are supported.
        
    Returns:
        Formatted string with search results
        
    Raises:
        FileNotFoundError: If the starting directory does not exist
        NotADirectoryError: If the path is not a directory
    """
    if exclude_patterns is None:
        exclude_patterns = []
    
    results = []
    
    for root, dirs, files in os.walk(path):
        # Check directories
        for dir_name in dirs:
            full_path = os.path.join(root, dir_name)
            relative_path = os.path.relpath(full_path, path)
            
            # Check if path matches any exclude pattern
            should_exclude = any(
                fnmatch.fnmatch(relative_path, pattern if '*' in pattern else f"**/{pattern}/**")
                for pattern in exclude_patterns
            )
            
            if should_exclude:
                continue
                
            if pattern.lower() in dir_name.lower():
                results.append(full_path)
        
        # Check files
        for file_name in files:
            full_path = os.path.join(root, file_name)
            relative_path = os.path.relpath(full_path, path)
            
            # Check if path matches any exclude pattern
            should_exclude = any(
                fnmatch.fnmatch(relative_path, pattern if '*' in pattern else f"**/{pattern}/**")
                for pattern in exclude_patterns
            )
            
            if should_exclude:
                continue
                
            if pattern.lower() in file_name.lower():
                results.append(full_path)
    
    return format_search_results(results)
############# End of SEARCH FILES  #############

############# GET FILES INFO  #############
def format_file_info(info: Dict[str, Any]) -> str:
    """
    Format file information into a LLM-friendly string.
    
    Args:
        info: Dictionary containing file metadata
        
    Returns:
        Formatted string with file information
    """
    formatted_output = [f"File Information:"]
    
    # Format size with appropriate units
    size_bytes = info['size']
    if size_bytes < 1024:
        size_str = f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.2f} KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
    
    formatted_output.append(f"Size: {size_str}")
    
    # Format timestamps
    date_format = "%Y-%m-%d %H:%M:%S"
    formatted_output.append(f"Created: {info['created'].strftime(date_format)}")
    formatted_output.append(f"Modified: {info['modified'].strftime(date_format)}")
    formatted_output.append(f"Accessed: {info['accessed'].strftime(date_format)}")
    
    # Format type and permissions
    file_type = "Directory" if info['isDirectory'] else "File"
    formatted_output.append(f"Type: {file_type}")
    formatted_output.append(f"Permissions: {info['permissions']}")
    
    return "\n".join(formatted_output)

@function_tool
def get_file_info(path: str) -> str:
    """
    Get detailed file/directory metadata.
    
    Args:
        path: Path to file or directory
        
    Returns:
        Formatted string with file information
        
    Raises:
        FileNotFoundError: If the file or directory does not exist
    """
    stats = os.stat(path)
    
    info = {
        'size': stats.st_size,
        'created': datetime.fromtimestamp(stats.st_ctime),
        'modified': datetime.fromtimestamp(stats.st_mtime),
        'accessed': datetime.fromtimestamp(stats.st_atime),
        'isDirectory': os.path.isdir(path),
        'isFile': os.path.isfile(path),
        'permissions': oct(stats.st_mode)[-3:]
    }
    
    return format_file_info(info)
############# End of GET FILES INFO  #############

############# LIST ALLOWED DIRECTORIES  #############
def format_allowed_directories(directories: List[str]) -> str:
    """
    Format the list of allowed directories into a LLM-friendly string.
    
    Args:
        directories: List of allowed directory paths
        
    Returns:
        Formatted string with allowed directories
    """
    if not directories:
        return "No directories are currently allowed for access."
    
    formatted_output = ["Allowed directories:"]
    
    for i, directory in enumerate(directories, 1):
        formatted_output.append(f"{i}. {directory}")
    
    return "\n".join(formatted_output)

@function_tool
def list_allowed_directories(allowed_dirs: List[str] = None) -> str:
    """
    List all directories the server is allowed to access.
    
    Args:
        allowed_dirs: Optional list of allowed directories
        
    Returns:
        Formatted string with allowed directories
    """
    if allowed_dirs is None:
        # If no directories are provided, return an empty list
        # In a real implementation, this might return system-defined allowed directories
        directories = []
    else:
        directories = allowed_dirs
    
    return format_allowed_directories(directories)
############# End of LIST ALLOWED DIRECTORIES  #############