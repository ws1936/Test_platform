"""网络连接测试脚本。

用法: python scripts/test_connection.py
"""
import requests


def test_connection(url: str, name: str, timeout: int = 5) -> bool:
    """测试单个 URL 的连接性。"""
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        ok = r.status_code < 400
        icon = "✅" if ok else "⚠️ "
        print(f"{icon} {name:20s} {url:40s} HTTP {r.status_code}")
        return ok
    except requests.exceptions.SSLError as e:
        print(f"⚠️  {name:20s} {url:40s} SSL 错误（本地证书问题）: {str(e)[:60]}")
        return True  # SSL 问题不等于网络不通
    except Exception as e:
        print(f"❌ {name:20s} {url:40s} 失败: {e}")
        return False


def main() -> None:
    """主入口。"""
    print("=" * 70)
    print("网络连接测试")
    print("=" * 70)

    endpoints = [
        ("https://api.github.com", "GitHub API"),
        ("https://pypi.org", "PyPI"),
        ("https://www.baidu.com", "Baidu"),
    ]

    results = [test_connection(url, name) for url, name in endpoints]
    success = sum(1 for r in results if r)
    total = len(results)

    print("=" * 70)
    print(f"结果: {success}/{total} 个端点可达")
    if success > 0:
        print("✅ 网络连接正常")
    else:
        print("❌ 网络连接异常")
    print("=" * 70)


if __name__ == "__main__":
    main()
