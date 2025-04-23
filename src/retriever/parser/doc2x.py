""" 
https://github.com/NoEdgeAI/pdfdeal
installation: pip install --upgrade "pdfdeal[rag]"

example_useage: 
doc2x -k "Your Key Here" -o ./ragtest/input -p --graphrag ./pdf

"""


from pdfdeal import Doc2X

from dotenv import find_dotenv, load_dotenv
import os 
from typing import List, Tuple, Dict, Union, Optional, Any, Literal

_ = load_dotenv(find_dotenv())



doc2x_client = Doc2X(
    api_key=os.getenv("DOC2X_API_KEY"),
    debug=True
)


OutputFormatType = Literal["md_dollar", "md", "tex", "docx", "text", "texts", "detailed"]

def doc2x_pdf2file(
    pdf_file: Union[str, List[str]], 
    output_path: Optional[str] = None, 
    output_format: OutputFormatType = "md_dollar",
    output_name: Optional[str] = None,
    convert: bool = False
) -> Tuple[List[str], List[Dict[str, Any]], bool]:
    """
    将PDF文件转换为指定格式的文件。
    
    Args:
        pdf_file (str | List[str]): 单个PDF文件路径或PDF文件路径列表。
        output_path (str, optional): 输出文件的目录路径。默认为环境变量WORKING_DIR下的parser_output文件夹。
        output_format (OutputFormatType, optional): 期望的输出格式。默认为`md_dollar`。
            支持的格式包括：`md_dollar`|`md`|`tex`|`docx`，将返回文件路径；
            支持的输出变量：`text`|`texts`|`detailed`（分别表示`md格式的字符串`、
            `按页分割的字符串列表`、`按页分割的字符串列表（包含详细页面信息）`）。
        output_name (str, optional): 输出文件名。默认为None。
        convert (bool, optional): 是否将"["和"[["转换为"$"和"$$"，
            仅当`output_format`为变量格式(`text`|`texts`|`detailed`)时有效。默认为False。
    
    Returns:
        Tuple[List[str], List[dict], bool]: 包含以下内容的元组：
            1. 成功转换的文件路径或内容列表。
            2. 包含失败转换错误信息的字典列表。
            3. 布尔值，表示转换过程中是否发生任何错误。
    
    Raises:
        ValueError: 当提供的参数无效时抛出。
        FileNotFoundError: 当PDF文件不存在时抛出。
        Exception: 当转换过程中发生其他错误时抛出。
    """
    try:
        # 设置默认输出路径为WORKING_DIR下的parser_output文件夹
        if output_path is None:
            working_dir = os.getenv("WORKING_DIR", ".")
            output_path = os.path.join(working_dir, "parser_output")
        
        # 验证输入参数
        if not pdf_file:
            raise ValueError("必须提供PDF文件路径")
        
        # 检查PDF文件是否存在
        if isinstance(pdf_file, str):
            if not os.path.exists(pdf_file):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_file}")
        elif isinstance(pdf_file, list):
            for file in pdf_file:
                if not os.path.exists(file):
                    raise FileNotFoundError(f"PDF文件不存在: {file}")
        
        # 确保输出目录存在
        os.makedirs(output_path, exist_ok=True)
        
        # 如果提供了单个output_name，将其转换为列表
        output_names = None
        if output_name is not None:
            if isinstance(pdf_file, list):
                output_names = [output_name] * len(pdf_file)
            else:
                output_names = [output_name]
        
        # 调用Doc2X的pdf2file方法
        success, failed, flag = doc2x_client.pdf2file(
            pdf_file=pdf_file,
            output_names=output_names,
            output_path=output_path,
            output_format=output_format,
            convert=convert
        )
        
        return success, failed, flag
    
    except ValueError as ve:
        print(f"参数错误: {str(ve)}")
        return [], [{"error": str(ve), "file": pdf_file}], True
    
    except FileNotFoundError as fnf:
        print(f"文件未找到: {str(fnf)}")
        return [], [{"error": str(fnf), "file": pdf_file}], True
    
    except Exception as e:
        print(f"转换过程中发生错误: {str(e)}")
        return [], [{"error": str(e), "file": pdf_file}], True
    
    