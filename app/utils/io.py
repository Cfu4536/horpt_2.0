import json
import os
from typing import Any, Optional, Union


def read_json_file(file_path: str, default: Any = None) -> Optional[Any]:
    """
    读取 JSON 文件并返回解析后的数据。

    参数:
        file_path (str): JSON 文件路径
        default (Any): 读取失败时返回的默认值，默认为 None

    返回:
        Optional[Any]: 解析成功返回数据，失败返回 default 并打印错误信息
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 打开并读取 JSON 文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    except FileNotFoundError as e:
        print(f"[错误] {e}")
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e} (文件: {file_path})")
    except PermissionError as e:
        print(f"[错误] 权限不足，无法读取文件: {e}")
    except Exception as e:
        print(f"[错误] 读取文件时发生未知错误: {e}")

    return default


def write_json_file(file_path: str, data: Any, indent: int = 4, ensure_ascii: bool = False) -> bool:
    """
    将数据写入 JSON 文件。

    参数:
        file_path (str): 目标 JSON 文件路径
        data (Any): 要写入的数据（需可序列化为 JSON）
        indent (int): 缩进空格数，设为 None 则紧凑输出，默认为 4
        ensure_ascii (bool): 是否转义非 ASCII 字符，False 可保留中文等字符，默认为 False

    返回:
        bool: 写入成功返回 True，失败返回 False
    """
    try:
        # 确保目标目录存在（如果路径包含目录）
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            raise FileNotFoundError(f"目标目录不存在: {dir_path}")

        # 写入 JSON 文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        return True

    except TypeError as e:
        print(f"[错误] 数据无法序列化为 JSON: {e} (请检查数据类型是否兼容)")
    except PermissionError as e:
        print(f"[错误] 权限不足，无法写入文件: {e}")
    except OSError as e:
        print(f"[错误] 系统错误，无法写入文件: {e}")
    except Exception as e:
        print(f"[错误] 写入文件时发生未知错误: {e}")

    return False


# ---------- 使用示例 ----------
if __name__ == "__main__":
    # 待写入的数据
    sample_data = {
        "name": "张三",
        "age": 30,
        "skills": ["Python", "JSON", "异常处理"]
    }
    json_file = "sample.json"

    # 写入文件
    success = write_json_file(json_file, sample_data, indent=2)
    if success:
        print(f"[成功] 数据已写入 {json_file}")

    # 读取文件
    read_data = read_json_file(json_file)
    if read_data is not None:
        print("[读取成功] 内容如下:")
        print(read_data)

