"""Deterministic seller-policy and SEO checks for spare-parts listings."""
import re
from services.import_utils import normalize_tags, invalid_tag_reason

WARRANTY_RU = '''Гарантия и условия возврата

Гарантийный срок — 30 календарных дней с момента получения товара.

Гарантия распространяется на производственные дефекты, обнаруженные при нормальной эксплуатации товара.

Гарантия не распространяется на повреждения, вызванные:
• неправильной установкой;
• перегревом вследствие неправильной эксплуатации;
• попаданием влаги;
• механическими повреждениями;
• использованием не по назначению;
• естественным износом расходных элементов;
• самостоятельным изменением конструкции детали.

Условия возврата и рассмотрения претензий применяются в соответствии с действующим законодательством и правилами торговой площадки.'''
WARRANTY_ZH = '''保修与退货条件

保修期为收到商品之日起30个自然日。

保修适用于商品在正常使用过程中发现的生产制造缺陷。

以下原因造成的损坏不属于卖家保修范围：
• 安装不正确；
• 使用不当引起的过热；
• 进水或受潮；
• 机械损坏；
• 未按预定用途使用；
• 易耗部件自然磨损；
• 擅自改动零件结构。

退货及索赔按照适用法律和平台规则处理。'''

def is_part(payload, result):
    kind = str(payload.get('product_type') or result.get('fact_packet',{}).get('product_type') or '').lower()
    return kind in ('part', '电动工具零件') or ('零件' in kind) or bool(result.get('fact_packet',{}).get('part_number'))

def apply_policy(result, payload):
    """Insert exact policy as separate section, not AI-rewritten warranty."""
    if not is_part(payload,result):
        return result
    for entry in result.get('listings',[]):
        ru = entry.get('part3_description_ru','')
        zh = entry.get('part4_description_zh','')
        # Existing AI warranties may be incomplete. Remove warranty sections only when
        # clearly bounded; otherwise reject ambiguous content instead of duplicating.
        ru = re.sub(r'(?ims)^\s*(?:###?\s*)?(?:Гарантия(?: продавца)?|Гарантия и условия возврата)\s*\n.*?(?=^\s*(?:###?\s*)?(?:Комплектация|Перед покупкой|Рекомендации|Важная информация)\s*$|\Z)', '', ru).strip()
        zh = re.sub(r'(?ims)^\s*(?:[一二三四五六七八九十]+[、.]\s*)?(?:卖家保修|保修说明|保修与退货条件)\s*\n.*?(?=^\s*(?:[一二三四五六七八九十]+[、.]\s*)?(?:包装清单|购买前|注意事项)\s*$|\Z)', '', zh).strip()
        # Standalone warranty sentences may be interspersed; remove only well-defined lines.
        ru = '\n'.join(line for line in ru.split('\n') if not re.match(r'^\s*(?:Гарантия продавца|Гарантийный срок|Условия гарантии)\s*[:—-]',line.strip(),re.I)).strip()
        zh = '\n'.join(line for line in zh.split('\n') if not re.match(r'^\s*(?:卖家保修|保修期|卖家提供自收货)',line.strip())).strip()
        entry['part3_description_ru'] = ru + '\n\n' + WARRANTY_RU
        entry['part4_description_zh'] = zh + '\n\n' + WARRANTY_ZH
    return result

def validate_tags(result, payload):
    for entry in result.get('listings',[]):
        tags = entry.get('part5_hashtags')
        if not isinstance(tags,list) or len(tags)!=30:
            raise ValueError('Part5 必须恰好30个标签')
        tags = normalize_tags(tags, payload.get('part_number') or payload.get('model') or result.get('fact_packet',{}).get('part_number') or '',payload.get('brand') or result.get('fact_packet',{}).get('brand') or '')
        if len(set(t.casefold() for t in tags)) != 30:
            raise ValueError('Part5 出现重复标签，请让 ChatGPT 重新生成30个不同标签')
        for i,tag in enumerate(tags,1):
            reason=invalid_tag_reason(tag)
            if reason:raise ValueError(f'第{i}个标签 {tag}：{reason}')
        entry['part5_hashtags']=tags
    return result
