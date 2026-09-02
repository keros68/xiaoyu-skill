"""
多源期刊指标聚合器
数据源：LetPub（IF/最新可得分区/审稿速度/SCI收录）+ OpenAlex（h-index/OA/APC）
使用公开页面和 OpenAlex 获取基础指标
"""
import requests
import time
import json
import os
import re
from typing import Dict, Optional, List

from .journal_index_client import lookup_index_journal
from .letpub_client import lookup_journal

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'assets')
CACHE_FILE = os.path.join(CACHE_DIR, 'journal_cache.json')
CACHE_TTL = 7 * 86400  # 7天
CACHE_SCHEMA_VERSION = 7
XINRUI_API_BASE = 'https://webapi.xr-scholar.com'

KNOWN_STATUS_OVERRIDES = {
    'scienceofthetotalenvironment': {
        'wos_status': 'removed',
        'sci_type': 'WOS_REMOVED',
        'warning': True,
        'status_note': 'Science of the Total Environment 已有 Web of Science/SCIE 移除报道；投稿前务必以 Clarivate Master Journal List 复核。',
    },
}


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get_letpub_info(
    journal_name: str,
    issn: str = None,
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    """从 LetPub 获取期刊详情"""
    try:
        letpub_errors = {}
        detail = lookup_journal(journal_name, issn or '', letpub_errors)
        if letpub_errors and source_errors is not None:
            source_errors['letpub'] = '; '.join(
                f"{source}: {reason}" for source, reason in letpub_errors.items()
            )
        return detail
    except Exception as e:
        print(f"LetPub 查询失败 [{journal_name}]: {e}")
        if source_errors is not None:
            source_errors['letpub'] = str(e)
        return None


def _get_openalex_info(
    journal_name: str,
    issn: str = None,
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    """从 OpenAlex 获取期刊指标"""
    try:
        api_key = os.environ.get('OPENALEX_API_KEY', '').strip()
        if not api_key:
            return None
        # 优先用 ISSN 搜索（更精确）
        if issn:
            url = f"https://api.openalex.org/sources?filter=issn:{issn}&per_page=1"
        else:
            url = f"https://api.openalex.org/sources?search={requests.utils.quote(journal_name)}&per_page=1"

        resp = requests.get(
            url,
            params={'api_key': api_key},
            headers={'User-Agent': 'sci-select/1.0'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get('results', [])
        if not results:
            return None

        source = results[0]
        if not _openalex_source_matches(source, journal_name, issn):
            return None

        stats = source.get('summary_stats', {})

        return {
            'openalex_id': source.get('id', ''),
            'h_index': stats.get('h_index'),
            'i10_index': stats.get('i10_index'),
            '2yr_mean_citedness': round(stats.get('2yr_mean_citedness', 0), 2),
            'cited_by_count': source.get('cited_by_count'),
            'works_count': source.get('works_count'),
            'recent_works_count': sum(
                int(row.get('works_count') or 0)
                for row in source.get('counts_by_year', []) or []
                if int(row.get('year') or 0) >= time.gmtime().tm_year - 4
            ) or None,
            'oa_works_count': source.get('oa_works_count'),
            'is_oa': source.get('is_oa'),
            'is_in_doaj': source.get('is_in_doaj'),
            'host_organization': source.get('host_organization_name', ''),
            'country': source.get('country_code', ''),
            'apc_usd': _extract_apc_usd(source.get('apc_prices', [])),
        }
    except Exception as e:
        print(f"OpenAlex 查询失败 [{journal_name}]: {e}")
        if source_errors is not None:
            source_errors['openalex'] = str(e)
        return None


def _get_xinrui_info(
    journal_name: str,
    issn: str = None,
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    """从新锐分区 API 获取 2026 分区；需要 XINRUI_API_KEY。"""
    api_key = os.environ.get('XINRUI_API_KEY', '').strip()
    if not api_key:
        return None

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    keyword = issn or journal_name
    try:
        search_resp = requests.post(
            f'{XINRUI_API_BASE}/api/journals/search',
            headers=headers,
            json={'keyword': keyword, 'year': 2026},
            timeout=20,
        )
        if search_resp.status_code == 401:
            raise RuntimeError('XinRui API key unauthorized')
        search_resp.raise_for_status()
        candidates = search_resp.json()
        if not candidates:
            return None

        match = _pick_xinrui_match(candidates, journal_name, issn)
        if not match:
            return None

        detail_resp = requests.get(
            f"{XINRUI_API_BASE}/api/journals/{match['jid']}",
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=20,
        )
        detail_resp.raise_for_status()
        detail = detail_resp.json()
        return {
            'xinrui_year': detail.get('year'),
            'xinrui_partition_2026': _format_xinrui_partition(detail),
            'xinrui_researcharea': detail.get('researcharea', []),
            'xinrui_jcrcategory': detail.get('jcrcategory', []),
            'xinrui_on_hold': detail.get('onHold'),
            'xinrui_delist': detail.get('delist'),
            'xinrui_under_review': detail.get('underReview'),
            'xinrui_delist_reason': detail.get('delist_reason', ''),
        }
    except Exception as e:
        print(f"新锐分区查询失败 [{journal_name}]: {e}")
        if source_errors is not None:
            source_errors['xinrui'] = str(e)
        return None


def _extract_apc_usd(apc_prices: list) -> Optional[int]:
    """从 apc_prices 提取 USD 价格"""
    for p in apc_prices:
        if p.get('currency') == 'USD':
            return p.get('price')
    return apc_prices[0].get('price') if apc_prices else None


def _openalex_source_matches(source: Dict, journal_name: str, issn: str = None) -> bool:
    """Return True when an OpenAlex source plausibly matches the requested journal."""
    if issn:
        target_issn = _normalize_issn(issn)
        source_issns = [
            _normalize_issn(value)
            for value in [source.get('issn_l'), *_as_list(source.get('issn'))]
            if value
        ]
        if target_issn and target_issn in source_issns:
            return True

    target_name = _normalize_source_name(journal_name)
    source_names = [
        _normalize_source_name(value)
        for value in [source.get('display_name'), *_as_list(source.get('alternate_titles'))]
        if value
    ]
    return bool(target_name and any(target_name == name for name in source_names))


def _as_list(value) -> List:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _normalize_issn(value: str) -> str:
    return re.sub(r'[^0-9Xx]', '', str(value or '')).upper()


def _normalize_source_name(value: str) -> str:
    text = re.sub(r'^the\b[\s:,-]*', '', str(value or '').lower().strip())
    return re.sub(r'[^a-z0-9]+', '', text)


def _pick_xinrui_match(candidates: List[Dict], journal_name: str, issn: str = None) -> Optional[Dict]:
    normalized_name = _normalize_source_name(journal_name)
    normalized_issn = _normalize_issn(issn or '')
    for candidate in candidates:
        if normalized_issn and normalized_issn in {
            _normalize_issn(candidate.get('issn', '')),
            _normalize_issn(candidate.get('eissn', '')),
        }:
            return candidate
    for candidate in candidates:
        titles = [
            candidate.get('title', ''),
            candidate.get('abbrTitle', ''),
            candidate.get('titleZh', ''),
        ]
        if normalized_name and any(normalized_name == _normalize_source_name(title) for title in titles):
            return candidate
    for candidate in candidates:
        if candidate.get('exactMatch'):
            return candidate
    return candidates[0] if len(candidates) == 1 else None


def _format_xinrui_partition(detail: Dict) -> str:
    areas = detail.get('researcharea') or []
    if not areas:
        return ''
    tiers = []
    for area in areas[:2]:
        tier = area.get('tier')
        if not tier:
            continue
        label = f"{tier}区"
        if area.get('top'):
            label += 'Top'
        tiers.append(label)
    return '；'.join(dict.fromkeys(tiers))


def _apply_known_status_overrides(record: Dict) -> None:
    """Apply time-sensitive status overrides for journals with known WoS changes."""
    override = KNOWN_STATUS_OVERRIDES.get(_normalize_source_name(record.get('name', '')))
    if not override:
        return

    record.update({
        'wos_status': override['wos_status'],
        'sci_type': override['sci_type'],
        'warning': override['warning'],
    })
    notes = record.setdefault('status_notes', [])
    note = override['status_note']
    if note not in notes:
        notes.append(note)


def _has_data_value(value) -> bool:
    return value is not None and value != '' and value != [] and value != {}


def _set_source_status(result: Dict, source: str, status: str, reason: str) -> None:
    """Record source semantics without replacing the legacy source fields."""
    result.setdefault('_source_status', {})[source] = {
        'status': status,
        'reason': reason,
    }


def _cache_record_is_complete(record: Dict) -> bool:
    """Return True only for cache entries that have the core fields they claim."""
    if record.get('_source_errors'):
        return False

    sources = set(record.get('_sources', []))
    if not sources:
        return False

    if 'letpub' in sources:
        required_letpub_fields = (
            'issn',
            'impact_factor',
            'sci_type',
            'xinrui_partition_2026',
        )
        if not all(_has_data_value(record.get(field)) for field in required_letpub_fields):
            return False

    if 'openalex' in sources:
        openalex_fields = (
            'h_index',
            'cited_by_count',
            'works_count',
            'is_oa',
        )
        if not any(_has_data_value(record.get(field)) for field in openalex_fields):
            return False

    if 'letpub' not in sources and 'journal-index' in sources:
        index_fields = (
            'issn',
            'impact_factor',
            'cas_partition_2025',
            'xinrui_partition_2026',
        )
        return any(_has_data_value(record.get(field)) for field in index_fields)

    return True


def get_journal_metrics(
    journal_name: str,
    use_cache: bool = True,
    source_mode: str = "full",
    issn: str = "",
) -> Dict:
    """
    聚合多源期刊公开指标

    Returns:
        {
            'name': 期刊名,
            'shortname': 简称,
            'issn': ISSN,
            # 来自 LetPub
            'impact_factor': 影响因子,
            'partition': 兼容旧字段，默认同 cas_partition_2025,
            'cas_partition_2025': 2025 中科院分区（如 '1区'）,
            'partition_detail': {'大类': ..., '小类': ..., 'Top': ...},
            'sci_type': SCIE/ESCI/无,
            'speed': 审稿速度,
            'accept': 录用比例,
            'warning': 是否预警,
            'publisher_letpub': 出版商(LetPub),
            'field': 研究方向,
            # 来自 OpenAlex
            'h_index': h指数,
            '2yr_mean_citedness': 2年平均被引（类IF）,
            'cited_by_count': 总被引,
            'works_count': 总论文数,
            'is_oa': 是否OA,
            'apc_usd': 文章处理费(USD),
            'publisher_oa': 出版商(OpenAlex),
            # 来自新锐
            'xinrui_partition_2026': 2026 新锐分区,
            # 来源标记
            '_sources': ['letpub', 'openalex'],
        }
    """
    cache = _load_cache()

    # 检查缓存
    if use_cache and journal_name in cache:
        cached = cache[journal_name]
        is_complete = _cache_record_is_complete(cached)
        is_current_schema = cached.get('_cache_schema_version') == CACHE_SCHEMA_VERSION
        source_mode_matches = source_mode != 'full' or 'letpub' in cached.get('_sources', [])
        if is_current_schema and is_complete and source_mode_matches and time.time() - cached.get('_cached_at', 0) < CACHE_TTL:
            _apply_known_status_overrides(cached)
            return cached

    result = {
        'name': journal_name,
        '_sources': [],
        '_source_errors': {},
        '_skipped_sources': [],
        '_source_status': {},
        '_source_mode': source_mode,
        '_cached_at': time.time(),
        '_cache_schema_version': CACHE_SCHEMA_VERSION,
    }
    if issn:
        result['issn'] = issn

    # 1. Optional local/static journal index for stable partition metadata.
    status_errors = {}
    journal_index = _get_journal_index_info(journal_name, issn or None, status_errors)
    if journal_index:
        result = _merge_journal_index_metrics(result, journal_index)
        _set_source_status(result, 'journal-index', 'succeeded', 'matching local/static record')
    elif status_errors.get('journal-index'):
        _set_source_status(result, 'journal-index', 'attempted', status_errors['journal-index'])
    else:
        _set_source_status(result, 'journal-index', 'succeeded', 'no matching local/static record')

    # 2. LetPub. Selection mode skips it when the local index already covers
    # identity, standing, and current partition fields.
    should_query_letpub = source_mode != 'selection' or not _selection_core_available(result)
    if should_query_letpub:
        letpub = _get_letpub_info(journal_name, result.get('issn') or None, status_errors)
        if letpub:
            result = _merge_letpub_metrics(result, letpub)
            if status_errors.get('letpub'):
                _set_source_status(
                    result,
                    'letpub',
                    'partial',
                    f"usable journal detail; {status_errors['letpub']}",
                )
            else:
                _set_source_status(result, 'letpub', 'succeeded', 'usable journal detail')
            time.sleep(1)  # LetPub 请求间隔
        else:
            result['_source_errors']['letpub'] = 'not found or request failed'
            if status_errors.get('letpub'):
                _set_source_status(result, 'letpub', 'attempted', status_errors['letpub'])
            else:
                _set_source_status(result, 'letpub', 'succeeded', 'no matching record')
    else:
        result['_skipped_sources'].append('letpub')
        _set_source_status(result, 'letpub', 'skipped', 'selection core already available from local/static index')

    # 3. OpenAlex（用 ISSN 或名称）
    issn = result.get('issn', '')
    openalex = _get_openalex_info(journal_name, issn if issn else None, status_errors)
    if openalex:
        result.update({
            'h_index': openalex.get('h_index'),
            '2yr_mean_citedness': openalex.get('2yr_mean_citedness'),
            'cited_by_count': openalex.get('cited_by_count'),
            'works_count': openalex.get('works_count'),
            'recent_works_count': openalex.get('recent_works_count'),
            'oa_works_count': openalex.get('oa_works_count'),
            'is_oa': openalex.get('is_oa'),
            'is_in_doaj': openalex.get('is_in_doaj'),
            'apc_usd': openalex.get('apc_usd'),
            'publisher_oa': openalex.get('host_organization', ''),
        })
        result['_sources'].append('openalex')
        _set_source_status(result, 'openalex', 'succeeded', 'usable source-level metrics')
    else:
        result['_source_errors']['openalex'] = (
            'OPENALEX_API_KEY not configured'
            if not os.environ.get('OPENALEX_API_KEY', '').strip()
            else 'not found or request failed'
        )
        if not os.environ.get('OPENALEX_API_KEY', '').strip():
            _set_source_status(result, 'openalex', 'skipped', 'OPENALEX_API_KEY not configured')
        elif status_errors.get('openalex'):
            _set_source_status(result, 'openalex', 'attempted', status_errors['openalex'])
        else:
            _set_source_status(result, 'openalex', 'succeeded', 'no matching source record')

    if not result.get('xinrui_partition_2026'):
        xinrui = _get_xinrui_info(journal_name, issn if issn else None, status_errors)
        if xinrui:
            result.update(xinrui)
            result['_sources'].append('xinrui')
            _set_source_status(result, 'xinrui', 'succeeded', 'usable 2026 XinRui record')
        elif not os.environ.get('XINRUI_API_KEY', '').strip():
            _set_source_status(result, 'xinrui', 'skipped', 'XINRUI_API_KEY not configured')
        elif status_errors.get('xinrui'):
            _set_source_status(result, 'xinrui', 'attempted', status_errors['xinrui'])
        else:
            _set_source_status(result, 'xinrui', 'succeeded', 'no matching record')
    else:
        _set_source_status(result, 'xinrui', 'skipped', 'higher-priority source already supplied 2026 XinRui')

    _apply_known_status_overrides(result)

    # 只缓存完整结果，避免一次临时网络失败污染后续推荐。
    if _cache_record_is_complete(result):
        cache[journal_name] = result
        _save_cache(cache)

    return result


def _selection_core_available(record: Dict) -> bool:
    identity_ok = bool(record.get('issn') or record.get('eissn'))
    coverage_ok = bool(record.get('sci_type'))
    standing_ok = bool(
        record.get('impact_factor')
        or record.get('jcr_quartile')
        or record.get('cas_partition_2025')
        or record.get('xinrui_partition_2026')
    )
    return identity_ok and coverage_ok and standing_ok


def _get_journal_index_info(
    journal_name: str,
    issn: str = None,
    source_errors: Optional[Dict] = None,
) -> Optional[Dict]:
    try:
        return lookup_index_journal(journal_name, issn or '')
    except Exception as e:
        print(f"本地期刊索引查询失败 [{journal_name}]: {e}")
        if source_errors is not None:
            source_errors['journal-index'] = str(e)
        return None


def _merge_journal_index_metrics(result: Dict, index_record: Dict) -> Dict:
    for key in [
        'issn',
        'eissn',
        'impact_factor',
        'if_year',
        'jcr_release_year',
        'jcr_data_year',
        'jcr_quartile',
        'jcr_categories',
        'sci_type',
        'nature_index',
        'nature_index_year',
        'nature_index_articles',
        'nature_index_publication_type',
        'nature_index_source_url',
        'warning',
        'journal_index_tags',
    ]:
        if index_record.get(key) not in (None, '', []):
            result[key] = index_record.get(key)

    _set_partition_field(
        result,
        'cas_partition_2025',
        index_record.get('cas_partition_2025', ''),
        'journal-index',
        prefer_new=True,
    )
    result['partition'] = result.get('cas_partition_2025', result.get('partition', ''))
    _set_partition_field(
        result,
        'xinrui_partition_2026',
        index_record.get('xinrui_partition_2026', ''),
        'journal-index',
        prefer_new=True,
    )
    if 'journal-index' not in result['_sources']:
        result['_sources'].append('journal-index')
    return result


def _merge_letpub_metrics(result: Dict, letpub: Dict) -> Dict:
    cas_partition = _extract_partition(letpub)
    result.update({
        'shortname': letpub.get('shortname', ''),
        'issn': result.get('issn') or letpub.get('issn', ''),
        'impact_factor': result.get('impact_factor') or letpub.get('impact_factor'),
        'letpub_rating': letpub.get('rating'),
        'real_time_if': letpub.get('real_time_if'),
        'five_year_if': letpub.get('five_year_if'),
        'partition_detail': letpub.get('ch_sci_2025'),
        'sci_type': result.get('sci_type') or letpub.get('_sci_type') or letpub.get('sci_type', ''),
        'speed': letpub.get('speed', ''),
        'accept': letpub.get('accept', ''),
        'warning': result.get('warning') or letpub.get('warning', False),
        'publisher_letpub': letpub.get('publisher', ''),
        'field': letpub.get('field', ''),
    })
    _set_partition_field(result, 'cas_partition_2025', cas_partition, 'LetPub', prefer_new=False)
    result['partition'] = result.get('cas_partition_2025', result.get('partition', ''))
    if letpub.get('xinrui_partition_2026'):
        _set_partition_field(
            result,
            'xinrui_partition_2026',
            letpub.get('xinrui_partition_2026'),
            'LetPub',
            prefer_new=False,
        )
        result['xinrui_2026'] = letpub.get('xinrui_2026', {})
    if 'letpub' not in result['_sources']:
        result['_sources'].append('letpub')
    return result


def _set_partition_field(result: Dict, key: str, new_value: str, source: str, prefer_new: bool) -> None:
    if not new_value:
        return
    old_value = result.get(key, '')
    if old_value and old_value != new_value:
        note = f"{key} 分区来源冲突需复核：journal-index/LetPub={old_value}/{new_value}"
        notes = result.setdefault('status_notes', [])
        if note not in notes:
            notes.append(note)
        if not prefer_new:
            return
    result[key] = new_value
    if key == 'cas_partition_2025':
        result['partition'] = new_value


def _extract_partition(letpub_detail: Dict) -> str:
    """从 LetPub 详情提取分区文本"""
    if letpub_detail.get('partition'):
        return letpub_detail.get('partition', '')
    p = letpub_detail.get('ch_sci_2025')
    if isinstance(p, dict):
        return p.get('分区', '')
    elif isinstance(p, str):
        return p
    # fallback: sci_part
    return letpub_detail.get('sci_part', '')


def batch_metrics(journal_names: List[str], delay: float = 1.0) -> Dict[str, Dict]:
    """批量获取期刊指标"""
    results = {}
    unique_names = list(set(journal_names))
    for i, name in enumerate(unique_names):
        metrics = get_journal_metrics(name)
        if metrics.get('_sources'):
            results[name] = metrics
        if i < len(unique_names) - 1:
            time.sleep(delay)
    return results


def format_metrics_line(m: Dict) -> str:
    """一行格式化期刊指标"""
    parts = []

    # 收录类型
    sci = m.get('sci_type', '')
    if m.get('wos_status') == 'removed' or _normalize_source_name(sci) == 'wosremoved':
        parts.append('WoS已移除')
    elif sci:
        s = sci.upper().replace(' ', '')
        if 'SCIE' in s:
            parts.append('SCIE')
        elif 'ESCI' in s:
            parts.append('⚠️ESCI')
        elif 'SSCI' in s:
            parts.append('SSCI')
        elif s != '无':
            parts.append(sci)
        else:
            parts.append('❌非SCI')
    else:
        parts.append('收录未获取')

    # IF
    if m.get('impact_factor'):
        parts.append(f"IF={m['impact_factor']}")
    elif m.get('real_time_if'):
        parts.append(f"实时IF≈{m['real_time_if']}(非JIF)")

    if m.get('nature_index'):
        parts.append(f"NI={m.get('nature_index_year') or '是'}")

    # 分区
    cas_partition = m.get('cas_partition_2025') or m.get('partition', '')
    parts.append(f"2025中科院={cas_partition or '未获取'}")
    xinrui_partition = m.get('xinrui_partition_2026', '')
    parts.append(f"2026新锐={xinrui_partition or '未获取'}")

    # SJR Q分区（如果有的话）
    # h-index
    if m.get('h_index'):
        parts.append(f"h={m['h_index']}")

    # 审稿速度
    if m.get('speed'):
        speed = m['speed'].split('；')[0].replace('网友分享经验：', '').strip()
        if speed and len(speed) < 30:
            parts.append(speed)

    # OA
    if m.get('is_oa') is not None:
        oa_str = 'OA'
        if m.get('apc_usd'):
            oa_str += f"(${m['apc_usd']})"
        parts.append(oa_str if m['is_oa'] else '非OA')

    # 预警
    if m.get('warning'):
        parts.append('⚠️预警')

    return ' | '.join(parts) if parts else '无信息'


if __name__ == '__main__':
    for name in ['Journal of Hydrology', 'Water Resources Research', 'Water']:
        m = get_journal_metrics(name)
        print(f"{name}: {format_metrics_line(m)}")
