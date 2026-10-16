"""Tolerant extraction of a JSON object from a copied ChatGPT response."""
import html
import json
import re


def parse_chatgpt_json(raw):
    text = html.unescape(raw).strip().lstrip('\ufeff')
    candidates = [text]
    for match in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text, re.I):
        candidates.insert(0, match.group(1).strip())
    decoder = json.JSONDecoder()
    errors = []
    for candidate in candidates:
        for pos, char in enumerate(candidate):
            if char != '{':
                continue
            fragment = candidate[pos:]
            try:
                obj, _ = decoder.raw_decode(fragment)
                if isinstance(obj, dict) and isinstance(obj.get('listings'), list):
                    return obj
            except json.JSONDecodeError as exc:
                errors.append(exc)
            # ChatGPT occasionally escapes periods in plain URLs, which JSON disallows.
            repaired = re.sub(r'\\([.:])', r'\1', fragment)
            if repaired != fragment:
                try:
                    obj, _ = decoder.raw_decode(repaired)
                    if isinstance(obj, dict) and isinstance(obj.get('listings'), list):
                        return obj
                except json.JSONDecodeError as exc:
                    errors.append(exc)
    if errors:
        err = max(errors, key=lambda e: e.pos)
        raise ValueError(f'无法解析 JSON：第 {err.lineno} 行、第 {err.colno} 列：{err.msg}。请确认内容完整。')
    raise ValueError('未找到包含 listings 的完整 JSON 对象，请复制 ChatGPT 的完整生成结果。')


def normalize_tags(tags):
    fixed = []
    for tag in tags:
        tag = str(tag).replace('-', '_')
        tag = re.sub(r'\d{10,}', lambda m: m.group(0)[:9] + '_' + m.group(0)[9:], tag)
        fixed.append(tag)
    return fixed
