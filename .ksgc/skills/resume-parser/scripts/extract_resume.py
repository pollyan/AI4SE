#!/usr/bin/env python3
"""
简历内容提取脚本
支持 PDF 和 Word 格式，输出 JSON 格式数据
使用正则表达式进行本地解析
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Education:
    """教育经历"""
    school: str
    degree: str
    major: str
    start_date: str
    end_date: str


@dataclass
class WorkExperience:
    """工作经历"""
    company: str
    position: str
    start_date: str
    end_date: str
    description: str


@dataclass
class ResumeData:
    """简历数据结构"""
    name: str = ""
    gender: str = ""
    age: int = 0
    education: str = ""
    work_years: float = 0.0
    birth_date: str = ""
    education_history: list = None
    work_history: list = None
    
    def __post_init__(self):
        if self.education_history is None:
            self.education_history = []
        if self.work_history is None:
            self.work_history = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "姓名": self.name,
            "性别": self.gender,
            "年龄": self.age,
            "学历": self.education,
            "工作年限": self.work_years,
            "出生年月": self.birth_date,
            "教育经历": [
                {
                    "学校": edu.school,
                    "学历": edu.degree,
                    "专业": edu.major,
                    "开始时间": edu.start_date,
                    "结束时间": edu.end_date
                } for edu in self.education_history
            ],
            "工作经历": [
                {
                    "公司": work.company,
                    "职位": work.position,
                    "开始时间": work.start_date,
                    "结束时间": work.end_date,
                    "工作描述": work.description
                } for work in self.work_history
            ]
        }


def extract_text_from_pdf(file_path: str) -> str:
    """从 PDF 提取文本"""
    try:
        import PyPDF2
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except ImportError:
        raise ImportError("请安装 PyPDF2: pip install PyPDF2")


def extract_text_from_word(file_path: str) -> str:
    """从 Word 文档提取文本"""
    try:
        from docx import Document
        doc = Document(file_path)
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    except ImportError:
        raise ImportError("请安装 python-docx: pip install python-docx")


def extract_text(file_path: str) -> str:
    """根据文件类型提取文本"""
    path = Path(file_path)
    suffix = path.suffix.lower()
    
    if suffix == '.pdf':
        return extract_text_from_pdf(file_path)
    elif suffix in ['.docx', '.doc']:
        return extract_text_from_word(file_path)
    elif suffix == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件格式: {suffix}")


def parse_resume_with_regex(text: str) -> ResumeData:
    """使用正则表达式解析简历文本（支持多种格式）"""
    resume = ResumeData()
    
    # 提取姓名（多种格式）
    name_patterns = [
        r'^([^\s\u3000]+)\s+应聘岗位',  # 姓名 应聘岗位
        r'姓名[：:]\s*([^\s\n]+)',       # 姓名：XXX
        r'姓名[：:]\s*([^\n]+)',         # 姓名：XXX（可能包含空格）
        r'^([^\s\n]{2,4})\s*\n',         # 文档开头的姓名
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            resume.name = match.group(1).strip()
            break
    
    # 提取性别
    gender_patterns = [
        r'性别[：:]\s*(\S+)',
        r'性\s*别[：:]\s*(\S+)',
        r'(\s|^)(男|女)(\s|$)',  # 独立的"男"或"女"字
    ]
    for pattern in gender_patterns:
        match = re.search(pattern, text)
        if match:
            # 获取匹配的组
            groups = match.groups()
            gender = None
            for g in groups:
                if g in ['男', '女']:
                    gender = g
                    break
            if gender:
                resume.gender = gender
                break
    
    # 提取年龄
    age_patterns = [
        r'(\d+)\s*岁',
        r'年龄[：:]\s*(\d+)',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                resume.age = int(match.group(1))
                break
            except ValueError:
                continue
    
    # 提取出生年月
    birth_patterns = [
        r'出生年月[：:]\s*(\d{4}\s*年\s*\d{1,2}\s*月)',
        r'出生年月[：:]\s*(\d{4}[-/]\d{1,2})',
        r'(\d{4})\s*年\s*(\d{1,2})\s*月',
    ]
    for pattern in birth_patterns:
        match = re.search(pattern, text)
        if match:
            if len(match.groups()) == 1:
                resume.birth_date = match.group(1).replace(' ', '')
            else:
                year, month = match.groups()
                resume.birth_date = f"{year}年{month}月"
            
            # 计算年龄
            if not resume.age:
                try:
                    birth_year = int(re.search(r'(\d{4})', resume.birth_date).group(1))
                    resume.age = datetime.now().year - birth_year
                except:
                    pass
            break
    
    # 提取学历（多种格式）
    education_patterns = [
        r'(\d{4}\.\d{2})[-~](\d{4}\.\d{2})\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)',  # 2014.09~2018.06 学校 专业 学历
        r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*[-~]\s*(\d{4})\s*年\s*(\d{1,2})\s*月\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)',  # 2014年9月~2018年6月 学校 专业 学历
    ]
    
    for pattern in education_patterns:
        for match in re.finditer(pattern, text):
            try:
                if len(match.groups()) == 5:
                    start_date, end_date = match.group(1), match.group(2)
                    school, major, degree = match.group(3), match.group(4), match.group(5)
                elif len(match.groups()) == 7:
                    start_date = f"{match.group(1)}.{match.group(2)}"
                    end_date = f"{match.group(3)}.{match.group(4)}"
                    school, major, degree = match.group(5), match.group(6), match.group(7)
                else:
                    continue
                
                resume.education = degree  # 使用最高学历
                resume.education_history.append(Education(
                    school=school,
                    degree=degree,
                    major=major,
                    start_date=start_date,
                    end_date=end_date
                ))
            except:
                continue
    
    # 提取工作经历（多种格式）
    # 格式 1: 项目 一(2022.08-至今)（公司名）
    work_pattern_1 = r'项目\s*[一二三四五六七八九十]+\((\d{4}\.\d{2})-([^\)]+)\)（([^）]+)）'
    for match in re.finditer(work_pattern_1, text):
        try:
            company = match.group(3).strip()
            start_date = match.group(1)
            end_date = match.group(2)
            
            # 提取项目名称作为职位
            project_match = re.search(r'项目名称\s*[：:]\s*([^\n]+)', text[match.start():match.start()+1000])
            position = project_match.group(1).strip() if project_match else "开发工程师"
            
            resume.work_history.append(WorkExperience(
                company=company,
                position=position,
                start_date=start_date,
                end_date=end_date,
                description=""
            ))
        except:
            continue
    
    # 格式 2: 工作经历 - 公司名称 - 职位 - 时间
    # 注意：需要排除教育经历（通常包含"学校"、"学院"、"大学"等关键词）
    work_pattern_2 = r'(\d{4}\.\d{2})[-~](\d{4}\.\d{2}|至今|Present)\s+([^\s]+)\s+([^\s]+)'
    for match in re.finditer(work_pattern_2, text):
        try:
            start_date = match.group(1)
            end_date = match.group(2)
            company = match.group(3)
            position = match.group(4)
            
            # 过滤掉教育经历（公司名中包含学校、学院、大学等关键词）
            if any(keyword in company for keyword in ['学校', '学院', '大学', 'School', 'College', 'University']):
                continue
            
            resume.work_history.append(WorkExperience(
                company=company,
                position=position,
                start_date=start_date,
                end_date=end_date,
                description=""
            ))
        except:
            continue
    
    # 计算工作年限（基于工作经历，而非教育经历）
    if resume.work_history:
        try:
            # 过滤掉教育经历
            work_experiences = [
                w for w in resume.work_history 
                if not any(keyword in w.company for keyword in ['学校', '学院', '大学'])
            ]
            
            if work_experiences:
                first_work = min(work_experiences, key=lambda x: x.start_date)
                if first_work.start_date and first_work.start_date != "":
                    start_year = int(first_work.start_date.split('.')[0])
                    work_years = datetime.now().year - start_year
                    resume.work_years = round(work_years, 1)
        except:
            pass
    
    return resume


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python extract_resume.py <简历文件路径>")
        print("支持格式: PDF, DOCX, DOC")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    try:
        print(f"正在提取文件: {file_path}", file=sys.stderr)
        text = extract_text(file_path)
        
        print("正在解析简历内容...", file=sys.stderr)
        resume_data = parse_resume_with_regex(text)
        
        result = resume_data.to_dict()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()