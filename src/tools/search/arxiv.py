import logging
import time # time.sleep 不再需要，使用 asyncio.sleep
import os
import re # 用于清理文件名
import asyncio # 用于异步操作和 sleep
#from concurrent.futures import ThreadPoolExecutor # 用于运行同步下载函数
from typing import Literal, List, Dict, Any

from agents import function_tool


import arxiv
# 明确导入需要捕获的异常类型
from arxiv import ArxivError, UnexpectedEmptyPageError, HTTPError

from dotenv import load_dotenv, find_dotenv

# --- 配置和全局变量 ---
# 假设 DEFAULT_MAX_RETRIES 在别处定义或不再需要
# DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 1.5 # 虽然不用作参数，但可能其他地方需要
ARXIV_DOWNLOAD_SUBDIR = "arxiv" # 定义下载子目录

logging.basicConfig(level=logging.INFO) # 调整日志级别以便查看信息
_ = load_dotenv(find_dotenv())
working_dir = os.getenv("WORKING_DIR")

# 确保 client 已初始化
client = arxiv.Client(
    page_size = 20,
    delay_seconds = 5.0,  # 请求之间的延迟
    num_retries = 3       # 客户端内部重试次数
)


# --- 辅助函数 ---

ARXIV_TOOLS_PROMPT = """ 
You have access to the following tools for interacting with the arXiv API:

1.  **arxiv_query(query: str, max_results: int = 10, sort_by: Literal["relevance", "lastUpdatedDate", "submittedDate"] = "relevance") -> str:**
    *   **Purpose:** Searches arXiv for papers matching the given query string.
    *   **Arguments:**
        *   `query` (str): The search query. You can use simple keywords or advanced arXiv query syntax (see ADVANCED_QUERY_SYNTAX_PROMPT for details).
        *   `max_results` (int, optional): The maximum number of results to return. Defaults to 10.
        *   `sort_by` (Literal["relevance", "lastUpdatedDate", "submittedDate"], optional): The sorting criterion for the results. Defaults to "relevance".
    *   **Returns:** A string containing the formatted search results (title, authors, summary, paper ID, PDF URL, etc.) for each found paper, separated by '--------------------', or an error message if the query fails or returns no results.
    *   **Best Practices:**
        *   Use specific keywords and fields (like `ti:`, `au:`, `abs:`) for targeted searches.
        *   Start with a smaller `max_results` unless you need a comprehensive list.
        *   Use `sort_by="lastUpdatedDate"` or `sort_by="submittedDate"` to find the newest papers.
        *   If a query fails, check the error message; it might indicate an issue with the query syntax or the arXiv service.

2.  **arxiv_download(paper_id: str) -> str:**
    *   **Purpose:** Downloads the PDF of a specific arXiv paper identified by its ID.
    *   **Arguments:**
        *   `paper_id` (str): The unique arXiv identifier for the paper (e.g., '2303.16419v1', 'math/0309136v1'). You can usually find this ID in the results from `arxiv_query`.
    *   **Returns:** A string indicating the success or failure of the download. On success, it provides the local filepath where the PDF was saved. On failure, it provides an error message.
    *   **Best Practices:**
        *   Ensure the `paper_id` is correct and includes the version number if applicable (e.g., 'v1', 'v2').
        *   Only call this function after identifying a specific paper of interest, typically using `arxiv_query` first to get the `paper_id`.
        *   The downloaded file will be saved in a pre-configured directory on the system.

**Best Practic Example:**

1.  User asks: "Find recent papers on large language models."
2.  You formulate a query: `arxiv_query(query='abs:"large language model"', sort_by='submittedDate', max_results=5)`
3.  You present the results to the user.
4.  User asks: "Download the paper with ID '2305.12345v1'."
5.  You call: `arxiv_download(paper_id='2305.12345v1')`
6.  You inform the user whether the download was successful and where the file is saved.
"""

ADVANCED_QUERY_SYNTAX_PROMPT = """ 
**Concise Guide: arXiv Advanced Search Syntax**

Use this format for precise arXiv searches:

1.  **Fields:** `field:query`. Key fields:
    * `ti:` (Title)
    * `au:` (Author - e.g., `au:"Last, F"`)
    * `abs:` (Abstract)
    * `cat:` (Category - e.g., `cat:cs.AI`, `cat:hep-th*`)
    * `id:` (arXiv ID)
    * `all:` (All fields - default)

2.  **Operators (UPPERCASE):**
    * `AND`: All terms (default).
    * `OR`: Any term.
    * `ANDNOT`: Exclude term.

3.  **Grouping:** `()` for order/priority.
    * Example: `(ti:X OR abs:X) AND cat:Y`

4.  **Phrases:** `""` for exact match.
    * Example: `abs:"machine learning"`

**Example Query:** Papers by Hinton OR LeCun in cs.LG with "neural network" in abstract:
`(au:Hinton OR au:LeCun) AND cat:cs.LG AND abs:"neural network"`
"""


def get_all_arxiv_tools():
    return [arxiv_query, arxiv_download]


def sanitize_filename(name: str) -> str:
    """
    清理字符串，使其适合用作文件名。
    移除特殊字符，并将空格替换为下划线。
    """
    # 移除或替换 Windows 和 Linux/macOS 不允许的字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # 将连续的空格替换为单个下划线
    name = re.sub(r'\s+', '_', name)
    # 移除可能存在的前导或尾随下划线/空格（清理后）
    name = name.strip('_ ')
    # 可以选择限制文件名长度
    # max_len = 150
    # if len(name) > max_len:
    #     name = name[:max_len]
    return name

async def run_sync_in_executor(func, *args):
    """在 Executor 中异步运行同步阻塞函数，避免阻塞 asyncio 事件循环"""
    loop = asyncio.get_event_loop()
    # 使用默认的 ThreadPoolExecutor
    return await loop.run_in_executor(None, func, *args)

# --- arxiv_query 函数 (保持之前的版本或根据需要修改为 async) ---
@function_tool
def arxiv_query(query: str, max_results: int = 10, sort_by: Literal["relevance", "lastUpdatedDate", "submittedDate"] = "relevance", retries: int = 3, backoff_factor: float = 1.5) -> str:
    """
    使用 arXiv API 查询论文，并处理潜在的错误和重试。 (同步版本)
    ... (之前的 arxiv_query 代码) ...
    """
    # ... (之前的 arxiv_query 代码，注意它仍然是同步的，使用 time.sleep) ...
    # 如果你的应用主要是异步的，建议将此函数也改为 async，使用 asyncio.sleep 和 run_sync_in_executor
    search_params = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=getattr(arxiv.SortCriterion, sort_by.capitalize()) # arxiv 库需要枚举类型
    )

    #results_list: List[Dict[str, Any]] = []
    last_exception: Exception | None = None

    for attempt in range(retries + 1): # +1 因为第一次尝试不算重试
        try:
            # 注意：这里的 list(client.results(...)) 是同步阻塞调用
            # 如果在异步环境中使用此函数，这可能会阻塞事件循环
            results_generator = client.results(search_params)
            fetched_results = list(results_generator) # 将生成器转换为列表以获取所有结果

            if not fetched_results:
                return "ArXiv query returned no results."

            output_lines = []
            for result in fetched_results:
                categories_str = ", ".join(result.categories)
                authors_str = ", ".join(author.name for author in result.authors)
                paper_id = "N/A"
                if result.pdf_url:
                    try:
                        paper_id = result.pdf_url.split('/')[-1].replace('.pdf', '')
                    except Exception as extract_err:
                        logging.warning(f"Could not extract paper_id from pdf_url '{result.pdf_url}': {extract_err}")

                output_lines.append(
                    f"--------------------\n" # 添加换行符
                    f"Title: {result.title}\n"
                    f"Paper ID: {paper_id}\n"
                    f"Authors: {authors_str}\n"
                    f"Published Date: {result.published.strftime('%Y-%m-%d')}\n"
                    f"Categories: {categories_str}\n"
                    f"Summary: {result.summary}\n"
                    f"PDF URL: {result.pdf_url}\n"
                    f"--------------------"
                )
            return "\n".join(output_lines)

        except (HTTPError, UnexpectedEmptyPageError, ArxivError) as e:
            last_exception = e
            logging.warning(f"ArXiv query attempt {attempt + 1}/{retries + 1} failed: {type(e).__name__}: {e}")
            if attempt < retries:
                wait_time = backoff_factor * (2 ** attempt)
                logging.info(f"Retrying query in {wait_time:.2f} seconds...")
                # 这是同步 sleep，会阻塞
                time.sleep(wait_time)
            else:
                logging.error(f"ArXiv query failed after {retries + 1} attempts.")
                return f"ArXiv query failed after {retries} retries. Last error: {type(e).__name__}: {e}"
        except Exception as e:
            logging.exception(f"An unexpected error occurred during ArXiv query: {e}")
            return f"An unexpected error occurred during ArXiv query: {type(e).__name__}: {e}"

    error_msg = f"ArXiv query failed after {retries} retries."
    if last_exception:
        error_msg += f" Last error: {type(last_exception).__name__}: {last_exception}"
    return error_msg


# --- arxiv_download 函数 (异步版本，单次重试) ---
@function_tool # 如果是 agent tool, 取消注释
async def arxiv_download(paper_id: str) -> str:
    """
    根据论文 ID 下载 arXiv 论文 PDF 到指定目录。
    如果首次尝试失败（由于特定网络或 API 错误），会等待 3 秒后重试一次。

    Args:
        paper_id (str): arXiv 论文的唯一标识符 (例如 '2303.16419v1' 或 'math/0309136v1')。

    Returns:
        str: 包含操作结果的消息。
            成功时："Successfully downloaded '{filepath}'"
            失败时："Failed to download paper {paper_id}. Error: {error_type}: {error_message}"
            或 "Working directory not configured."
            或 "Paper with ID {paper_id} not found."
            或 "Failed to download paper {paper_id} after 1 retry. Last error: ..."

    Raises:
        无直接抛出异常，错误信息将包含在返回的字符串中。
        注意：此函数是异步的，需要在 asyncio 事件循环中运行。
    """
    if not working_dir:
        logging.error("Working directory environment variable 'WORKING_DIR' is not set.")
        return "Failed to download: Working directory not configured. Please set the WORKING_DIR environment variable."

    target_dir = os.path.join(working_dir, ARXIV_DOWNLOAD_SUBDIR)
    last_exception: Exception | None = None

    async def attempt_download():
        """封装单次下载尝试的逻辑"""
        # 1. 创建目标目录 (如果不存在)
        # 使用 run_sync_in_executor 运行同步的 os.makedirs，虽然通常很快，但保持一致性
        await run_sync_in_executor(os.makedirs, target_dir, exist_ok=True)

        # 2. 获取论文元数据 (同步调用，放入 executor)
        logging.debug(f"Fetching metadata for paper ID: {paper_id}")
        search = arxiv.Search(id_list=[paper_id])
        # client.results 是同步的，需要放入 executor
        results_iterator = await run_sync_in_executor(client.results, search)
        # next() 也是同步的，理论上也应放入 executor，但通常很快
        # 为简化，这里直接调用，如果遇到问题可以改为 await run_sync_in_executor(next, results_iterator)
        try:
            paper = next(results_iterator) # 获取第一个（也是唯一一个）结果
        except StopIteration:
            # 特殊处理 StopIteration，因为它不是由 run_sync_in_executor 抛出的
            raise StopIteration(f"Paper with ID {paper_id} not found.")


        # 3. 构建文件名
        title_sanitized = sanitize_filename(paper.title)
        primary_category = paper.primary_category or "unknown_category"
        published_date = paper.published.strftime('%Y-%m-%d') if paper.published else "unknown_date"
        paper_id_sanitized = sanitize_filename(paper_id) # 清理 paper_id 以防万一

        final_filename = f"{paper_id_sanitized}_{title_sanitized}_{primary_category}_{published_date}.pdf"
        final_filepath = os.path.join(target_dir, final_filename)

        # 4. 下载 PDF (同步调用，放入 executor)
        logging.info(f"Downloading '{paper.title}' to '{final_filepath}'")
        # paper.download_pdf 是同步的，需要放入 executor
        downloaded_path = await run_sync_in_executor(
            paper.download_pdf,
            dirpath=target_dir,
            filename=final_filename
        )
        logging.info(f"Successfully downloaded '{downloaded_path}'")
        return f"Successfully downloaded '{downloaded_path}'"

    try:
        # 首次尝试
        logging.info(f"Attempting first download for paper ID: {paper_id}")
        return await attempt_download()
    except StopIteration as e: # 捕获上面显式 raise 的 StopIteration
        logging.error(str(e))
        return f"Failed to download: {e}"
    except (HTTPError, UnexpectedEmptyPageError, ArxivError, ConnectionError, TimeoutError) as e:
        last_exception = e
        logging.warning(f"First download attempt failed for {paper_id}: {type(e).__name__}: {e}. Retrying after 3 seconds...")
        await asyncio.sleep(3) # 异步等待 3 秒
        try:
            # 第二次（重试）尝试
            logging.info(f"Attempting second download for paper ID: {paper_id}")
            return await attempt_download()
        except StopIteration as e_retry:
            logging.error(f"Paper with ID {paper_id} not found on arXiv during retry.")
            return f"Failed to download: Paper with ID {paper_id} not found."
        except (HTTPError, UnexpectedEmptyPageError, ArxivError, ConnectionError, TimeoutError, OSError, Exception) as e_retry:
            # 捕获重试时的所有可能错误
            last_exception = e_retry # 更新为重试时的错误
            logging.error(f"Second download attempt failed for {paper_id}: {type(e_retry).__name__}: {e_retry}")
            # 返回最后一次遇到的错误信息
            return f"Failed to download paper {paper_id} after 1 retry. Last error: {type(last_exception).__name__}: {last_exception}"
    except OSError as e:
        # 处理首次尝试时的文件系统错误 (例如权限问题)
        logging.exception(f"File system error during first download attempt for {paper_id}: {e}")
        return f"Failed to download paper {paper_id}. File system error: {e}"
    except Exception as e:
        # 捕获首次尝试时的其他意外错误
        logging.exception(f"An unexpected error occurred during first download attempt for {paper_id}: {e}")
        return f"Failed to download paper {paper_id}. Unexpected error: {type(e).__name__}: {e}"


# --- map_category_id_to_category 函数 ---
def map_category_id_to_category(category_id: str):
    """mapping arxiv category to full category name
    e.g: cs.CL -> Computer Science - Computation and Language

    fore more mapping rule, See [arXiv: Category Taxonomy](https://arxiv.org/category_taxonomy)

    Args:
        category_id (str): the category id of arxiv

    Returns:
        str:  full category name and description
    """
    arxiv_category_map = {
        # 计算机科学（Computer Science）
        "cs": "Computer Science",
        "cs.AI": "Computer Science - Artificial Intelligence",
        "cs.AR": "Computer Science - Hardware Architecture",
        "cs.CC": "Computer Science - Computational Complexity",
        "cs.CE": "Computer Science - Computational Engineering, Finance, and Science",
        "cs.CG": "Computer Science - Computational Geometry",
        "cs.CL": "Computer Science - Computation and Language",
        "cs.CR": "Computer Science - Cryptography and Security",
        "cs.CV": "Computer Science - Computer Vision and Pattern Recognition",
        "cs.DB": "Computer Science - Databases",
        "cs.DC": "Computer Science - Distributed, Parallel, and Cluster Computing",
        "cs.DL": "Computer Science - Digital Libraries",
        "cs.DM": "Computer Science - Discrete Mathematics",
        "cs.DS": "Computer Science - Data Structures and Algorithms",
        "cs.ET": "Computer Science - Emerging Technologies (field needs to explore and advance information processing (computing, communication, sensing) and bio-chemical analysis beyond traditional silicon CMOS technologies, the cs.ET category focuses on researching approaches based on diverse emerging technologies like nanoscale electronics, photonics, and quantum systems.)",
        "cs.FL": "Computer Science - Formal Languages and Automata Theory",
        "cs.GL": "Computer Science - General Literature(Covers introductory material, survey material, predictions of future trends, biographies, and miscellaneous computer-science related material. Roughly includes all of ACM Subject Class A, except it does not include conference proceedings (which will be listed in the appropriate subject area).)",
        "cs.GR": "Computer Science - Graphics",
        "cs.GT": "Computer Science - Computer Science and Game Theory",
        "cs.HC": "Computer Science - Human-Computer Interaction",
        "cs.IR": "Computer Science - Information Retrieval",
        "cs.IT": "Computer Science - Information Theory",
        "cs.LG": "Computer Science - Machine Learning",
        "cs.LO": "Computer Science - Logic in Computer Science",
        "cs.MA": "Computer Science - Multiagent Systems",
        "cs.MM": "Computer Science - Multimedia",
        "cs.MS": "Computer Science - Mathematical Software",
        "cs.NA": "Computer Science - Numerical Analysis",
        "cs.NE": "Computer Science - Neural and Evolutionary Computing",
        "cs.NI": "Computer Science - Networking and Internet Architecture",
        "cs.OH": "Computer Science - Other Computer Science",
        "cs.OS": "Computer Science - Operating Systems",
        "cs.PF": "Computer Science - Performance(Covers performance measurement and evaluation, queueing, and simulation)",
        "cs.PL": "Computer Science - Programming Languages",
        "cs.RO": "Computer Science - Robotics",
        "cs.SC": "Computer Science - Symbolic Computation",
        "cs.SD": "Computer Science - Sound(Covers all aspects of computing with sound, and sound as an information channel. Includes models of sound, analysis and synthesis, audio user interfaces, sonification of data, computer music, and sound signal processing)",
        "cs.SE": "Computer Science - Software Engineering",
        "cs.SI": "Computer Science - Social and Information Networks(covers the design, analysis, and modeling of social and information networks.)",
        "cs.SY": "Computer Science - Systems and Control(covers theoretical and experimental research in automatic control systems.)",
        
        # 经济学(Economics)
        "econ": "Economics",
        "econ.EM": "Economics - Econometrics(Econometric Theory, Micro-Econometrics, Macro-Econometrics, Empirical Content of Economic Relations discovered via New Methods)",
        "econ.GN": "Economics - General Economics(General methodological, applied, and empirical contributions to economics)",
        "econ.TH": "Economics - Theory(Contract Theory, Decision Theory, Game Theory, General Equilibrium, Growth, Learning and Evolution, Macroeconomics, Market and Mechanism Design, and Social Choice.)",
        
        # 电气工程与系统科学(Electrical Engineering and Systems Science)
        "eess": "Electrical Engineering and Systems Science - Top-level category for eess subfields.",
        "eess.AS": "Electrical Engineering and Systems Science - Audio and Speech Processing - Theory and methods for processing and applications of audio, speech, and language signals.",
        "eess.IV": "Electrical Engineering and Systems Science - Image and Video Processing - Theory, algorithms, and architectures for processing and analysis of images, video, and multidimensional signals.",
        "eess.SP": "Electrical Engineering and Systems Science - Signal Processing - Theory, algorithms, and applications of signal and data analysis across various domains.",
        "eess.SY": "Electrical Engineering and Systems Science - Systems and Control - Theoretical and experimental research on automatic control systems, modeling, simulation, and optimization.",
        
        # 数学(Mathmatics)
        "math": "Mathematics - Top-level category for math subfields.",
        "math.AC": "Commutative Algebra - Covers commutative rings, modules, ideals, homological algebra, computational aspects, and connections to algebraic geometry and combinatorics.",
        "math.AG": "Algebraic Geometry - Includes algebraic varieties, stacks, sheaves, schemes, moduli spaces, complex geometry, and quantum cohomology.",
        "math.AP": "Analysis of PDEs - Focuses on existence and uniqueness, boundary conditions, operators, stability, soliton theory, integrable PDEs, and qualitative dynamics.",
        "math.AT": "Algebraic Topology - Deals with homotopy theory, homological algebra, and algebraic treatments of manifolds.",
        "math.CA": "Classical Analysis and ODEs - Includes special functions, orthogonal polynomials, harmonic analysis, ODEs, calculus of variations, approximations, and asymptotics.",
        "math.CO": "Combinatorics - Covers discrete mathematics, graph theory, enumeration, combinatorial optimization, and game theory.",
        "math.CT": "Category Theory - Includes enriched categories, topoi, abelian categories, monoidal categories, and homological algebra.",
        "math.CV": "Complex Variables - Focuses on holomorphic functions, automorphic group actions/forms, pseudoconvexity, complex geometry, and analytic spaces/sheaves.",
        "math.DG": "Differential Geometry - Covers complex, contact, Riemannian, pseudo-Riemannian, Finsler geometry, relativity, gauge theory, and global analysis.",
        "math.DS": "Dynamical Systems - Deals with dynamics of differential equations, flows, mechanics, classical few-body problems, iterations, and complex/delayed dynamics.",
        "math.FA": "Functional Analysis - Includes Banach spaces, function spaces, real functions, integral transforms, distributions, and measure theory.",
        "math.GM": "General Mathematics - Contains mathematical material of general interest or topics not covered in other categories.",
        "math.GN": "General Topology - Covers continuum theory, point-set topology, spaces with algebraic structure, foundations, and dimension theory.",
        "math.GR": "Group Theory - Focuses on finite/topological groups, representation theory, cohomology, classification, and structure.",
        "math.GT": "Geometric Topology - Deals with manifolds, orbifolds, polyhedra, cell complexes, foliations, and geometric structures.",
        "math.HO": "History and Overview - Includes biographies, philosophy/education/communication/ethics of mathematics, and recreational mathematics.",
        "math.IT": "Information Theory - (Alias for cs.IT) Covers theoretical and experimental aspects of information theory and coding.",
        "math.KT": "K-Theory and Homology - Includes algebraic/topological K-theory and relations with topology, commutative algebra, and operator algebras.",
        "math.LO": "Logic - Covers logic, set theory, point-set topology, and formal mathematics.",
        "math.MG": "Metric Geometry - Includes Euclidean, hyperbolic, discrete, convex, coarse geometry, and comparisons in Riemannian geometry and symmetric spaces.",
        "math.MP": "Mathematical Physics - (Alias for math-ph) Focuses on applications of mathematics to physics, mathematical methods for physics, and rigorous formulations of physical theories.",
        "math.NA": "Numerical Analysis - Deals with numerical algorithms for analysis/algebra problems and scientific computation.",
        "math.NT": "Number Theory - Covers prime numbers, diophantine equations, analytic/algebraic number theory, arithmetic geometry, and Galois theory.",
        "math.OA": "Operator Algebras - Includes algebras of operators on Hilbert space, C^*-algebras, von Neumann algebras, and non-commutative geometry.",
        "math.OC": "Optimization and Control - Focuses on operations research, linear programming, control theory, systems theory, optimal control, and game theory.",
        "math.PR": "Probability - Covers theory and applications of probability and stochastic processes.",
        "math.QA": "Quantum Algebra - Includes quantum groups, skein theories, operadic/diagrammatic algebra, and quantum field theory.",
        "math.RA": "Rings and Algebras - Deals with non-commutative/non-associative rings and algebras, universal algebra, lattice theory, and linear algebra.",
        "math.RT": "Representation Theory - Covers linear representations of algebras/groups, Lie theory, and associative/multilinear algebras.",
        "math.SG": "Symplectic Geometry - Focuses on Hamiltonian systems, symplectic flows, and classical integrable systems.",
        "math.SP": "Spectral Theory - Includes Schrodinger operators, operators on manifolds, differential operators, and spectral studies.",
        "math.ST": "Statistics Theory - Covers applied, computational, and theoretical statistics: inference, regression, time series, data analysis, MCMC, design of experiments, and case studies.",
        
        # 天文物理学(Astrophysics)
        "astro-ph": "Astrophysics - Top-level category for astronomy and astrophysics.",
        "astro-ph.CO": "Astrophysics - Cosmology and Nongalactic Astrophysics - Early universe, CMB, large-scale structure, dark matter/energy.",
        "astro-ph.EP": "Astrophysics - Earth and Planetary Astrophysics - Planets, solar system, extrasolar planets, astrobiology.",
        "astro-ph.GA": "Astrophysics - Astrophysics of Galaxies - Galaxies, Milky Way, star clusters, interstellar medium, AGN.",
        "astro-ph.HE": "Astrophysics - High Energy Astrophysical Phenomena - Cosmic rays, gamma/X-rays, supernovae, stellar remnants, black holes.",
        "astro-ph.IM": "Astrophysics - Instrumentation and Methods for Astrophysics - Detectors, telescopes, data analysis, software, laboratory astrophysics.",
        "astro-ph.SR": "Astrophysics - Solar and Stellar Astrophysics - Stars, Sun, stellar evolution, binaries, gravitational radiation from stellar systems.",
        
        # 凝聚态物理(Condensed Matter Physics)
        "cond-mat": "Condensed Matter - Top-level category for condensed matter physics.",
        "cond-mat.dis-nn": "Condensed Matter - Disordered Systems and Neural Networks - Glasses, spin glasses, random/aperiodic systems, localization, neural networks.",
        "cond-mat.mes-hall": "Condensed Matter - Mesoscale and Nanoscale Physics - Semiconducting nanostructures, quantum Hall effect, nanotubes, graphene.",
        "cond-mat.mtrl-sci": "Condensed Matter - Materials Science - Techniques, synthesis, characterization, structure, defects, interfaces.",
        "cond-mat.other": "Condensed Matter - Other Condensed Matter - Work not fitting other cond-mat classifications.",
        "cond-mat.quant-gas": "Condensed Matter - Quantum Gases - Ultracold atoms/molecules, Bose-Einstein condensation, optical lattices, quantum simulation.",
        "cond-mat.soft": "Condensed Matter - Soft Condensed Matter - Membranes, polymers, liquid crystals, glasses, colloids, granular matter.",
        "cond-mat.stat-mech": "Condensed Matter - Statistical Mechanics - Phase transitions, thermodynamics, field theory, non-equilibrium, turbulence.",
        "cond-mat.str-el": "Condensed Matter - Strongly Correlated Electrons - Quantum magnetism, non-Fermi liquids, spin liquids, metal-insulator transitions.",
        "cond-mat.supr-con": "Condensed Matter - Superconductivity - Superconductivity theory, models, experiment, superflow in helium.",
        
        # 广义相对论与量子宇宙学(General Relativity and Quantum Cosmology)
        "gr-qc": "General Relativity and Quantum Cosmology - Gravitational physics, waves, tests of gravity, cosmology, quantum gravity.",
        
        # 高能物理(High Energy Physics)
        "hep-ex": "High Energy Physics - Experiment - Results from high-energy/particle physics experiments, standard model tests, BSM, astroparticle.",
        "hep-lat": "High Energy Physics - Lattice - Lattice field theory, phenomenology, algorithms, hardware.",
        "hep-ph": "High Energy Physics - Phenomenology - Theoretical particle physics related to experiment, predictions, models.",
        "hep-th": "High Energy Physics - Theory - Formal quantum field theory, string theory, supersymmetry, supergravity.",
        
        # 数学物理(Math Physics)
        "math-ph": "Mathematical Physics - Application of mathematics to physics, mathematical methods for physics, rigorous formulations.",

        # 非线性科学(Nonlinear Sciences)
        "nlin": "Nonlinear Sciences - Top-level category for nonlinear physics.",
        "nlin.AO": "Nonlinear Sciences - Adaptation and Self-Organizing Systems - Adaptation, self-organizing systems, statistical physics, stochastic processes.",
        "nlin.CD": "Nonlinear Sciences - Chaotic Dynamics - Dynamical systems, chaos, quantum chaos, turbulence.",
        "nlin.CG": "Nonlinear Sciences - Cellular Automata and Lattice Gases - Computational methods, time series, signal processing, lattice gases.",
        "nlin.PS": "Nonlinear Sciences - Pattern Formation and Solitons - Pattern formation, coherent structures, solitons.",
        "nlin.SI": "Nonlinear Sciences - Exactly Solvable and Integrable Systems - Exactly solvable systems, integrable PDEs/ODEs/maps/lattices/quantum systems.",
        
        # 核科学(Nuclear Science)
        "nucl-ex": "Nuclear Experiment - Results from experimental nuclear physics, fundamental interactions, low/medium/high-energy collisions.",
        "nucl-th": "Nuclear Theory - Theory of nuclear structure, equation of state, nuclear reactions.",
        
        # 物理学(Physics)
        "physics": "Physics - Top-level category for general physics.",
        "physics.acc-ph": "Physics - Accelerator Physics - Accelerator theory, technology, experiments, beam physics, design, applications, radiation sources.",
        "physics.ao-ph": "Physics - Atmospheric and Oceanic Physics - Atmospheric/oceanic physics/chemistry, biogeophysics, climate science.",
        "physics.app-ph": "Physics - Applied Physics - Applications to new technology: devices, optics, materials, nanotechnology, energy.",
        "physics.atm-clus": "Physics - Atomic and Molecular Clusters - Clusters, nanoparticles: properties, spectroscopy, calculations, fragmentation.",
        "physics.atom-ph": "Physics - Atomic Physics - Atomic/molecular structure, spectra, collisions, dynamics, cold atoms/molecules.",
        "physics.bio-ph": "Physics - Biological Physics - Biophysics (molecular, cellular, neuro, membrane, single-molecule, ecological, quantum), modeling, biomechanics, bioinformatics.",
        "physics.chem-ph": "Physics - Chemical Physics - Physics of atoms, molecules, clusters: states, processes, dynamics, spectroscopy, thermodynamics, surfaces.",
        "physics.class-ph": "Physics - Classical Physics - Newtonian/relativistic dynamics, many particle systems, E&M, waves, acoustics, thermodynamics.",
        "physics.comp-ph": "Physics - Computational Physics - All aspects of computational science applied to physics.",
        "physics.data-an": "Physics - Data Analysis, Statistics and Probability - Methods, software, hardware for physics data analysis, statistics, measurement.",
        "physics.ed-ph": "Physics - Physics Education - Research on improving physics teaching and learning.",
        "physics.flu-dyn": "Physics - Fluid Dynamics - Turbulence, instabilities, various flow types, acoustics, complex fluids, mathematical/computational methods, experimental techniques.",
        "physics.gen-ph": "Physics - General Physics - Description coming soon.",
        "physics.geo-ph": "Physics - Geophysics - Atmospheric, hydrospheric, magnetospheric, solid earth geophysics, planetology, space plasma, mineral physics.",
        "physics.hist-ph": "Physics - History and Philosophy of Physics - History and philosophy of physics, astrophysics, cosmology, appreciations.",
        "physics.ins-det": "Physics - Instrumentation and Detectors - Instrumentation and detectors for natural science research, associated electronics and infrastructure.",
        "physics.med-ph": "Physics - Medical Physics - Radiation therapy/dosimetry, biomedical imaging/modeling/analysis, health physics.",
        "physics.optics": "Physics - Optics - Various optics subfields: adaptive, astronomical, atmospheric, biomedical, fiber, Fourier, geometrical, holography, integrated, laser, micro/nano, optical devices/materials/metrology, quantum, ultrafast, X-ray.",
        "physics.plasm-ph": "Physics - Plasma Physics - Fundamental plasma physics, magnetically/inertial confined plasmas, heliophysics, lasers, accelerators, low-temperature plasmas.",
        "physics.pop-ph": "Physics - Popular Physics - Description coming soon.",
        "physics.soc-ph": "Physics - Physics and Society - Structure/dynamics/collective behavior of societies, social/complex networks, physics of infrastructure.",
        "physics.space-ph": "Physics - Space Physics - Space plasma physics, heliophysics, space weather, magnetospheres, auroras, interplanetary space, cosmic rays, radio astronomy.",
        
        # 量子物理(Quantum Physics)
        "quant-ph": "Quantum Physics",
        
        # 定量生物学(Quantitative Biology)
        "q-bio": "Quantitative Biology - Top-level category for biological research using quantitative methods.",
        "q-bio.BM": "Quantitative Biology - Biomolecules - DNA, RNA, proteins, lipids: structure, folding, interactions, single-molecule manipulation.",
        "q-bio.CB": "Quantitative Biology - Cell Behavior - Cell signaling, morphogenesis, apoptosis, host interaction, immunology.",
        "q-bio.GN": "Quantitative Biology - Genomics - DNA sequencing, gene finding, RNA editing, genomic processes, mutations.",
        "q-bio.MN": "Quantitative Biology - Molecular Networks - Gene regulation, signal transduction, proteomics, metabolomics, biological networks.",
        "q-bio.NC": "Quantitative Biology - Neurons and Cognition - Neuronal dynamics, neural networks, sensorimotor control, behavior, cognition.",
        "q-bio.OT": "Quantitative Biology - Other Quantitative Biology - Work not fitting other q-bio classifications.",
        "q-bio.PE": "Quantitative Biology - Populations and Evolution - Population dynamics, spatio-temporal/epidemiological models, evolution, biodiversity, aging, phylogeny.",
        "q-bio.QM": "Quantitative Biology - Quantitative Methods - Experimental, numerical, statistical, mathematical contributions to biology.",
        "q-bio.SC": "Quantitative Biology - Subcellular Processes - Assembly/control of subcellular structures, molecular motors, transport, mitosis/meiosis.",
        "q-bio.TO": "Quantitative Biology - Tissues and Organs - Blood flow, biomechanics, electrical waves, endocrine system, tumor growth in tissues/organs.",
        
        # 定量金融(Quantitative Finance)
        "q-fin": "Quantitative Finance - Top-level category for quantitative methods in finance.",
        "q-fin.CP": "Quantitative Finance - Computational Finance - Computational and numerical methods for financial modeling.",
        "q-fin.EC": "Quantitative Finance - Economics - (Alias for econ.GN) Economic topics outside of finance.",
        "q-fin.GN": "Quantitative Finance - General Finance - Development of general quantitative methodologies for finance applications.",
        "q-fin.MF": "Quantitative Finance - Mathematical Finance - Mathematical and analytical methods for finance.",
        "q-fin.PM": "Quantitative Finance - Portfolio Management - Security selection, optimization, capital allocation, investment strategies, performance measurement.",
        "q-fin.PR": "Quantitative Finance - Pricing of Securities - Valuation and hedging of financial securities, derivatives, and structured products.",
        "q-fin.RM": "Quantitative Finance - Risk Management - Measurement and management of financial risks.",
        "q-fin.ST": "Quantitative Finance - Statistical Finance - Statistical, econometric, and econophysics analyses for financial markets and economic data.",
        "q-fin.TR": "Quantitative Finance - Trading and Market Microstructure - Market microstructure, liquidity, exchange design, automated trading, market-making.",
        
        # 统计学(Statistics)
        "stat": "Statistics - Top-level category for statistical research.",
        "stat.AP": "Statistics - Applications - Statistical applications in various fields like biology, engineering, and social sciences.",
        "stat.CO": "Statistics - Computation - Algorithms, simulation, and visualization methods in statistics.",
        "stat.ME": "Statistics - Methodology - Statistical design, surveys, model selection, multivariate methods, time series, spatial statistics, survival analysis, and non/semiparametrics.",
        "stat.ML": "Statistics - Machine Learning - Machine learning papers with statistical or theoretical foundations.",
        "stat.OT": "Statistics - Other Statistics - Statistical work not fitting into other categories.",
        "stat.TH": "Statistics - Statistics Theory - (Alias for math.ST) Covers asymptotics, Bayesian inference, decision theory, estimation, and testing."
    }
    
    return  arxiv_category_map.get(category_id, "Unknown Category")
    



async def arxiv_extract() -> str:
    """获取一个具体的的论文的详细信息
    """
    
    
    return None