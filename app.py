import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI
import re
from urllib.parse import urlparse
from serpapi import GoogleSearch
from bs4 import BeautifulSoup
import time

# 简单的链接验证函数
def validate_url(url):
    """验证URL是否有效"""
    if not url or url.strip() == "":
        return False, "空链接"
    
    # 检查URL格式
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False, "无效的URL格式"
    except:
        return False, "URL解析失败"
    
    # 检查是否是常见的无效链接模式
    invalid_patterns = [
        r'example\.com',
        r'placeholder\.com',
        r'test\.com',
        r'sample\.com',
        r'news\.cnstock\.com.*202508',  # 您提到的无效链接模式
        r'www\.cs\.com\.cn.*202508'     # 您提到的无效链接模式
    ]
    
    for pattern in invalid_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False, "无效链接模式"
    
    return True, "链接格式有效"

def process_and_validate_result(result):
    """后处理验证API返回结果中的链接"""
    if not result or result.startswith("❌"):
        return result
    
    # 检查是否包含明显的虚假链接模式
    fake_patterns = [
        r'content_\d{6,}\.html?',  # content_123456.html
        r'/\d{10,}\.html?',        # /1234567890.html
        r'0{8,}',                  # 连续8个或更多零
        r'content_\d+\.htm',       # content_数字.htm
        r'/202\d{1}/\d{8,}\.html', # /2025/12345678.html
    ]
    
    contains_fake_link = False
    for pattern in fake_patterns:
        if re.search(pattern, result):
            contains_fake_link = True
            break
    
    if contains_fake_link:
        # 如果检测到虚假链接，替换为警告信息
        warning_msg = """
⚠️ 检测到可能的虚假链接，系统无法提供真实可访问的新闻链接。

可能的原因：
1. 联网搜索功能未正常工作
2. 搜索结果中没有包含有效的新闻链接
3. 当前时间范围内缺少相关新闻

建议：
- 尝试调整关键词或时间范围
- 稍后重试搜索
- 联系技术支持检查联网搜索功能
        """
        
        if st.session_state.language == "en":
            warning_msg = """
⚠️ Detected potentially fake links. The system cannot provide real accessible news links.

Possible reasons:
1. Web search functionality not working properly
2. Search results contain no valid news links
3. Lack of relevant news in current time range

Suggestions:
- Try adjusting keywords or time range
- Retry search later
- Contact technical support to check web search functionality
            """
        
        return warning_msg
    
    return result

# 国际化配置
LANGUAGES = {
    "en": {
        "title": "🔍 Critical Minerals News Analysis System",
        "tab1_title": "📰 News Filtering Analysis",
        "tab2_title": "💬 Custom Prompt",
        "keywords_title": "🔑 Keyword Selection",
        "companies_title": "🏢 Company Selection", 
        "time_title": "⏰ Time Selection",
        "start_analysis": "🚀 Start Analysis",
        "custom_prompt": "💬 Custom Prompt",
        "example_prompts": "📚 Example Prompts",
        "model_selection": "Model Selection",
        "analyze_button": "🔍 Start Analysis",
        "time_options": {
            "2_weeks": "Last 2 Weeks",
            "2_days": "Last 2 Days", 
            "custom": "Custom Time Range"
        },
        "start_date": "Start Date",
        "end_date": "End Date",
        "time_range_info": "📅 Time Range",
        "selected_companies": "Selected Companies",
        "news_analysis": "News Analysis",
        "generated_prompt": "Generated Prompt",
        "analysis_results": "Analysis Results",
        "last_results": "Last Analysis Results",
        "view_last_results": "View Last Results",
        "custom_input": "Custom Input",
        "edit_selected_prompt": "Edit Selected Prompt",
        "input_prompt": "Input Your Prompt",
        "prompt_placeholder": "Enter your prompt here...",
        "help_text": "Select DeepSeek model version",
        "error_no_keywords": "Please select at least one keyword!",
        "error_no_companies": "Please select at least one company!",
        "error_no_prompt": "Please enter prompt content!",
        "analyzing": "Analyzing with API...",
        "step1_analyzing": "🔍 Step 1: Analyzing custom prompt...",
        "step2_converting": "🔄 Step 2: Converting output language according to UI language setting...",
        "language_conversion_prompt": "🔄 Language Conversion Prompt",
        "api_key_expired": "❌ API key expired, please update your DeepSeek API key",
        "api_quota_exceeded": "❌ API quota exceeded, please check your account balance",
        "api_error": "❌ API call error",
        "news_prompt_template": "Please help me find the LATEST and MOST RECENT news about the following keywords and companies in {time_range}:\n\nKeywords: {keywords}\nCompanies: {companies}\n\nCRITICAL TIME REQUIREMENTS:\n1. The time range '{time_range}' refers to the CURRENT DATE and time - NOT historical dates from previous years\n2. If the prompt mentions 'last 24 hours', 'last 2 weeks', etc., calculate this from TODAY'S DATE, not from 2024 or any other past year\n3. ONLY provide news that was published or occurred within the specified time range from TODAY\n4. If no recent news exists in the specified time range, clearly state 'No recent news found in {time_range} (calculated from current date)' instead of providing old information\n5. NEVER reference dates from 2024, 2023, or any previous years unless they are specifically relevant to current developments\n\nPlease provide:\n1. Title, source, and publication time for each news item\n2. Relevance score (0-1, 1 being most relevant) for each news item with selected keywords and companies\n3. Source Link: URL link to the original news article (must be real and accessible)\n4. News summary\n5. News complete content\n6. Sorted by relevance and recency\n\nPlease answer in English with clear formatting and ensure ALL news is from the specified time period calculated from TODAY'S DATE."
    },
    "zh": {
        "title": "🔍 关键矿产新闻分析系统",
        "tab1_title": "📰 新闻筛选分析",
        "tab2_title": "💬 自定义Prompt",
        "keywords_title": "🔑 关键词选择",
        "companies_title": "🏢 公司选择",
        "time_title": "⏰ 时间选择", 
        "start_analysis": "🚀 开始分析",
        "custom_prompt": "💬 自定义Prompt",
        "example_prompts": "📚 示例Prompt",
        "model_selection": "模型选择",
        "analyze_button": "🔍 开始分析",
        "time_options": {
            "2_weeks": "最近2周",
            "2_days": "最近2天",
            "custom": "自定义时间区间"
        },
        "start_date": "开始日期",
        "end_date": "结束日期",
        "time_range_info": "📅 时间范围",
        "selected_companies": "已选公司",
        "news_analysis": "新闻分析",
        "generated_prompt": "生成的Prompt",
        "analysis_results": "分析结果",
        "last_results": "上次分析结果",
        "view_last_results": "查看上次结果",
        "custom_input": "自定义输入",
        "edit_selected_prompt": "编辑选中的Prompt",
        "input_prompt": "输入您的Prompt",
        "prompt_placeholder": "请输入您想要分析的Prompt...",
        "help_text": "选择DeepSeek模型版本",
        "error_no_keywords": "请至少选择一个关键词！",
        "error_no_companies": "请至少选择一个公司！",
        "error_no_prompt": "请输入Prompt内容！",
        "analyzing": "正在调用API分析...",
        "step1_analyzing": "🔍 第一步：正在分析自定义Prompt...",
        "step2_converting": "🔄 第二步：正在根据界面语言要求转换输出语言...",
        "language_conversion_prompt": "🔄 语言转换Prompt",
        "api_key_expired": "❌ API密钥已过期，请更新您的DeepSeek API密钥",
        "api_quota_exceeded": "❌ API配额已用完，请检查您的账户余额",
        "api_error": "❌ API调用错误",
        "news_prompt_template": "请帮我查找{time_range}关于以下关键词和公司的最新新闻：\n\n关键词：{keywords}\n公司：{companies}\n\n关键时间要求：\n1. 时间范围'{time_range}'指的是当前日期和时间 - 不是之前年份的历史日期\n2. 如果提示中提到'最近24小时'、'最近2周'等，请从今天的日期开始计算，而不是从2024年或任何其他过去的年份\n3. 只提供在指定时间范围内（从今天开始计算）发布或发生的新闻\n4. 如果在指定时间范围内没有最新新闻，请明确说明'在{time_range}内未找到最新新闻（从当前日期计算）'，而不是提供旧信息\n5. 除非与当前发展特别相关，否则永远不要引用2024年、2023年或任何之前年份的日期\n\n请提供：\n1. 每条新闻的标题、来源、发布时间\n2. 每条新闻与选中关键词和公司的相关性评分（0-1，1表示最相关）\n3. 来源链接：原始新闻文章的URL链接（必须是真实可访问的链接）\n4. 新闻摘要\n5. 新闻完整内容\n6. 按相关性和时效性排序\n\n请用中文回答，格式要清晰易读，确保所有新闻都来自从当前日期开始计算的指定时间段。"
    }
}

# 中英文关键词映射
KEYWORDS_MAPPING = {
    "en": [
        "Lithium", "Cobalt", "Nickel", "Graphite", "Manganese", "Copper", "Aluminum", "Zinc", "Gallium", "Germanium", 
        "Rare Earth", "Tungsten", "Titanium", "Vanadium", "Antimony", "Beryllium", "Zirconium", "Tantalum", "Niobium",
        "Arsenic", "Barite", "Bismuth", "Cerium", "Cesium", "Chromium", "Dysprosium", "Erbium", "Europium", "Fluorite", 
        "Gadolinium", "Hafnium", "Holmium", "Indium", "Iridium", "Lanthanum", "Lutetium", "Magnesium", "Neodymium", 
        "Palladium", "Platinum", "Praseodymium", "Rhodium", "Rubidium", "Ruthenium", "Samarium", "Scandium", "Tellurium", 
        "Terbium", "Thulium", "Tin", "Ytterbium", "Yttrium", "China-US Critical Minerals", "Geopolitical Competition Critical Minerals",
        "China-Africa Critical Minerals", "EU-China-Africa Geopolitical Competition", "Belt and Road Initiative, China and Africa", 
        "Rare Earth US, China Rare Earth", "Rare Earth China-Africa", "EU-China-Africa Critical Minerals", 
        "Refining Africa and China Critical Minerals", "China-Congo Cobalt Industry"
    ],
    "zh": [
        "锂", "钴", "镍", "石墨", "锰", "铜", "铝", "锌", "镓", "锗", "稀土", "钨", "钛", "钒", "锑", "铍", "锆", "钽", "铌",
        "砷", "重晶石", "铋", "铈", "铯", "铬", "镝", "铒", "铕", "萤石", "钆", "铪", "钬", "铟", "铱", "镧", "镥", "镁", 
        "钕", "钯", "铂", "镨", "铑", "铷", "钌", "钐", "钪", "碲", "铽", "铥", "锡", "镱", "钇", "中美关键矿产", "地缘政治竞争的关键矿产",
        "中非关键矿产", "欧盟、中国、非洲地缘政治竞争", "一带一路倡议,中国和非洲", "稀土美国，中国稀土", "稀土中国-非洲，稀土中非", 
        "欧盟-中国-非洲关键矿产", "提炼非洲和中国的关键矿产", "中国-刚果钴业"
    ]
}

# 中英文公司映射
COMPANIES_MAPPING = {
    "en": {
        "CMOC China Molybdenum / Luoyang Molybdenum Industry": "Luoyang Molybdenum Group",
        "Zijin": "Zijin Mining Group Co., Ltd.",
        "Chengxin Lithium (Chengxin Lithium Group / Chengxin)": "Chengdu Chengxin Lithium Industry Co., Ltd.",
        "Tsingshan Holding group": "Tsingshan Holding Group Co., Ltd.",
        "Huayou Cobalt": "Zhejiang Huayou Cobalt Co., Ltd.",
        "Sinomine Resources Group": "Sinomine Resources Group Co., Ltd.",
        "Sinohydro Corporation": "Sinohydro Corporation",
        "Sichuan Yahua Industrial Group": "Sichuan Yahua Industrial Group Co., Ltd.",
        "Chinalco (Aluminum Corporation of China)": "Aluminum Corporation of China Limited",
        "China Minmetals Corporation": "China Minmetals Corporation",
        "China Hongqiao group": "China Hongqiao Group Limited",
        "China Non Metals Mining Group": "China Nonferrous Metal Mining Group Co., Ltd.",
        "Jiangxi Copper Company": "Jiangxi Copper Co., Ltd.",
        "Baiyin Nonferrous Group (BNMC)": "Baiyin Nonferrous Group Co., Ltd.",
        "Hunan Nonferrous Metals Group": "Hunan Nonferrous Metals Holding Group Co., Ltd.",
        "Tibet Huayu Mining": "Tibet Huayu Mining Co., Ltd.",
        "Ganfeng Lithium": "Ganfeng Lithium Co., Ltd.",
        "Tibet Everest Resources": "Tibet Summit Resources Co., Ltd.",
        "BYD": "BYD Co., Ltd.",
        "Tianqi Lithium": "Tianqi Lithium Corporation",
        "CATL": "Contemporary Amperex Technology Co., Limited"
    },
    "zh": {
        "CMOC China Molybdenum / Luoyang Molybdenum Industry": "洛钼集团",
        "Zijin": "紫金矿业集团股份有限公司",
        "Chengxin Lithium (Chengxin Lithium Group / Chengxin)": "成都成鑫锂业股份有限公司",
        "Tsingshan Holding group": "青山控股集团有限公司",
        "Huayou Cobalt": "浙江华友钴业股份有限公司",
        "Sinomine Resources Group": "中矿资源集团股份有限公司",
        "Sinohydro Corporation": "中国水利水电建设集团公司",
        "Sichuan Yahua Industrial Group": "四川雅化实业集团股份有限公司 (雅化集团)",
        "Chinalco (Aluminum Corporation of China)": "中国铝业集团有限公司 (中国铝业 / 中铝)",
        "China Minmetals Corporation": "中国五矿集团有限公司 (五矿集团)",
        "China Hongqiao group": "中国宏桥集团有限公司",
        "China Non Metals Mining Group": "中国有色矿业集团有限公司",
        "Jiangxi Copper Company": "江西铜业集团有限公司 (江西铜业)",
        "Baiyin Nonferrous Group (BNMC)": "白银有色集团股份有限公司 (白银有色)",
        "Hunan Nonferrous Metals Group": "湖南有色金属控股集团有限公司 (湖南有色)",
        "Tibet Huayu Mining": "西藏华钰矿业股份有限公司 (华钰矿业)",
        "Ganfeng Lithium": "赣丰锂业",
        "Tibet Everest Resources": "西藏珠峰资源股份有限公司",
        "BYD": "比亚迪股份有限公司 (比亚迪)",
        "Tianqi Lithium": "天齐锂业股份有限公司 (天齐锂业)",
        "CATL": "宁德时代新能源科技股份有限公司 (宁德时代)"
    }
}

# 配置页面
st.set_page_config(
    page_title="Critical Minerals News Analysis System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 语言选择器（默认英文）
if 'language' not in st.session_state:
    st.session_state.language = 'en'

# 侧边栏语言切换
with st.sidebar:
    st.header("🌐 Language / 语言")
    selected_language = st.selectbox(
        "Select Language / 选择语言",
        options=[("en", "English"), ("zh", "中文")],
        index=0 if st.session_state.language == 'en' else 1,
        format_func=lambda x: x[1]
    )
    
    if selected_language[0] != st.session_state.language:
        st.session_state.language = selected_language[0]
        st.rerun()
    
    # 初始化历史记录
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    
    # 历史记录管理函数
    def add_to_history(keywords, companies, time_option, result, prompt):
        """添加搜索结果到历史记录"""
        current_date = datetime.now()
        date_str = current_date.strftime('%Y-%m-%d %H:%M')
        
        # 构建标题
        keywords_str = ", ".join(keywords) if keywords else ("无关键词" if st.session_state.language == "zh" else "No Keywords")
        companies_str = ", ".join(companies) if companies else ("无公司" if st.session_state.language == "zh" else "No Companies")
        
        if st.session_state.language == "zh":
            title = f"{date_str} - {keywords_str} - {companies_str}"
        else:
            title = f"{date_str} - {keywords_str} - {companies_str}"
        
        # 创建历史记录项
        history_item = {
            'id': len(st.session_state.search_history),
            'title': title,
            'date': date_str,
            'keywords': keywords,
            'companies': companies,
            'time_option': time_option,
            'result': result,
            'prompt': prompt,
            'language': st.session_state.language
        }
        
        # 添加到历史记录开头
        st.session_state.search_history.insert(0, history_item)
        
        # 保持最多10条记录
        if len(st.session_state.search_history) > 10:
            st.session_state.search_history = st.session_state.search_history[:10]
    

    
    # 历史记录选择器
    st.markdown("---")
    st.subheader("📚 搜索历史" if st.session_state.language == "zh" else "📚 Search History")
    
    if st.session_state.search_history:
        # 创建历史记录选择器
        history_titles = [item['title'] for item in st.session_state.search_history]
        selected_history = st.selectbox(
            "选择历史记录" if st.session_state.language == "zh" else "Select History Record",
            options=history_titles,
            index=0
        )
        
        # 保存选中的历史记录到session state
        selected_item = next((item for item in st.session_state.search_history if item['title'] == selected_history), None)
        if selected_item:
            st.session_state.selected_history_item = selected_item
    else:
        st.info("暂无搜索历史" if st.session_state.language == "zh" else "No search history yet")
        st.session_state.selected_history_item = None

# 获取当前语言
lang = LANGUAGES[st.session_state.language]

# 根据语言获取关键词和公司
KEYWORDS = KEYWORDS_MAPPING[st.session_state.language]
COMPANIES = COMPANIES_MAPPING[st.session_state.language]

TIME_OPTIONS = lang["time_options"]

# 确保关键词和公司列表根据语言动态更新
def get_localized_options():
    """获取本地化的选项列表"""
    current_lang = st.session_state.language
    return {
        "keywords": KEYWORDS_MAPPING[current_lang],
        "companies": list(COMPANIES_MAPPING[current_lang].keys()),
        "time_options": LANGUAGES[current_lang]["time_options"]
    }

# API 配置 - 从 secrets.toml 文件读取
try:
    SERPAPI_API_KEY = st.secrets["SERPAPI_API_KEY"]
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
except KeyError as e:
    st.error(f"❌ 配置错误: 在 .streamlit/secrets.toml 文件中缺少 API 密钥: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ 读取配置文件失败: {e}")
    st.stop()

# 预定义数据
KEYWORDS = [
    "锂", "钴", "镍", "石墨", "锰", "铜", "铝", "锌", "镓", "锗", "稀土", "钨", "钛", "钒", "锑", "铍", "锆", "钽", "铌",
    "砷", "重晶石", "铋", "铈", "铯", "铬", "镝", "铒", "铕", "萤石", "钆", "铪", "钬", "铟", "铱", "镧", "镥", "镁", 
    "钕", "钯", "铂", "镨", "铑", "铷", "钌", "钐", "钪", "碲", "铽", "铥", "锡", "镱", "钇",     "中美关键矿产", "地缘政治竞争的关键矿产",
    "中非关键矿产", "欧盟、中国、非洲地缘政治竞争", "一带一路倡议,中国和非洲", "稀土美国，中国稀土", "稀土中国-非洲，稀土中非", 
    "欧盟-中国-非洲关键矿产", "提炼非洲和中国的关键矿产", "中国-刚果钴业"
]

COMPANIES = {
    "CMOC China Molybdenum / Luoyang Molybdenum Industry": "洛钼集团",
    "Zijin": "紫金矿业集团股份有限公司",
    "Chengxin Lithium (Chengxin Lithium Group / Chengxin)": "成都成鑫锂业股份有限公司",
    "Tsingshan Holding group": "青山控股集团有限公司",
    "Huayou Cobalt": "浙江华友钴业股份有限公司",
    "Sinomine Resources Group": "中矿资源集团股份有限公司",
    "Sinohydro Corporation": "中国水利水电建设集团公司",
    "Sichuan Yahua Industrial Group": "四川雅化实业集团股份有限公司 (雅化集团)",
    "Chinalco (Aluminum Corporation of China)": "中国铝业集团有限公司 (中国铝业 / 中铝)",
    "China Minmetals Corporation": "中国五矿集团有限公司 (五矿集团)",
    "China Hongqiao group": "中国宏桥集团有限公司",
    "China Non Metals Mining Group": "中国有色矿业集团有限公司",
    "Jiangxi Copper Company": "江西铜业集团有限公司 (江西铜业)",
    "Baiyin Nonferrous Group (BNMC)": "白银有色集团股份有限公司 (白银有色)",
    "Hunan Nonferrous Metals Group": "湖南有色金属控股集团有限公司 (湖南有色)",
    "Tibet Huayu Mining": "西藏华钰矿业股份有限公司 (华钰矿业)",
    "Ganfeng Lithium": "赣丰锂业",
    "Tibet Everest Resources": "西藏珠峰资源股份有限公司",
    "BYD": "比亚迪股份有限公司 (比亚迪)",
    "Tianqi Lithium": "天齐锂业股份有限公司 (天齐锂业)",
    "CATL": "宁德时代新能源科技股份有限公司 (宁德时代)"
}

TIME_OPTIONS = {
    "最近2周": "2_weeks",
    "最近2天": "2_days",
    "自定义时间区间": "custom"
}

def generate_news_prompt(selected_keywords, selected_companies, time_option, custom_start_date=None, custom_end_date=None):
    """生成搜索参数描述（用于显示）"""
    current_date = datetime.now()
    
    # 构建关键词显示
    if selected_keywords:
        keywords_str = ", ".join(selected_keywords)
        keywords_display = f"Keywords: {keywords_str}" if st.session_state.language == "en" else f"关键词: {keywords_str}"
    else:
        keywords_display = "Keywords: Not specified" if st.session_state.language == "en" else "关键词: 未指定"
    
    # 构建公司显示
    if selected_companies:
        current_companies_mapping = COMPANIES_MAPPING[st.session_state.language]
        predefined_companies = [comp for comp in selected_companies if comp in current_companies_mapping]
        custom_companies = [comp for comp in selected_companies if comp not in current_companies_mapping]
        
        companies_parts = []
        if predefined_companies:
            companies_parts.append(f"Predefined companies: {', '.join(predefined_companies)}" if st.session_state.language == "en" else f"预定义公司: {', '.join(predefined_companies)}")
        if custom_companies:
            companies_parts.append(f"Custom companies: {', '.join(custom_companies)}" if st.session_state.language == "en" else f"自定义公司: {', '.join(custom_companies)}")
        
        companies_display = "; ".join(companies_parts)
    else:
        companies_display = "Companies: Not specified" if st.session_state.language == "en" else "公司: 未指定"
    
    # 构建时间字符串
    if time_option == "2_weeks":
        start_date = current_date - timedelta(weeks=2)
        if st.session_state.language == "en":
            time_str = f"last 2 weeks ({start_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')})"
        else:
            time_str = f"最近2周（{start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}）"
    elif time_option == "2_days":
        start_date = current_date - timedelta(days=2)
        if st.session_state.language == "en":
            time_str = f"last 2 days ({start_date.strftime('%Y-%m-%d')} to {current_date.strftime('%Y-%m-%d')})"
        else:
            time_str = f"最近2天（{start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}）"
    elif time_option == "custom" and custom_start_date and custom_end_date:
        if st.session_state.language == "en":
            time_str = f"custom time range ({custom_start_date} to {custom_end_date})"
        else:
            time_str = f"自定义时间区间（{custom_start_date} 至 {custom_end_date}）"
    else:
        time_str = "recent time period" if st.session_state.language == "en" else "最近时间段"
    
    # 构建搜索范围描述
    if selected_keywords and selected_companies:
        search_scope = f"news about {keywords_display} or {companies_display}" if st.session_state.language == "en" else f"关于{keywords_display}或{companies_display}的新闻"
    elif selected_keywords:
        search_scope = f"news about {keywords_display}" if st.session_state.language == "en" else f"关于{keywords_display}的新闻"
    elif selected_companies:
        search_scope = f"news about {companies_display}" if st.session_state.language == "en" else f"关于{companies_display}的新闻"
    else:
        search_scope = "news" if st.session_state.language == "en" else "新闻"
    
    # 生成搜索参数描述
    if st.session_state.language == "en":
        prompt = f"""Search Parameters:
- Search Scope: {search_scope}
- Time Range: {time_str}
- Current Date: {current_date.strftime('%Y-%m-%d')}
- Search Engine: Baidu News (via SerpApi) → OpenAI Formatting
- Logic: OR (news content is relevant if it matches ANY keyword OR ANY company)

{keywords_display}
{companies_display}

The system will: 1) Search for real news articles via SerpApi, 2) Format output with OpenAI using the following 7 fields for each news item:
1. Title: Complete news title
2. Relevance: Relevance score (0-1, 1 being most relevant)
3. Source: News source (from Chinese media)
4. Source Link: URL link to the original news article (real and accessible)
5. Publish Time: Specific publication time (YYYY-MM-DD HH:MM)
6. Summary: Brief overview (100-200 words)
7. Full Text: Complete news content"""
    else:
        prompt = f"""搜索参数：
- 搜索范围：{search_scope}
- 时间范围：{time_str}
- 当前日期：{current_date.strftime('%Y年%m月%d日')}
- 搜索引擎：百度新闻（通过SerpApi）→ OpenAI格式化
- 逻辑：或（新闻内容与任一关键词或任一公司相关即可）

{keywords_display}
{companies_display}

系统将：1）通过SerpApi搜索真实新闻文章，2）使用OpenAI格式化输出，为每条新闻提供以下7个字段的分析：
1. 标题：新闻的完整标题
2. 相关性：相关性评分（0-1，1为最相关）
3. 来源：新闻来源（来自中国媒体）
4. 来源链接：原始新闻文章的URL链接（真实可访问）
5. 发布时间：具体发布时间（年-月-日 时:分）
6. 摘要：简要概述（100-200字）
7. 全文：新闻完整内容"""
    
    return prompt

def generate_language_conversion_prompt(news_content, target_language):
    """生成语言转换Prompt - 第二步：根据UI语言要求转换输出语言"""
    if target_language == "en":
        prompt = f"""You are a professional news content translator and formatter. Please convert the following Chinese news analysis to English while maintaining the exact same structure and format.

⚠️ CRITICAL REQUIREMENTS:
- Convert ALL Chinese text to English
- Keep the exact same 7-field format: Title, Relevance, Source, Source Link, Publish Time, Summary, Full Text
- Maintain red bold formatting for field labels: <span style="color: #ff0000; font-weight: bold;">**Field Name**</span>
- Keep the same line breaks and spacing between fields
- Preserve all news content and relevance scores
- Ensure professional English translation

Original Chinese content:
{news_content}

Please provide the English version with the exact same format and structure."""
    else:
        prompt = f"""你是一个专业的新闻内容翻译和格式化专家。请将以下英文新闻分析转换为中文，同时保持完全相同的结构和格式。

⚠️ 重要要求：
- 将所有英文文本转换为中文
- 保持完全相同的7字段格式：标题、相关性、来源、来源链接、发布时间、摘要、全文
- 保持字段标签的红色加粗格式：<span style="color: #ff0000; font-weight: bold;">**字段名**</span>
- 保持相同的换行和字段间间距
- 保留所有新闻内容和相关性评分
- 确保专业的中文翻译

原始英文内容：
{news_content}

请提供中文版本，保持完全相同的格式和结构。"""
    
    return prompt

def search_baidu_news(keywords, companies, time_option, custom_start_date=None, custom_end_date=None):
    """使用SerpApi搜索百度新闻（第一步）"""
    try:
        # 构建搜索查询
        search_terms = []
        
        # 添加关键词
        if keywords:
            search_terms.extend(keywords)
        
        # 添加公司名称
        if companies:
            # 获取当前语言的公司映射
            current_companies_mapping = COMPANIES_MAPPING[st.session_state.language]
            for company in companies:
                if company in current_companies_mapping:
                    # 使用预定义公司的中文名称进行搜索
                    search_terms.append(current_companies_mapping[company])
                else:
                    # 使用自定义公司名称
                    search_terms.append(company)
        
        # 构建搜索查询字符串
        query = " OR ".join(search_terms) if search_terms else "关键矿产"
        
        # 添加时间范围限制
        current_date = datetime.now()
        if time_option == "2_weeks":
            start_date = current_date - timedelta(weeks=2)
            date_range = f" {start_date.strftime('%Y年%m月%d日')}..{current_date.strftime('%Y年%m月%d日')}"
        elif time_option == "2_days":
            start_date = current_date - timedelta(days=2)
            date_range = f" {start_date.strftime('%Y年%m月%d日')}..{current_date.strftime('%Y年%m月%d日')}"
        elif time_option == "custom" and custom_start_date and custom_end_date:
            date_range = f" {custom_start_date.strftime('%Y年%m月%d日')}..{custom_end_date.strftime('%Y年%m月%d日')}"
        else:
            date_range = ""
        
        # 最终搜索查询
        final_query = query + date_range
        
        # 使用SerpApi搜索百度新闻
        search = GoogleSearch({
            "engine": "baidu_news",
            "q": final_query,
            "api_key": SERPAPI_API_KEY,
            "medium":1,
            "rtt":4,
            "num": 8  # 获取前8条结果
        })
        
        results = search.get_dict()
        
        # 处理搜索结果
        if "organic_results" in results and results["organic_results"]:
            return results["organic_results"]  # 返回原始搜索结果
        else:
            return None  # 返回None表示未找到结果
            
    except Exception as e:
        raise Exception(f"搜索失败: {str(e)}")

def scrape_web_content(url, max_retries=3):
    """抓取网页内容"""
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        for attempt in range(max_retries):
            try:
                # 发送请求
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type:
                    return f"❌ 无法获取HTML内容，内容类型: {content_type}"
                
                # 解析HTML
                soup = BeautifulSoup(response.content, 'lxml')
                
                # 移除脚本和样式标签
                for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    script.decompose()
                
                # 尝试多种选择器来找到主要内容
                content_selectors = [
                    'article',
                    '.article-content',
                    '.content',
                    '.news-content',
                    '.post-content',
                    '.entry-content',
                    'main',
                    '.main-content',
                    '#content',
                    '.article-body',
                    '.news-body'
                ]
                
                content_text = ""
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        content_text = ' '.join([elem.get_text(strip=True) for elem in elements])
                        if len(content_text) > 100:  # 确保内容足够长
                            break
                
                # 如果没有找到特定内容区域，尝试获取body内容
                if not content_text or len(content_text) < 100:
                    body = soup.find('body')
                    if body:
                        content_text = body.get_text(strip=True)
                
                # 清理文本
                if content_text:
                    # 移除多余的空白字符
                    content_text = re.sub(r'\s+', ' ', content_text)
                    # 限制长度（避免过长的内容）
                    if len(content_text) > 5000:
                        content_text = content_text[:5000] + "..."
                    return content_text
                else:
                    return "❌ 无法提取网页内容"
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    return f"❌ 网络请求失败: {str(e)}"
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                else:
                    return f"❌ 解析失败: {str(e)}"
                    
    except Exception as e:
        return f"❌ 抓取失败: {str(e)}"

def fix_html_rendering(content):
    """修复HTML渲染问题，确保HTML标签被正确显示"""
    import html
    
    # 如果内容被HTML转义了，先解码
    if '&lt;' in content or '&gt;' in content or '&amp;' in content:
        content = html.unescape(content)
    
    # 确保span标签格式正确
    content = content.replace('&lt;span', '<span')
    content = content.replace('&lt;/span&gt;', '</span>')
    content = content.replace('&quot;', '"')
    
    return content

def normalize_publish_time(publish_time):
    """将发布时间统一转换为 %Y-%m-%d 格式"""
    if not publish_time:
        return None
    
    current_date = datetime.now()
    current_year = current_date.year
    
    # 处理"今天"的情况
    if "今天" in publish_time:
        return current_date.strftime('%Y-%m-%d')
    
    # 处理"昨天"的情况
    elif "昨天" in publish_time:
        return (current_date - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 处理"X天前"的情况
    elif "天前" in publish_time:
        try:
            days_ago = int(publish_time.replace("天前", "").strip())
            target_date = current_date - timedelta(days=days_ago)
            return target_date.strftime('%Y-%m-%d')
        except ValueError:
            return None
    
    # 处理"X月X日"格式（如 "9月27日"）
    elif "月" in publish_time and "日" in publish_time:
        try:
            # 提取月份和日期
            parts = publish_time.replace("月", " ").replace("日", "").split()
            if len(parts) >= 2:
                month = int(parts[0])
                day = int(parts[1])
                
                # 创建日期，假设是当前年份
                target_date = datetime(current_year, month, day)
                
                # 如果日期在未来（比如现在是10月，但日期是9月），则认为是去年
                if target_date > current_date:
                    target_date = datetime(current_year - 1, month, day)
                
                return target_date.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            return None
    
    # 处理标准日期格式（如 "2025-10-03 18:51"）
    else:
        try:
            # 尝试解析 "YYYY-MM-DD HH:MM" 格式
            news_date = datetime.strptime(publish_time.split()[0], '%Y-%m-%d')
            return news_date.strftime('%Y-%m-%d')
        except (ValueError, IndexError):
            # 如果解析失败，尝试直接使用 "YYYY-MM-DD" 格式
            try:
                news_date = datetime.strptime(publish_time, '%Y-%m-%d')
                return news_date.strftime('%Y-%m-%d')
            except ValueError:
                return None

def analyze_news_with_openai(news_results, keywords, companies, start_date, end_date):
    """使用OpenAI分析新闻搜索结果，重新根据时间范围进行筛选处理"""
    
    # 将 start_date 和 end_date 转换为 date 对象进行比较
    if isinstance(start_date, datetime):
        start_date_obj = start_date.date()
    else:
        start_date_obj = start_date
    
    if isinstance(end_date, datetime):
        end_date_obj = end_date.date()
    else:
        end_date_obj = end_date
    
    # Filter news_results by Publish Time
    filtered_news = []
    
    for news_item in news_results:
        publish_time = news_item.get('date', '')
        
        # 规范化发布时间格式
        standardized_date = normalize_publish_time(publish_time)
        
        if standardized_date:
            try:
                news_date = datetime.strptime(standardized_date, '%Y-%m-%d').date()
                
                # 使用 date 对象进行比较
                if start_date_obj <= news_date <= end_date_obj:
                    filtered_news.append(news_item)
            except ValueError:
                continue  # Skip if date cannot be parsed

    # Check if any news collected after filtering
    if not filtered_news:
        return ("未找到符合时间范围的新闻" if st.session_state.language == "zh" else "No news found within the time range")

    # Proceed to analyze with OpenAI
    try:
        # The rest of the code remains the same, analysis continues...
        enhanced_news_results = []
        for i, news_item in enumerate(filtered_news):
            enhanced_item = news_item.copy()
            news_url = news_item.get('link', '')
            if news_url and validate_url(news_url)[0]:
                if st.session_state.language == "zh":
                    progress_text = f"🔍 正在抓取第{i+1}条新闻内容..."
                else:
                    progress_text = f"🔍 Scraping content for news item {i+1}..."
                if hasattr(st, 'info'):
                    st.info(progress_text)

                full_text = scrape_web_content(news_url)
                enhanced_item['full_text'] = full_text
            else:
                enhanced_item['full_text'] = "❌ 无效链接或无法访问"
            enhanced_news_results.append(enhanced_item)

        # Rebuild the prompt for language-specific analysis
        current_lang = st.session_state.language if hasattr(st, 'session_state') and 'language' in st.session_state else "zh"
        
        if current_lang == "zh":
            analysis_prompt = f"""你是一个专业的新闻分析师。请根据以下百度新闻搜索结果，为每条新闻提供详细的分析和格式化输出。

重要说明：
1. 请确保所有输出内容都是中文，包括标题、摘要、全文等所有字段
2. 请直接输出HTML格式，不要转义HTML标签
3. 使用以下HTML格式来标记字段标题：<span style="color: #ff0000; font-weight: bold;">**字段名**</span>

搜索关键词：{', '.join(keywords) if keywords else '无'}
搜索公司：{', '.join(companies) if companies else '无'}

请为每条新闻提供以下7个字段的详细分析：

1. 标题：新闻的完整标题（保持原标题，如果是英文标题则翻译为中文）
2. 相关性：相关性评分（0-1，1为最相关），基于与关键词和公司的匹配度
3. 来源：新闻来源（必须来自中国媒体）
4. 来源链接：原始新闻文章的URL链接
5. 发布时间：具体发布时间（年-月-日 时:分）
6. 摘要：新闻的简要概述（100-200字，必须用中文）
7. 全文：新闻的完整内容（如果抓取成功，请将抓取到的内容翻译为中文；如果抓取失败，请基于标题和摘要生成合理的中文内容）

新闻搜索结果（包含抓取的完整内容）：
{json.dumps(enhanced_news_results, ensure_ascii=False, indent=2)}

输出格式示例：
<span style="color: #ff0000; font-weight: bold;">**标题**</span>: [新闻标题]

<span style="color: #ff0000; font-weight: bold;">**相关性**</span>: [0-1分值]

<span style="color: #ff0000; font-weight: bold;">**来源**</span>: [新闻来源]

<span style="color: #ff0000; font-weight: bold;">**来源链接**</span>: [URL链接]

<span style="color: #ff0000; font-weight: bold;">**发布时间**</span>: [时间]

<span style="color: #ff0000; font-weight: bold;">**摘要**</span>: [摘要内容]

<span style="color: #ff0000; font-weight: bold;">**全文**</span>: [全文内容]

---

请严格按照上述格式输出，不要转义HTML标签。"""
        else:
            analysis_prompt = f"""You are a professional news analyst. Please analyze the following Baidu news search results and provide detailed analysis for each news item.

IMPORTANT Instructions:
1. Please ensure ALL output content is in English, including titles, summaries, full text, and all other fields
2. Please output HTML format directly, do NOT escape HTML tags
3. Use this HTML format for field headers: <span style="color: #ff0000; font-weight: bold;">**Field Name**</span>

Search Keywords: {', '.join(keywords) if keywords else 'None'}
Search Companies: {', '.join(companies) if companies else 'None'}

Please provide detailed analysis for each news item with the following 7 fields:

1. Title: Complete news title (translate Chinese titles to English if necessary)
2. Relevance: Relevance score (0-1, 1 being most relevant), based on match with keywords and companies
3. Source: News source (must be from Chinese media, keep original Chinese name)
4. Source Link: URL link to the original news article
5. Publish Time: Specific publication time (YYYY-MM-DD HH:MM)
6. Summary: Brief overview (100-200 words, must be in English)
7. Full Text: Complete news content (if scraping successful, translate the scraped content to English; if scraping failed, generate reasonable English content based on title and snippet)

News search results (with scraped full content):
{json.dumps(enhanced_news_results, ensure_ascii=False, indent=2)}

Output format example:
<span style="color: #ff0000; font-weight: bold;">**Title**</span>: [News title]

<span style="color: #ff0000; font-weight: bold;">**Relevance**</span>: [0-1 score]

<span style="color: #ff0000; font-weight: bold;">**Source**</span>: [News source]

<span style="color: #ff0000; font-weight: bold;">**Source Link**</span>: [URL link]

<span style="color: #ff0000; font-weight: bold;">**Publish Time**</span>: [Time]

<span style="color: #ff0000; font-weight: bold;">**Summary**</span>: [Summary content]

<span style="color: #ff0000; font-weight: bold;">**Full Text**</span>: [Full text content]

---

Please strictly follow the above format and do NOT escape HTML tags."""
        
        # 调用OpenAI API进行分析
        analysis_result = call_openai_api(analysis_prompt)
        
        # 修复HTML渲染问题
        analysis_result = fix_html_rendering(analysis_result)
        
        return analysis_result
    except Exception as e:
        return format_news_results(news_results, keywords, companies)

def format_news_results(news_results, keywords, companies):
    """格式化新闻搜索结果"""
    formatted_results = []
    
    # 获取当前语言设置
    current_lang = st.session_state.language if hasattr(st, 'session_state') and hasattr(st.session_state, 'language') else "zh"
    
    for i, news in enumerate(news_results[:5]):  # 限制显示前5条新闻
        # 计算相关性评分
        relevance_score = calculate_relevance_score(news, keywords, companies)
        
        # 根据语言设置格式化单条新闻
        if current_lang == "zh":
            news_item = f"""<span style="color: #ff0000; font-weight: bold;">**Title（标题）**</span>: {news.get('title', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Relevance（相关性）**</span>: {relevance_score:.2f}

<span style="color: #ff0000; font-weight: bold;">**Source（来源）**</span>: {news.get('source', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Source Link（来源链接）**</span>: {news.get('link', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Publish Time（发布时间）**</span>: {news.get('date', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Summary（摘要）**</span>: {news.get('snippet', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Full Text（全文）**</span>: {news.get('snippet', 'N/A')}

---
"""
        else:
            news_item = f"""<span style="color: #ff0000; font-weight: bold;">**Title**</span>: {news.get('title', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Relevance**</span>: {relevance_score:.2f}

<span style="color: #ff0000; font-weight: bold;">**Source**</span>: {news.get('source', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Source Link**</span>: {news.get('link', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Publish Time**</span>: {news.get('date', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Summary**</span>: {news.get('snippet', 'N/A')}

<span style="color: #ff0000; font-weight: bold;">**Full Text**</span>: {news.get('snippet', 'N/A')}

---
"""
        formatted_results.append(news_item)
    
    return "\n".join(formatted_results)

def calculate_relevance_score(news, keywords, companies):
    """计算新闻相关性评分"""
    score = 0.0
    title = news.get('title', '').lower()
    snippet = news.get('snippet', '').lower()
    content = f"{title} {snippet}"
    
    # 关键词匹配
    if keywords:
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in content)
        score += (keyword_matches / len(keywords)) * 0.6
    
    # 公司匹配
    if companies:
        company_matches = 0
        current_companies_mapping = COMPANIES_MAPPING[st.session_state.language]
        for company in companies:
            if company in current_companies_mapping:
                company_name = current_companies_mapping[company].lower()
                if company_name in content:
                    company_matches += 1
            else:
                if company.lower() in content:
                    company_matches += 1
        score += (company_matches / len(companies)) * 0.4
    
    # 确保评分在0-1之间
    return min(max(score, 0.1), 1.0)

def extract_search_terms_from_prompt(prompt):
    """从自定义prompt中提取关键词和公司信息"""
    keywords = []
    companies = []
    
    # 获取当前语言的关键词和公司列表
    current_keywords = KEYWORDS_MAPPING[st.session_state.language]
    current_companies = list(COMPANIES_MAPPING[st.session_state.language].keys())
    
    prompt_lower = prompt.lower()
    
    # 提取关键词
    for keyword in current_keywords:
        if keyword.lower() in prompt_lower:
            keywords.append(keyword)
    
    # 提取公司
    for company in current_companies:
        if company.lower() in prompt_lower:
            companies.append(company)
    
    # 如果没有找到预定义的关键词或公司，使用一些通用关键词
    if not keywords and not companies:
        keywords = ["关键矿产", "矿业"] if st.session_state.language == "zh" else ["critical minerals", "mining"]
    
    return keywords, companies

def extract_keywords_and_time_with_chatgpt(prompt, model="gpt-4o"):
    """使用ChatGPT从自定义prompt中提取核心关键词和时间信息"""
    try:
        # 构建提取prompt
        if st.session_state.language == "zh":
            extraction_prompt = f"""你是一个专业的文本分析助手。请从以下用户输入的prompt中提取核心搜索关键词和时间信息。

用户输入的prompt: "{prompt}"

请按照以下JSON格式返回结果：
{{
    "keywords": ["核心关键词"],
    "time_description": "时间描述",
    "time_type": "relative|absolute|none",
    "time_value": "具体时间值",
    "explanation": "提取过程的简要说明"
}}

提取规则：
1. keywords: 只提取最核心的1-2个关键词，必须是关键矿产、矿业、公司、投资、项目等相关的核心词汇
   - 例如："I searched for Chinese top news on critical minerals in the last 2 days" 只提取 "critical minerals"
   - 例如："Latest news about Zijin Mining lithium projects" 只提取 "Zijin Mining" 和 "lithium"
   - 不要提取"news"、"latest"、"top"、"Chinese"等修饰词
2. time_description: 原始prompt中的时间描述（如"最近2天"、"last 2 days"等）
3. time_type: "relative"表示相对时间，"absolute"表示绝对时间，"none"表示无时间限制
4. time_value: 如果是相对时间，提取数字和单位（如"2 days"、"1 week"等）
5. explanation: 简要说明提取的核心关键词和时间信息

请确保：
- 只提取最核心的关键词，数量控制在1-2个
- 关键词要具体且相关，不要包含修饰词
- 时间信息要准确
- JSON格式要正确
- 如果prompt中没有明确的时间信息，time_type设为"none"
"""
        else:
            extraction_prompt = f"""You are a professional text analysis assistant. Please extract core search keywords and time information from the following user prompt.

User prompt: "{prompt}"

Please return the result in the following JSON format:
{{
    "keywords": ["core keyword"],
    "time_description": "time description",
    "time_type": "relative|absolute|none",
    "time_value": "specific time value",
    "explanation": "brief explanation of extraction process"
}}

Extraction rules:
1. keywords: Extract only the most core 1-2 keywords related to critical minerals, mining, companies, investments, projects, etc.
   - Example: "I searched for Chinese top news on critical minerals in the last 2 days" → extract only "critical minerals"
   - Example: "Latest news about Zijin Mining lithium projects" → extract only "Zijin Mining" and "lithium"
   - Do NOT extract modifiers like "news", "latest", "top", "Chinese", etc.
2. time_description: Original time description in the prompt (e.g., "last 2 days", "recent week", etc.)
3. time_type: "relative" for relative time, "absolute" for absolute time, "none" for no time limit
4. time_value: If relative time, extract number and unit (e.g., "2 days", "1 week", etc.)
5. explanation: Brief explanation of extracted core keywords and time information

Please ensure:
- Extract only the most core keywords, limit to 1-2 keywords
- Keywords should be specific and relevant, exclude modifiers
- Time information is accurate
- JSON format is correct
- If no clear time information in prompt, set time_type to "none"
"""
        
        # 调用OpenAI API
        client = OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": extraction_prompt}
            ],
            temperature=0.1,
            max_tokens=1000,
            stream=False
        )
        
        response_text = completion.choices[0].message.content
        
        # 解析JSON响应
        import json
        try:
            # 尝试提取JSON部分
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
                
                # 验证必要字段
                if all(key in result for key in ['keywords', 'time_description', 'time_type', 'time_value', 'explanation']):
                    return result
                else:
                    raise ValueError("Missing required fields in JSON response")
            else:
                raise ValueError("No valid JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # 如果JSON解析失败，返回默认值
            return {
                "keywords": ["关键矿产", "矿业"] if st.session_state.language == "zh" else ["critical minerals", "mining"],
                "time_description": "无时间限制" if st.session_state.language == "zh" else "no time limit",
                "time_type": "none",
                "time_value": "",
                "explanation": f"JSON解析失败，使用默认关键词: {str(e)}"
            }
            
    except Exception as e:
        # 如果API调用失败，返回默认值
        return {
            "keywords": ["关键矿产", "矿业"] if st.session_state.language == "zh" else ["critical minerals", "mining"],
            "time_description": "无时间限制" if st.session_state.language == "zh" else "no time limit",
            "time_type": "none",
            "time_value": "",
            "explanation": f"API调用失败，使用默认关键词: {str(e)}"
        }

def convert_time_to_date_range(time_description, time_type, time_value):
    """将时间描述转换为具体的日期范围"""
    try:
        current_date = datetime.now()
        
        if time_type == "none" or not time_value:
            # 默认使用最近6个月
            start_date = current_date - timedelta(days=180)  # 约6个月
            end_date = current_date
            return start_date, end_date, "最近6个月" if st.session_state.language == "zh" else "last 6 months"
        
        elif time_type == "relative":
            # 处理相对时间
            time_value_lower = time_value.lower().strip()
            
            # 处理天数
            if "day" in time_value_lower:
                try:
                    days = int(''.join(filter(str.isdigit, time_value_lower)))
                    start_date = current_date - timedelta(days=days)
                    end_date = current_date
                    time_desc = f"最近{days}天" if st.session_state.language == "zh" else f"last {days} days"
                    return start_date, end_date, time_desc
                except ValueError:
                    pass
            
            # 处理周数
            elif "week" in time_value_lower:
                try:
                    weeks = int(''.join(filter(str.isdigit, time_value_lower)))
                    start_date = current_date - timedelta(weeks=weeks)
                    end_date = current_date
                    time_desc = f"最近{weeks}周" if st.session_state.language == "zh" else f"last {weeks} weeks"
                    return start_date, end_date, time_desc
                except ValueError:
                    pass
            
            # 处理月数
            elif "month" in time_value_lower:
                try:
                    months = int(''.join(filter(str.isdigit, time_value_lower)))
                    start_date = current_date - timedelta(days=months * 30)  # 近似处理
                    end_date = current_date
                    time_desc = f"最近{months}个月" if st.session_state.language == "zh" else f"last {months} months"
                    return start_date, end_date, time_desc
                except ValueError:
                    pass
            
            # 处理小时
            elif "hour" in time_value_lower:
                try:
                    hours = int(''.join(filter(str.isdigit, time_value_lower)))
                    start_date = current_date - timedelta(hours=hours)
                    end_date = current_date
                    time_desc = f"最近{hours}小时" if st.session_state.language == "zh" else f"last {hours} hours"
                    return start_date, end_date, time_desc
                except ValueError:
                    pass
        
        # 如果无法解析，使用默认值
        start_date = current_date - timedelta(days=180)  # 约6个月
        end_date = current_date
        return start_date, end_date, "最近6个月" if st.session_state.language == "zh" else "last 6 months"
        
    except Exception as e:
        # 异常情况下使用默认值
        current_date = datetime.now()
        start_date = current_date - timedelta(days=180)  # 约6个月
        end_date = current_date
        return start_date, end_date, "最近6个月" if st.session_state.language == "zh" else "last 6 months"

def translate_keywords_to_chinese(keywords, model="gpt-4o"):
    """将英文关键字翻译成中文"""
    try:
        if not keywords:
            return []
        
        # 检查是否包含英文字符
        has_english = any(any(c.isalpha() and ord(c) < 128 for c in keyword) for keyword in keywords)
        if not has_english:
            # 如果没有英文字符，直接返回原关键字
            return keywords
        
        # 构建翻译prompt
        keywords_str = ", ".join(keywords)
        translation_prompt = f"""请将以下英文关键词翻译成中文，保持专业术语的准确性：

英文关键词: {keywords_str}

翻译要求：
1. 保持关键词的专业性和准确性
2. 如果是矿业、矿产相关的专业术语，请使用标准的中文翻译
3. 如果是公司名称，请使用该公司的官方中文名称
4. 只返回翻译后的中文关键词，用逗号分隔
5. 不要添加任何解释或其他内容

请直接返回翻译结果："""
        
        # 调用OpenAI API进行翻译
        client = OpenAI(api_key=OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": translation_prompt}
            ],
            temperature=0.1,
            max_tokens=500,
            stream=False
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # 解析翻译结果
        translated_keywords = [keyword.strip() for keyword in response_text.split(',') if keyword.strip()]
        
        # 如果翻译失败或结果为空，返回原关键字
        if not translated_keywords:
            return keywords
        
        return translated_keywords
        
    except Exception as e:
        # 如果翻译失败，返回原关键字
        print(f"Translation failed: {str(e)}")
        return keywords

def call_openai_api(prompt, model="gpt-4o"):
    """调用OpenAI API (用于语言转换和内容分析)"""
    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=OPENAI_API_KEY,
        )
        
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=4096,
            stream=False
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return "❌ API调用失败: 您的OpenAI API密钥已过期或无效，请检查API密钥设置。"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return "❌ API调用失败: 已达到OpenAI API调用配额限制，请稍后再试。"
        else:
            return f"❌ API调用失败: {error_msg}"

def main():
    st.title(lang["title"])
    st.markdown("---")
    
    # 创建三个Tab页
    tab1, tab2, tab3 = st.tabs([lang["tab1_title"], lang["tab2_title"], "📚 Search History" if st.session_state.language == "en" else "📚 搜索历史"])
    
    with tab1:
        st.header(lang["tab1_title"])
        st.markdown("Please select filtering criteria, the system will: 1) Search Baidu News via SerpApi, 2) Format output with OpenAI" if st.session_state.language == "en" else "请选择筛选条件，系统将：1）通过SerpApi搜索百度新闻，2）使用OpenAI进行格式化输出")
        st.markdown('<div style="font-size: 16px;">💡 Search Tip: You can choose keywords, companies, or both, combined with time range for flexible search</div>' if st.session_state.language == "en" else '<div style="font-size: 16px;">💡 搜索提示：您可以选择关键词、公司或两者都选择，配合时间范围进行灵活搜索</div>', unsafe_allow_html=True)
        
        # 创建三列布局
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader(lang["keywords_title"])
            # 动态获取当前语言的选项
            localized_options = get_localized_options()
            current_keywords = localized_options["keywords"]
            
            # 默认选择前5个关键词
            default_keywords = current_keywords[:5] if len(current_keywords) >= 5 else current_keywords
            selected_keywords = st.multiselect(
                "Select keywords (multiple choice):" if st.session_state.language == "en" else "选择关键词（可多选，可选）:",
                options=current_keywords,
                default=default_keywords,
                help="Select critical minerals or related topics of interest, optional" if st.session_state.language == "en" else "选择您感兴趣的关键矿产或相关主题，可以不选择",
                format_func=lambda x: x  # 关键修复：确保显示的是本地化关键词文本
            )
            
            # 自定义关键词输入
            custom_keyword = st.text_input(
                "Input custom keyword:" if st.session_state.language == "en" else "输入自定义关键词:", 
                placeholder="Input other keywords..." if st.session_state.language == "en" else "输入其他关键词..."
            )
            if custom_keyword and custom_keyword not in selected_keywords:
                selected_keywords.append(custom_keyword)
        
        with col2:
            st.subheader(lang["companies_title"])
            # 动态获取当前语言的公司选项
            current_companies = localized_options["companies"]
            
            selected_companies = st.multiselect(
                "Select companies (multiple choice):" if st.session_state.language == "en" else "选择公司（可多选，可选）:",
                options=current_companies,
                default=[],  # 默认不选择任何公司
                help="Select companies you are interested in, optional" if st.session_state.language == "en" else "选择您关注的公司，可以不选择",
                format_func=lambda x: x  # 关键修复：确保显示的是本地化公司名称
            )
            
            # 显示选中公司
            if selected_companies:
                st.markdown(f"**{lang['selected_companies']}:**")
                for company in selected_companies:
                    if company in COMPANIES:
                        st.markdown(f"- {company}: {COMPANIES[company]}")
                    else:
                        st.markdown(f"- {company} (自定义)" if st.session_state.language == "zh" else f"- {company} (Custom)")
            
            # 自定义公司输入
            custom_company = st.text_input(
                "Input custom company name:" if st.session_state.language == "en" else "输入自定义公司名称:", 
                placeholder="Input other company names..." if st.session_state.language == "en" else "输入其他公司名称..."
            )
            if custom_company and custom_company not in selected_companies:
                selected_companies.append(custom_company)
        
        with col3:
            st.subheader(lang["time_title"])
            # 动态获取当前语言的时间选项
            current_time_options = localized_options["time_options"]
            
            time_option = st.selectbox(
                "Select time range:" if st.session_state.language == "en" else "选择时间范围:",
                options=list(current_time_options.keys()),
                index=0,
                format_func=lambda x: current_time_options[x]
            )
            
            # 显示动态时间范围
            current_date = datetime.now()
            if time_option == "2_weeks":
                start_date = current_date - timedelta(weeks=2)
                if st.session_state.language == "zh":
                    st.markdown(f'<div style="font-size: 16px;">{lang["time_range_info"]}: {start_date.strftime("%Y年%m月%d日")} 至 {current_date.strftime("%Y年%m月%d日")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size: 16px;">{lang["time_range_info"]}: {start_date.strftime("%Y-%m-%d")} to {current_date.strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
            elif time_option == "2_days":
                start_date = current_date - timedelta(days=2)
                if st.session_state.language == "zh":
                    st.markdown(f'<div style="font-size: 16px;">{lang["time_range_info"]}: {start_date.strftime("%Y年%m月%d日")} 至 {current_date.strftime("%Y年%m月%d日")}</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="font-size: 16px;">{lang["time_range_info"]}: {start_date.strftime("%Y-%m-%d")} to {current_date.strftime("%Y-%m-%d")}</div>', unsafe_allow_html=True)
            
            if time_option == "custom":
                col3a, col3b = st.columns(2)
                with col3a:
                    custom_start_date = st.date_input(lang["start_date"], value=datetime.now() - timedelta(days=7))
                with col3b:
                    custom_end_date = st.date_input(lang["end_date"], value=datetime.now())
            else:
                custom_start_date = None
                custom_end_date = None
        
        # 分析按钮
        st.markdown("---")
        if st.button(lang["start_analysis"], type="primary", use_container_width=True):
            if not selected_keywords and not selected_companies:
                st.markdown(f'<div style="font-size: 16px; color: #ff4b4b;">{lang["error_no_keywords"] if not selected_keywords else lang["error_no_companies"]}</div>', unsafe_allow_html=True)
                st.markdown('<div style="font-size: 16px; color: #ffa500;">💡 Tip: Selecting only time range cannot perform effective search, please choose keywords or companies</div>' if st.session_state.language == "en" else '<div style="font-size: 16px; color: #ffa500;">💡 提示：只选择时间范围无法进行有效搜索，请选择关键词或公司</div>', unsafe_allow_html=True)
            else:
                with st.spinner(lang["analyzing"]):
                    # 第一步：生成新闻搜索Prompt并获取新闻内容
                    news_prompt = generate_news_prompt(
                        selected_keywords, 
                        selected_companies, 
                        time_option,  # 传递键值，不是显示文本
                        custom_start_date,
                        custom_end_date
                    )
                    
                    # 显示第一步生成的Prompt
                    with st.expander(lang["generated_prompt"], expanded=False):
                        st.markdown(f'<div style="font-size: 18px;">{news_prompt}</div>', unsafe_allow_html=True)
                    
                    # 第一步：使用SerpApi搜索百度新闻
                    st.info("🔍 第一步：正在使用SerpApi搜索百度新闻..." if st.session_state.language == "zh" else "🔍 Step 1: Searching Baidu News with SerpApi...")
                    try:
                        news_results = search_baidu_news(selected_keywords, selected_companies, time_option, custom_start_date, custom_end_date)
                        
                        if news_results:
                            # 计算实际的时间范围用于过滤
                            current_date = datetime.now()
                            if time_option == "2_weeks":
                                filter_start_date = current_date - timedelta(weeks=2)
                                filter_end_date = current_date
                            elif time_option == "2_days":
                                filter_start_date = current_date - timedelta(days=2)
                                filter_end_date = current_date
                            elif time_option == "custom" and custom_start_date and custom_end_date:
                                filter_start_date = datetime.combine(custom_start_date, datetime.min.time())
                                filter_end_date = datetime.combine(custom_end_date, datetime.max.time())
                            else:
                                # 默认使用最近2周
                                filter_start_date = current_date - timedelta(weeks=2)
                                filter_end_date = current_date
                            
                            # 显示时间范围信息
                            if st.session_state.language == "zh":
                                st.info(f"📅 过滤时间范围: {filter_start_date.strftime('%Y-%m-%d')} 至 {filter_end_date.strftime('%Y-%m-%d')}")
                            else:
                                st.info(f"📅 Filter time range: {filter_start_date.strftime('%Y-%m-%d')} to {filter_end_date.strftime('%Y-%m-%d')}")
                            
                            # 第二步：使用OpenAI进行格式化输出
                            st.info("🤖 第二步：正在使用OpenAI进行格式化输出..." if st.session_state.language == "zh" else "🤖 Step 2: Formatting output with OpenAI...")
                            final_result = analyze_news_with_openai(news_results, selected_keywords, selected_companies, filter_start_date, filter_end_date)
                            
                            # 显示分析结果
                            st.subheader(lang["analysis_results"])
                            st.markdown(f'<div style="font-size: 18px;">{final_result}</div>', unsafe_allow_html=True)
                            
                            # 保存结果到session state
                            st.session_state.last_news_result = final_result
                            st.session_state.last_prompt = news_prompt
                            
                            # 添加到历史记录
                            add_to_history(selected_keywords, selected_companies, time_option, final_result, news_prompt)
                        else:
                            # 如果未找到新闻
                            error_msg = "❌ 未找到相关新闻，请尝试调整搜索条件或时间范围。" if st.session_state.language == "zh" else "❌ No relevant news found, please try adjusting search conditions or time range."
                            st.subheader(lang["analysis_results"])
                            st.markdown(f'<div style="font-size: 18px;">{error_msg}</div>', unsafe_allow_html=True)
                            
                            # 保存结果到session state
                            st.session_state.last_news_result = error_msg
                            st.session_state.last_prompt = news_prompt
                        
                            # 添加到历史记录
                            add_to_history(selected_keywords, selected_companies, time_option, error_msg, news_prompt)
                            
                    except Exception as e:
                        # 如果搜索失败
                        error_msg = f"❌ 搜索失败: {str(e)}"
                        st.subheader(lang["analysis_results"])
                        st.markdown(f'<div style="font-size: 18px;">{error_msg}</div>', unsafe_allow_html=True)
                        
                        # 保存结果到session state
                        st.session_state.last_news_result = error_msg
                        st.session_state.last_prompt = news_prompt
                        
                        # 添加到历史记录
                        add_to_history(selected_keywords, selected_companies, time_option, error_msg, news_prompt)
        
        # 显示上次分析结果
        if 'last_news_result' in st.session_state:
            st.markdown("---")
            st.subheader(lang["last_results"])
            with st.expander(lang["view_last_results"], expanded=False):
                st.markdown(f'<div style="font-size: 18px;">{st.session_state.last_news_result}</div>', unsafe_allow_html=True)
    
    with tab2:
        st.header(lang["tab2_title"])
        st.markdown("Input your custom prompt, the system will: 1) Search Baidu News via SerpApi, 2) Format output with OpenAI" if st.session_state.language == "en" else "输入您的自定义Prompt，系统将：1）通过SerpApi搜索百度新闻，2）使用OpenAI进行格式化输出")
        
        # 示例Prompt选择
        st.subheader(lang["example_prompts"])
        example_prompts = [
            "Prepare a summary of top critical minerals news in China related to China Molybdenum / Luoyang Molybdenum Industry in the last week, or 2 days",
            "Latest news related to Company Name (i.e Tsingshan Holding group) mining investments in South America",
            "Chinese mining companies in South America lithium copper news last 24 hours",
            "Zijin Mining latest copper or lithium deals in South America",
            "CMOC (China Molybdenum) copper cobalt projects Peru Chile Brazil Argentina news",
            "Chinalco Toromocho mine Peru expansion investment protest",
            "China Minmetals South America, Africa mining copper lithium projects",
            "Ganfeng Lithium Argentina project production expansion news",
            "BYD Brazil Lithium Valley mining project developments",
            "Tianqi Lithium SQM Chile partnership lithium expansion",
            "CATL Bolivia Uyuni salt flats lithium plant progress",
            "CITIC Guoan Bolivia lithium plant project financing",
            "Summarize today's news on Chinese lithium companies in South America, focusing on deals, protests, and government policy.",
            "List new copper, cobalt, or lithium projects announced by Chinese mining companies in Argentina, Chile, Peru, Bolivia, and Brazil in the past 24 hours.",
            "Track latest stock or market for Chinese critical minerals companies with projects in South America, and Africa"
        ]
        
        selected_example = st.selectbox(
            "Select example prompt:" if st.session_state.language == "en" else "选择示例Prompt:",
            options=[lang["custom_input"]] + example_prompts,
            index=0
        )
        
        if selected_example == lang["custom_input"]:
            custom_prompt = st.text_area(
                lang["input_prompt"],
                placeholder=lang["prompt_placeholder"],
                height=150,
                help="Support Chinese and English input" if st.session_state.language == "en" else "支持中英文输入"
            )
        else:
            custom_prompt = st.text_area(
                lang["edit_selected_prompt"],
                value=selected_example,
                height=150
            )
        
        # 模型选择
        model_option = st.selectbox(
            lang["model_selection"],
            options=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            index=0,
            help="Select OpenAI model version" if st.session_state.language == "en" else "选择OpenAI模型版本"
        )
        
        # 分析按钮
        if st.button(lang["analyze_button"], type="primary", use_container_width=True):
            if not custom_prompt.strip():
                st.markdown(f'<div style="font-size: 16px; color: #ff4b4b;">{lang["error_no_prompt"]}</div>', unsafe_allow_html=True)
            else:
                with st.spinner(lang["analyzing"]):
                    # 第一步：使用ChatGPT提取关键词和时间信息
                    st.info("🧠 第一步：正在使用ChatGPT分析Prompt..." if st.session_state.language == "zh" else "🧠 Step 1: Analyzing prompt with ChatGPT...")
                    
                    try:
                        # 使用ChatGPT提取关键词和时间信息
                        extraction_result = extract_keywords_and_time_with_chatgpt(custom_prompt, model_option)
                        
                        # 显示提取结果
                        st.success("✅ Prompt分析完成！" if st.session_state.language == "zh" else "✅ Prompt analysis completed!")
                        
                        # 第三步：翻译关键字为中文
                        st.info("🔄 第三步：正在翻译关键字为中文..." if st.session_state.language == "zh" else "🔄 Step 3: Translating keywords to Chinese...")
                        
                        # 翻译关键字
                        original_keywords = extraction_result["keywords"]
                        translated_keywords = translate_keywords_to_chinese(original_keywords, model_option)
                        
                        # 显示翻译结果
                        st.success("✅ 关键字翻译完成！" if st.session_state.language == "zh" else "✅ Keywords translation completed!")
                        
                        # 创建三列显示提取的参数
                        col_extract1, col_extract2, col_extract3 = st.columns(3)
                        
                        with col_extract1:
                            st.markdown("**🔑 原始关键词 / Original Keywords:**")
                            original_display = ", ".join(original_keywords) if original_keywords else ("无" if st.session_state.language == "zh" else "None")
                            st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;">{original_display}</div>', unsafe_allow_html=True)
                        
                        with col_extract2:
                            st.markdown("**🇨🇳 中文关键词 / Chinese Keywords:**")
                            translated_display = ", ".join(translated_keywords) if translated_keywords else ("无" if st.session_state.language == "zh" else "None")
                            st.markdown(f'<div style="background-color: #e8f5e8; padding: 10px; border-radius: 5px; margin: 5px 0;">{translated_display}</div>', unsafe_allow_html=True)
                        
                        with col_extract3:
                            st.markdown("**⏰ 时间范围 / Time Range:**")
                            time_display = extraction_result["time_description"] if extraction_result["time_description"] else ("无时间限制" if st.session_state.language == "zh" else "No time limit")
                            st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;">{time_display}</div>', unsafe_allow_html=True)
                        
                        # 显示提取说明
                        with st.expander("📝 提取说明 / Extraction Explanation", expanded=False):
                            st.markdown(f'<div style="font-size: 14px;">{extraction_result["explanation"]}</div>', unsafe_allow_html=True)
                        
                        # 第四步：转换时间为具体日期范围
                        st.info("📅 第四步：正在转换时间范围..." if st.session_state.language == "zh" else "📅 Step 4: Converting time range...")
                        
                        filter_start_date, filter_end_date, time_desc = convert_time_to_date_range(
                            extraction_result["time_description"],
                            extraction_result["time_type"],
                            extraction_result["time_value"]
                        )
                        
                        # 显示具体的时间范围
                        st.success(f"📅 搜索时间范围: {filter_start_date.strftime('%Y-%m-%d')} 至 {filter_end_date.strftime('%Y-%m-%d')}" if st.session_state.language == "zh" else f"📅 Search time range: {filter_start_date.strftime('%Y-%m-%d')} to {filter_end_date.strftime('%Y-%m-%d')}")
                        
                        # 第五步：使用SerpApi搜索百度新闻
                        st.info("🔍 第五步：正在使用SerpApi搜索百度新闻..." if st.session_state.language == "zh" else "🔍 Step 5: Searching Baidu News with SerpApi...")
                        
                        # 使用翻译后的中文关键词进行搜索
                        news_results = search_baidu_news(translated_keywords, [], "custom", filter_start_date, filter_end_date)
                        
                        if news_results:
                            # 第六步：使用OpenAI进行格式化输出
                            st.info("🤖 第六步：正在使用OpenAI进行格式化输出..." if st.session_state.language == "zh" else "🤖 Step 6: Formatting output with OpenAI...")
                            final_result = analyze_news_with_openai(news_results, translated_keywords, [], filter_start_date, filter_end_date)
                            
                            # 显示分析结果
                            st.subheader(lang["analysis_results"])
                            st.markdown(f'<div style="font-size: 18px;">{final_result}</div>', unsafe_allow_html=True)
                            
                            # 保存结果到session state
                            st.session_state.last_custom_result = final_result
                            st.session_state.last_custom_prompt = custom_prompt
                            st.session_state.last_extraction_result = extraction_result
                            st.session_state.last_translated_keywords = translated_keywords
                            st.session_state.last_time_range = {
                                "start_date": filter_start_date,
                                "end_date": filter_end_date,
                                "description": time_desc
                            }
                        else:
                            # 如果未找到新闻
                            error_msg = "❌ 未找到相关新闻，请尝试调整搜索条件或时间范围。" if st.session_state.language == "zh" else "❌ No relevant news found, please try adjusting search conditions or time range."
                            st.subheader(lang["analysis_results"])
                            st.markdown(f'<div style="font-size: 18px;">{error_msg}</div>', unsafe_allow_html=True)
                            
                            # 保存结果到session state
                            st.session_state.last_custom_result = error_msg
                            st.session_state.last_custom_prompt = custom_prompt
                            st.session_state.last_extraction_result = extraction_result
                            st.session_state.last_translated_keywords = translated_keywords
                            st.session_state.last_time_range = {
                                "start_date": filter_start_date,
                                "end_date": filter_end_date,
                                "description": time_desc
                            }
                            
                    except Exception as e:
                        # 如果提取失败，使用传统方法
                        st.warning("⚠️ ChatGPT提取失败，使用传统方法..." if st.session_state.language == "zh" else "⚠️ ChatGPT extraction failed, using traditional method...")
                        
                        # 使用传统方法提取关键词
                        extracted_keywords, extracted_companies = extract_search_terms_from_prompt(custom_prompt)
                        
                        # 显示提取的关键词
                        st.markdown("**🔑 提取的关键词 / Extracted Keywords:**")
                        keywords_display = ", ".join(extracted_keywords) if extracted_keywords else ("无" if st.session_state.language == "zh" else "None")
                        st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;">{keywords_display}</div>', unsafe_allow_html=True)
                        
                        # 使用默认时间范围
                        current_date = datetime.now()
                        filter_start_date = current_date - timedelta(days=180)  # 约6个月
                        filter_end_date = current_date
                        
                        st.markdown("**⏰ 时间范围 / Time Range:**")
                        st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin: 5px 0;">最近6个月 / Last 6 months</div>', unsafe_allow_html=True)
                        
                        try:
                            news_results = search_baidu_news(extracted_keywords, extracted_companies, "custom", filter_start_date, filter_end_date)
                            
                            if news_results:
                                final_result = analyze_news_with_openai(news_results, extracted_keywords, extracted_companies, filter_start_date, filter_end_date)
                                
                                # 显示分析结果
                                st.subheader(lang["analysis_results"])
                                st.markdown(f'<div style="font-size: 18px;">{final_result}</div>', unsafe_allow_html=True)
                                
                                # 保存结果到session state
                                st.session_state.last_custom_result = final_result
                                st.session_state.last_custom_prompt = custom_prompt
                            else:
                                error_msg = "❌ 未找到相关新闻，请尝试调整搜索条件或时间范围。" if st.session_state.language == "zh" else "❌ No relevant news found, please try adjusting search conditions or time range."
                                st.subheader(lang["analysis_results"])
                                st.markdown(f'<div style="font-size: 18px;">{error_msg}</div>', unsafe_allow_html=True)
                                
                                st.session_state.last_custom_result = error_msg
                                st.session_state.last_custom_prompt = custom_prompt
                                
                        except Exception as e2:
                            # 如果搜索失败
                            error_msg = f"❌ 搜索失败: {str(e2)}"
                            st.subheader(lang["analysis_results"])
                            st.markdown(f'<div style="font-size: 18px;">{error_msg}</div>', unsafe_allow_html=True)
                            
                            st.session_state.last_custom_result = error_msg
                            st.session_state.last_custom_prompt = custom_prompt
        
        # 显示上次分析结果
        if 'last_custom_result' in st.session_state:
            st.markdown("---")
            st.subheader(lang["last_results"])
            
            # 显示上次搜索的参数信息
            if 'last_extraction_result' in st.session_state and 'last_time_range' in st.session_state:
                st.markdown("**📊 上次搜索参数 / Last Search Parameters:**")
                
                col_last1, col_last2, col_last3, col_last4 = st.columns(4)
                
                with col_last1:
                    st.markdown("**🔑 原始关键词 / Original Keywords:**")
                    last_original_keywords = ", ".join(st.session_state.last_extraction_result["keywords"]) if st.session_state.last_extraction_result["keywords"] else ("无" if st.session_state.language == "zh" else "None")
                    st.markdown(f'<div style="background-color: #e8f4fd; padding: 8px; border-radius: 5px; font-size: 14px;">{last_original_keywords}</div>', unsafe_allow_html=True)
                
                with col_last2:
                    st.markdown("**🇨🇳 中文关键词 / Chinese Keywords:**")
                    last_translated_keywords = ", ".join(st.session_state.last_translated_keywords) if 'last_translated_keywords' in st.session_state and st.session_state.last_translated_keywords else ("无" if st.session_state.language == "zh" else "None")
                    st.markdown(f'<div style="background-color: #e8f5e8; padding: 8px; border-radius: 5px; font-size: 14px;">{last_translated_keywords}</div>', unsafe_allow_html=True)
                
                with col_last3:
                    st.markdown("**⏰ 时间范围 / Time Range:**")
                    last_time_desc = st.session_state.last_time_range["description"]
                    st.markdown(f'<div style="background-color: #e8f4fd; padding: 8px; border-radius: 5px; font-size: 14px;">{last_time_desc}</div>', unsafe_allow_html=True)
                
                with col_last4:
                    st.markdown("**📅 具体日期 / Specific Dates:**")
                    last_start = st.session_state.last_time_range["start_date"].strftime('%Y-%m-%d')
                    last_end = st.session_state.last_time_range["end_date"].strftime('%Y-%m-%d')
                    st.markdown(f'<div style="background-color: #e8f4fd; padding: 8px; border-radius: 5px; font-size: 14px;">{last_start} ~ {last_end}</div>', unsafe_allow_html=True)
            
            with st.expander(lang["view_last_results"], expanded=False):
                st.markdown(f'<div style="font-size: 18px;">{st.session_state.last_custom_result}</div>', unsafe_allow_html=True)
                
                # 显示语言转换Prompt（如果存在）
                if 'last_custom_language_prompt' in st.session_state:
                    with st.expander(lang["language_conversion_prompt"], expanded=False):
                        st.markdown(f'<div style="font-size: 16px;">{st.session_state.last_custom_language_prompt}</div>', unsafe_allow_html=True)
    
    with tab3:
        st.header("📚 Search History" if st.session_state.language == "en" else "📚 搜索历史")
        
        if st.session_state.search_history:
            if 'selected_history_item' in st.session_state and st.session_state.selected_history_item:
                # 显示选中的历史记录详情
                history_item = st.session_state.selected_history_item
                
                # 基本信息
                st.subheader("📋 Historical Search Result Details" if st.session_state.language == "en" else "📋 Historical Search Result Details")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**{'搜索时间' if st.session_state.language == 'zh' else 'Search Time'}:** {history_item['date']}")
                    st.markdown(f"**{'关键词' if st.session_state.language == 'zh' else 'Keywords'}:** {', '.join(history_item['keywords']) if history_item['keywords'] else ('无' if st.session_state.language == 'zh' else 'None')}")
                with col2:
                    st.markdown(f"**{'公司' if st.session_state.language == 'zh' else 'Companies'}:** {', '.join(history_item['companies']) if history_item['companies'] else ('无' if st.session_state.language == 'zh' else 'None')}")
                    st.markdown(f"**{'时间范围' if st.session_state.language == 'zh' else 'Time Range'}:** {history_item['time_option']}")
                
                # 显示结果
                st.markdown("---")
                st.subheader("🔍 搜索结果" if st.session_state.language == "zh" else "🔍 Search Results")
                st.markdown(f'<div style="font-size: 18px;">{history_item["result"]}</div>', unsafe_allow_html=True)
                
                # 显示Prompt
                with st.expander("📝 生成的Prompt" if st.session_state.language == "zh" else "📝 Generated Prompt", expanded=False):
                    st.markdown(f'<div style="font-size: 16px;">{history_item["prompt"]}</div>', unsafe_allow_html=True)
            else:
                st.info("请在侧边栏选择一条历史记录以查看详情" if st.session_state.language == "zh" else "Please select a history record in the sidebar to view details")
        else:
            st.info("暂无搜索历史" if st.session_state.language == "zh" else "No search history yet")

if __name__ == "__main__":
    main()
