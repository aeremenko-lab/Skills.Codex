"""TicNote API 共享工具：AppKey 前缀 → Base URL / COS 配置路由"""
from dataclasses import dataclass


# ─── AppKey 前缀 → API Base URL ───

APPKEY_PREFIX_MAP = [
    ("tnovs_sit_sk_", "https://ainote-sit-api.mobvoi.com"),
    ("tnovs_sk_",     "https://ainote-api.mobvoi.com"),
    ("tncn_sit_sk_",  "https://voice-api-sit.ticnote.cn"),
    ("tncn_sk_",      "https://voice-api.ticnote.cn"),
]


def resolve_base_url(appkey: str) -> str:
    """根据 AppKey 前缀返回对应的 Base URL。

    Args:
        appkey: TicNote AppKey (如 tncn_sit_sk_xxx, tnovs_sk_xxx)

    Returns:
        对应的 Base URL

    Raises:
        ValueError: AppKey 前缀无法识别
    """
    for prefix, url in APPKEY_PREFIX_MAP:
        if appkey.startswith(prefix):
            return url

    known = ", ".join(p for p, _ in APPKEY_PREFIX_MAP)
    raise ValueError(
        f"无法识别 AppKey 前缀: '{appkey[:20]}...'\n"
        f"已知前缀: {known}"
    )


# ─── AppKey → COS 对象存储配置 ───

@dataclass
class CosConfig:
    """腾讯云 COS 对象存储配置"""
    bucket: str       # Bucket 名称
    region: str       # COS 区域
    cdn: str          # CDN 域名
    env: str          # 上传路径前缀 (ticnote-web-prd / ticnote-web-sit)

    @property
    def bucket_url(self) -> str:
        """COS Bucket 完整域名"""
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com"


# 国内 COS 配置（sit/prd 共用同一个 bucket）
_COS_CN = {
    "bucket": "tc-nj-ticnote-1324023246",
    "region": "ap-nanjing",
    "cdn": "https://cdn.ticnote.cn",
}

# 海外 COS 配置（sit/prd 共用同一个 bucket）
_COS_OVERSEAS = {
    "bucket": "voice-recorder-1308581983",
    "region": "na-siliconvalley",
    "cdn": "https://voice-recorder-cdn.ticnote.com",
}


def resolve_cos_config(appkey: str) -> CosConfig:
    """根据 AppKey 返回完整的 COS 配置。

    判断规则：
    - tncn_* → 国内，tnovs_* → 海外
    - 包含 sit → ticnote-web-sit，否则 → ticnote-web-prd

    Args:
        appkey: TicNote AppKey

    Returns:
        CosConfig 实例
    """
    # 判断国内/海外
    if appkey.startswith("tnovs_"):
        base = _COS_OVERSEAS
    elif appkey.startswith("tncn_"):
        base = _COS_CN
    else:
        raise ValueError(
            f"无法识别 AppKey 区域: '{appkey[:20]}...'\n"
            f"AppKey 应以 tncn_ (国内) 或 tnovs_ (海外) 开头"
        )

    # 判断 sit/prd
    env = "ticnote-web-sit" if "sit" in appkey else "ticnote-web-prd"

    return CosConfig(
        bucket=base["bucket"],
        region=base["region"],
        cdn=base["cdn"],
        env=env,
    )


# ─── 向后兼容 ───

def resolve_cos_env(appkey: str) -> str:
    """根据 AppKey 判断 COS 上传路径的 env 前缀（向后兼容）。"""
    return resolve_cos_config(appkey).env
