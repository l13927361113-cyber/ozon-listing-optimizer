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

def _part_number(payload, result):
    packet=result.get('fact_packet') or {}
    return str(payload.get('part_number') or packet.get('part_number') or payload.get('model') or '').strip()


def apply_policy(result, payload):
    """Keep the seller's exact warranty; do not append extra legal commentary.

    The product number is inserted only when known. Unverified model fitments
    are never promoted into assertions by this post-processor.
    """
    if not is_part(payload, result):
        return result
    number=_part_number(payload,result)
    table=result.get('compatibility_table') or []
    verified=[]
    for row in table:
        if not isinstance(row,dict):continue
        model=str(row.get('model') or '').strip()
        if model and str(row.get('evidence_level') or '').upper() in ('A','B') and row.get('source_url') and model not in verified:
            verified.append(model)
    ru_before=("Перед покупкой\n\nПеред оформлением заказа убедитесь, что:\n"
       + (f"• Номер детали соответствует заменяемому узлу: {number}.\n" if number else "• Номер детали соответствует заменяемому узлу.\n")
       + "• Модель инструмента указана в списке совместимых моделей.\n"
       + "• Конструкция и технические параметры детали соответствуют заменяемому узлу.\n\n"
       + "При возникновении вопросов по совместимости свяжитесь с продавцом до оформления заказа.")
    zh_before=("购买前\n\n下单前请确认：\n"
       + (f"• 零件号与需要更换的部件一致：{number}。\n" if number else "• 零件号与需要更换的部件一致。\n")
       + "• 机器型号在有资料支持的适配型号列表中。\n"
       + "• 零件结构与技术参数和原部件一致。\n\n"
       + "如对兼容性有疑问，请在下单前联系卖家。")
    for entry in result.get('listings',[]):
        ru=str(entry.get('part3_description_ru') or '')
        zh=str(entry.get('part4_description_zh') or '')
        # Remove old AI-authored warranty and purchase sections, then append the exact templates.
        ru=re.split(r'(?im)^\s*(?:#{1,3}\s*)?(?:Гарантия(?: и условия возврата| продавца)?|Перед покупкой)\s*$',ru,maxsplit=1)[0].strip()
        zh=re.split(r'(?im)^\s*(?:#{1,3}\s*)?(?:[一二三四五六七八九十]+[、.、]\s*)?(?:保修说明|保修与退货条件|卖家保修|购买前)\s*$',zh,maxsplit=1)[0].strip()
        # Remove duplicate standalone legal-rights paragraphs and short AI warranty statements.
        ru='\n'.join(line for line in ru.splitlines() if not re.search(r'(?i)Гарантия продавца|Гарантийный срок|Условия гарантии|не ограничива(?:ет|ют) законные права',line)).strip()
        zh='\n'.join(line for line in zh.splitlines() if not re.search(r'卖家保修|保修期为|法定索赔|上述限制|消费者依法享有|法定退货权',line)).strip()
        entry['part3_description_ru']='\n\n'.join(x for x in (ru,ru_before,WARRANTY_RU) if x)
        entry['part4_description_zh']='\n\n'.join(x for x in (zh,zh_before,WARRANTY_ZH) if x)
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


DESCRIPTION_TARGET_MAX = 5000
DESCRIPTION_HARD_MAX = 6000

def validate_description_lengths(result, target_max=DESCRIPTION_TARGET_MAX, hard_max=DESCRIPTION_HARD_MAX):
    """Validate the final Russian description after fixed policy text is appended.

    Python len() counts Unicode code points, including spaces, punctuation and newlines.
    The platform ceiling is 6,000 characters; allow descriptions up to that limit.
    """
    for index, entry in enumerate(result.get('listings', []), 1):
        description = str(entry.get('part3_description_ru') or '')
        count = len(description)
        if count > hard_max:
            raise ValueError(
                f'第 {index} 个配置的 Part3 俄文简介为 {count} 个字符，超过工具硬性上限 {hard_max}。'
                '请精简重复介绍、重复卖点和重复使用场景后重新导入；不得删除已核实参数、主要适配型号、购买提醒或固定保修条款。'
            )
    return result
