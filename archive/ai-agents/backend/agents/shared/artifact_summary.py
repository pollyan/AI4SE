from typing import Dict


ARTIFACT_KEY_NAMES: Dict[str, str] = {
    # Lisa - 测试设计工作流
    "test_design_requirements": "需求分析文档",
    "test_design_strategy": "测试策略蓝图",
    "test_design_cases": "测试用例集",
    "test_design_final": "最终测试设计文档",
    
    # Lisa - 需求评审工作流
    "req_review_record": "需求评审记录",
    "req_review_risk": "风险评估报告",
    "req_review_report": "敏捷需求评审报告",
    
    # Alex - 产品设计工作流
    "product_elevator": "电梯演讲 (价值定位)",
    "product_persona": "用户画像分析",
    "product_journey": "用户旅程地图",
    "product_brd": "业务需求文档 (BRD)",
}


def get_artifacts_summary(artifacts: dict) -> str:
    if not artifacts:
        return "(无)"
    
    summaries = []
    for key, value in artifacts.items():
        name = ARTIFACT_KEY_NAMES.get(key, key)
        length = len(value) if value else 0
        summaries.append(f"- {name}: {length} 字符")
    
    return "\n".join(summaries) if summaries else "(无)"
