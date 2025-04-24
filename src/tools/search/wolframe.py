from wolframalpha import Client 

from agents import function_tool

from typing import Literal 

from dotenv import load_dotenv, find_dotenv
import os 

_ = load_dotenv(find_dotenv()) # read local.env file 


appid = os.getenv("WOLFRAM_ALPHA_APPID")

client = Client(appid)


WOLFRAME_TOOLS_PROMPT = """ 
Wolfram Alpha 是一个强大的计算知识引擎，能够提供精确的数值计算、事实性数据和专业领域知识。通过 wolframe_query 函数，你可以访问这个引擎的能力，增强你的回答准确性和权威性
你可以使用以下 Wolfram Alpha 工具来获取信息： wolframe_query : 执行 Wolfram Alpha 查询并返回格式化的结果。
## 适用场景
在以下场景中，你应该考虑使用 Wolfram Alpha 工具：

1. 数学计算 ：当用户需要复杂的数学计算、方程求解、积分、微分、线性代数等结果
   
   - 例如："计算 ∫x²sin(x)dx"、"解方程 3x² + 2x - 5 = 0"
2. 科学数据 ：当需要物理常数、化学元素性质、天文数据等科学信息
   
   - 例如："氦的沸点是多少？"、"地球到火星的平均距离"
3. 统计数据 ：当需要最新的人口、GDP、面积等统计数据
   
   - 例如："中国2023年的GDP是多少？"、"世界上人口最多的五个国家"
4. 单位换算 ：当需要在不同单位系统间进行转换
   
   - 例如："50公里等于多少英里？"、"3磅转换为克"
5. 日期和时间计算 ：当需要计算特定日期之间的天数或特定历史事件的时间
   
   - 例如："从2000年1月1日到今天有多少天？"、"下一次日食是什么时候？
   
## 最佳实践
1. 信息查询流程 :
   
   - 首先分析用户问题，确定是否适合使用 Wolfram Alpha 查询
   - 将用户问题转换为简洁明确的查询语句
   - 使用 wolframe_query 执行查询获取结果
   - 根据返回结果，提供给用户准确的信息
2. 查询语句构造 ：构造简洁、明确的查询语句，避免模糊表述
   - 好： wolframe_query("boiling point of mercury")
   - 差： wolframe_query("tell me about mercury")
3. 适当转换用户问题 ：将用户的自然语言问题转换为适合 Wolfram Alpha 的查询格式
   
   - 用户问题："法国的GDP是多少？"
   - 转换为： wolframe_query("GDP of France")
4. 结合上下文 ：在回答中结合 Wolfram Alpha 的结果与你自己的知识
5. 错误处理 ：当 Wolfram Alpha 返回错误或无法提供结果时，使用你自己的知识回答或建议用户重新表述问题
6. 引用来源 ：明确指出数据来自 Wolfram Alpha
7. 语言参数 ：根据用户提问的语言或上下文选择合适的查询语言，通常使用英语可获得最佳结果

## 注意事项
1. 不要对主观问题、伦理问题或政治问题使用 Wolfram Alpha
2. 不要对需要长篇文字解释的问题使用 Wolfram Alpha
3. 当用户明确要求你自己的观点或解释时，不要仅依赖 Wolfram Alpha
4. 对于时效性强的数据（如股票价格、天气），提醒用户数据可能不是实时的
5. 如果 Wolfram Alpha 返回的结果与你的知识有冲突，优先考虑 Wolfram Alpha 的结果，因为它可能包含更新的信息
记住，Wolfram Alpha 是增强你能力的工具，而不是替代你的思考。明智地结合工具结果和你自己的知识，为用户提供最有价值的回答。
"""


def format_wolframe_response(res, error=None):
    """
    格式化 Wolfram Alpha 的响应为 LLM 友好的字符串。
    
    参数:
        res: Wolfram Alpha 的响应对象
        error: 可选的错误信息
        
    返回:
        格式化后的字符串
    """
    if error:
        return f"Wolfram Alpha 查询错误: {error}"
    
    if not hasattr(res, 'pods'):
        input_str = getattr(res, 'inputstring', '未知查询')
        return f"对于查询 {input_str}, Wolfram Alpha 未返回任何结果。"
    
    # 检查是否有 numpods=0 的情况
    if hasattr(res, 'numpods') and int(res.numpods) == 0:
        input_str = getattr(res, 'inputstring', '未知查询')
        return f"对于查询 {input_str}, Wolfram Alpha 未返回任何结果。"
    
    result = []
    max_numpods = 5
    
    # 限制处理的 pod 数量并跳过错误的 pod
    for index, pod in enumerate(res.pods):
        if index >= max_numpods:
            break
            
        # 安全地获取 pod 的 error 属性
        pod_error = getattr(pod, 'error', 'false')
        if pod_error == 'true':
            continue
            
        # 安全地获取 pod 的属性
        pod_title = getattr(pod, 'title', '未知标题')
        pod_scanner = getattr(pod, 'scanner', '未知扫描器')
        pod_id = getattr(pod, 'id', '未知ID')
        
        # 添加 pod 标题
        result.append(f"# title: {pod_title}")
        result.append(f"Scanner: {pod_scanner}, ID: {pod_id}")
        
        # 安全地处理 subpods
        if hasattr(pod, 'subpods'):
            for subpod in pod.subpods:
                # 安全地获取 subpod 的属性
                subpod_title = getattr(subpod, 'title', '')
                if subpod_title:
                    result.append(f"## sub_title: {subpod_title}")
                
                # 安全地获取 plaintext，确保不是 None 再调用 strip()
                plaintext = getattr(subpod, 'plaintext', '')
                if plaintext is not None and plaintext.strip():
                    result.append(f"{plaintext}")

                # 安全地处理图片
                if hasattr(subpod, 'img'):
                    img = subpod.img
                    img_title = getattr(img, 'title', 'img_title:')
                    img_alt = getattr(img, 'alt', 'img_descp:')
                    img_src = getattr(img, 'src', '')
                    if img_src:
                        result.append(f"![{img_title} - {img_alt}]({img_src})")

    # 如果没有找到任何有用的信息
    if not result:
        input_str = getattr(res, 'inputstring', '未知查询')
        return f"对于查询 {input_str}, Wolfram Alpha 无法提供有用信息。"
    
    return "\n".join(result)

@function_tool
def wolframe_query(query: str, retries: int = 3) -> str: 
    """
    执行 Wolfram Alpha 查询并返回格式化的结果。
    
    该函数适用于需要获取事实性知识、数学计算、科学数据等场景，可以增强大语言模型的能力。
    特别适合以下场景：
    1. 需要精确数值计算（如复杂数学问题、物理公式求解等）
    2. 需要最新的事实性数据（如国家GDP、人口统计等）
    3. 需要专业领域知识（如化学方程式、物理常数等）
    4. 需要时间相关信息（如天文数据、历史事件等）
    5. 需要单位转换或比较不同量级的数据
    
    使用示例：
    # 查询国家信息
    e.g. query = "countries with the largest child population" 
        return -> " 1 | India | 361.6 million people | 
                    2 | China | 251.9 million people | 
                    3 | Nigeria | 92.37 million people | 
                    4 | Pakistan | 85.48 million people | 
                    5 | Indonesia | 69.74 million people |" 
    
    # 解决数学问题
    e.g. query  = "integrate x^2 sin^3 x dx"
        return -> Indefinite integral : 

    
    # 查询科学数据
    e.g. query = "boiling point of mercury" 
        return -> "629.88 K (356.73 °C, 674.11 °F)"
    ```
    
    参数:
        query: 要查询的问题
        retries: 重试次数，默认为3
        
    返回:
        格式化后的查询结果字符串
    """
    attempt = 0
    last_error = None
    
    while attempt < retries:
        try:
            res = client.query(query)
            return format_wolframe_response(res)
        except Exception as e:
            last_error = str(e)
            attempt += 1
            if attempt >= retries:
                break
    
    return format_wolframe_response(None, error=last_error)
        

                





    



    