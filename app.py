import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI
import re
from urllib.parse import urlparse

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
        "help_text": "Select Kimi model version",
        "error_no_keywords": "Please select at least one keyword!",
        "error_no_companies": "Please select at least one company!",
        "error_no_prompt": "Please enter prompt content!",
        "analyzing": "Analyzing with API...",
        "step1_analyzing": "🔍 Step 1: Analyzing custom prompt...",
        "step2_converting": "🔄 Step 2: Converting output language according to UI language setting...",
        "language_conversion_prompt": "🔄 Language Conversion Prompt",
        "api_key_expired": "❌ API key expired, please update your Kimi API key",
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
        "help_text": "选择Kimi模型版本",
        "error_no_keywords": "请至少选择一个关键词！",
        "error_no_companies": "请至少选择一个公司！",
        "error_no_prompt": "请输入Prompt内容！",
        "analyzing": "正在调用API分析...",
        "step1_analyzing": "🔍 第一步：正在分析自定义Prompt...",
        "step2_converting": "🔄 第二步：正在根据界面语言要求转换输出语言...",
        "language_conversion_prompt": "🔄 语言转换Prompt",
        "api_key_expired": "❌ API密钥已过期，请更新您的Kimi API密钥",
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

# Kimi API 配置 (根据官方示例)
# 注意：请将此处替换为您从 Kimi 开放平台申请的 API Key
KIMI_API_KEY = "sk-wkpkVs2LmR7menRJAabHK4te2f9QMqdIDroIsW8uw58CSUNE"
KIMI_BASE_URL = "https://api.moonshot.cn/v1"

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
    """生成新闻搜索Prompt - 第一步：获取新闻内容"""
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
    
    # 构建搜索范围
    if selected_keywords and selected_companies:
        search_scope = f"news about {keywords_display} or {companies_display}" if st.session_state.language == "en" else f"关于{keywords_display}或{companies_display}的新闻"
    elif selected_keywords:
        search_scope = f"news about {keywords_display}" if st.session_state.language == "en" else f"关于{keywords_display}的新闻"
    elif selected_companies:
        search_scope = f"news about {companies_display}" if st.session_state.language == "en" else f"关于{companies_display}的新闻"
    else:
        search_scope = "news" if st.session_state.language == "en" else "新闻"
    
    # 第一步：简化的新闻搜索Prompt
    if st.session_state.language == "en":
        prompt = f"""Please help me find {search_scope} in {time_str}.

⚠️ Important Requirements:
- Current date is {current_date.strftime('%Y-%m-%d')}
- Time range: {time_str}
- All news sources must be from China (Chinese media, websites, institutions, etc.)
- Use "OR" logic: news content is relevant if it matches ANY keyword OR ANY company
- If no news found in specified time range, expand search appropriately

{keywords_display}
{companies_display}

Please provide news analysis with the following 7 fields for each news item:
1. Title: Complete news title
2. Relevance: Relevance score (0-1, 1 being most relevant)
3. Source: News source (must be from China)
4. Source Link: URL link to the original news article (must be real and accessible)
5. Publish Time: Specific publication time (YYYY-MM-DD HH:MM)
6. Summary: Brief overview (100-200 words)
7. Full Text: Complete news content

Format each field on a separate line with blank lines between fields for readability."""
    else:
        prompt = f"""请帮我查找{time_str}{search_scope}。

⚠️ 重要要求：
- 当前日期是 {current_date.strftime('%Y年%m月%d日')}
- 时间范围：{time_str}
- 所有新闻来源必须来自中国（中国媒体、网站、机构等）
- 使用"或"逻辑：新闻内容与任一关键词或任一公司相关即可
- 如果指定时间范围内没有找到新闻，可以适当扩大搜索范围

{keywords_display}
{companies_display}

请提供新闻分析，每条新闻包含以下7个字段：
1. 标题：新闻的完整标题
2. 相关性：相关性评分（0-1，1为最相关）
3. 来源：新闻来源（必须来自中国）
4. 来源链接：原始新闻文章的URL链接（必须是真实可访问的链接）
5. 发布时间：具体发布时间（年-月-日 时:分）
6. 摘要：简要概述（100-200字）
7. 全文：新闻完整内容

每个字段单独占一行，字段之间用空行分隔，确保格式清晰易读。"""
    
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

def call_kimi_api(prompt, model="kimi-k2-turbo-preview"):
    """调用Kimi API (使用官方OpenAI客户端)"""
    try:
        # 初始化OpenAI客户端
        client = OpenAI(
            api_key=KIMI_API_KEY,
            base_url=KIMI_BASE_URL,
        )
        
        # 获取当前日期，用于系统提示
        current_date = datetime.now()
        if st.session_state.language == "zh":
            current_date_str = current_date.strftime('%Y年%m月%d日')
        else:
            current_date_str = current_date.strftime('%Y-%m-%d')
        
        # 根据语言设置系统提示
        if st.session_state.language == "zh":
            system_prompt = f"""你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。

🎯 新闻搜索专家模式：
你是一个专业的新闻搜索和分析专家，擅长：
- 根据关键词和公司进行精准新闻搜索
- 分析新闻的相关性和重要性
- 提供详细的新闻摘要和内容
- 智能处理时间范围和搜索策略

⚠️ 重要时间要求：
- 当前日期是 {current_date_str}
- 绝对不要使用2024年、2023年或更早的日期作为"当前时间"
- 请尽可能找到指定时间范围内的真实新闻

⚠️ 重要输出格式要求：
每条新闻必须严格按照以下7项固定格式输出，不能缺少任何一项：

1. **Title（标题）**：新闻的完整标题
2. **Relevance（相关性）**：相关性评分（0-1，1为最相关）
3. **Source（来源）**：新闻来源必须来自中国（中国媒体、网站、机构等）
4. **Source Link（来源链接）**：原始新闻文章的URL链接（必须是真实可访问的链接）
5. **Publish Time（发布时间）**：新闻发布的具体时间（年-月-日 时:分）
6. **Summary（摘要）**：新闻的简要概述（100-200字）
7. **Full Text（全文）**：新闻的完整内容

⚠️ 字段标签显示要求：
所有字段标签（Title、Relevance、Source、Source Link、Publish Time、Summary、Full Text）必须使用红色加粗字体显示，格式为：<span style="color: #ff0000; font-weight: bold;">**字段名** ： </span>

⚠️ Source Link 特殊要求：
- 必须提供真实可访问的新闻链接
- 链接格式应该是标准的HTTP/HTTPS URL
- 如果无法提供真实链接，请使用"链接暂不可用"或"Link not available"
- 避免生成虚构的URL或示例链接

⚠️ 格式要求：
每个字段必须单独占一行，字段之间必须有空行分隔，确保格式清晰易读。

搜索策略：
- 优先搜索指定时间范围内的新闻
- 如果指定时间范围内新闻较少，可以适当扩大搜索范围
- **重要**：使用"或"逻辑搜索，即新闻内容与任一关键词或任一公司相关即可
- 确保新闻内容与关键词或公司高度相关
- **重要**：所有新闻来源必须来自中国（中国媒体、网站、机构等）
- 如果确实没有找到相关新闻，请说明"在指定时间范围内未找到相关新闻"

⚠️ 链接质量要求：
- 优先提供来自知名中国媒体的真实新闻链接
- 确保链接格式正确且可访问
- 如果无法验证链接真实性，请明确标注"链接需要验证"

请用中文回答，严格按照上述7项固定格式输出每条新闻。"""
        else:
            system_prompt = f"""You are Kimi, an AI assistant provided by Moonshot AI. You are better at Chinese and English conversations. You will provide users with safe, helpful, and accurate answers. At the same time, you will refuse to answer any questions involving terrorism, racial discrimination, pornography, violence, etc. Moonshot AI is a proper noun and cannot be translated into other languages.

🎯 News Search Expert Mode:
You are a professional news search and analysis expert, skilled in:
- Precise news search based on keywords and companies
- Analyzing news relevance and importance
- Providing detailed news summaries and content
- Intelligently handling time ranges and search strategies

⚠️ Important Time Requirements:
- Current date is {current_date_str}
- Absolutely do not use dates from 2024, 2023, or earlier as "current time"
- Please try to find real news within the specified time range

⚠️ Important Output Format Requirements:
Each news item must strictly follow the following 7 fixed format items, without missing any:

1. **Title**: Complete news title
2. **Relevance**: Relevance score (0-1, 1 being most relevant)
3. **Source**: News source must be from China (Chinese media, websites, institutions, etc.)
4. **Source Link**: URL link to the original news article (must be real and accessible, format like: https://www.example.com/news/2024/01/01/article.html)
5. **Publish Time**: Specific publication time (YYYY-MM-DD HH:MM)
6. **Summary**: Brief overview (100-200 words)
7. **Full Text**: Complete news content

⚠️ Field Label Display Requirements:
All field labels (Title, Relevance, Source, Source Link, Publish Time, Summary, Full Text) must use red bold font, formatted as: <span style="color: #ff0000; font-weight: bold;">**Field Name** ：</span>

⚠️ Source Link Special Requirements:
- Must provide real and accessible news links
- Link format should be standard HTTP/HTTPS URL
- If unable to provide real links, use "Link not available" or "链接暂不可用"
- Avoid generating fictional URLs or example links

⚠️ Format Requirements:
Each field must be on a separate line, with blank lines between fields to ensure clear and readable formatting.

Search Strategy:
- Prioritize news within the specified time range
- If there are fewer news items in the specified time range, you can appropriately expand the search scope
- **Important**: Use "OR" logic for search, meaning news content is relevant if it matches ANY keyword OR ANY company
- Ensure news content is highly relevant to keywords or companies
- **Important**: All news sources must be from China (Chinese media, websites, institutions, etc.)
- If no relevant news is found, please state "No relevant news found in the specified time range"

⚠️ Link Quality Requirements:
- Prioritize providing real news links from well-known Chinese media
- Ensure link format is correct and accessible
- If unable to verify link authenticity, clearly mark as "Link needs verification"

Please answer in English, strictly following the above 7 fixed format items for each news item."""
        
        # 调用API
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=10000
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "unauthorized" in error_msg.lower():
            return "❌ API调用失败: 您的API密钥已过期或无效，请检查API密钥设置。"
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            return "❌ API调用失败: 已达到API调用配额限制，请稍后再试。"
        else:
            return f"❌ API调用失败: {error_msg}"

def main():
    st.title(lang["title"])
    st.markdown("---")
    
    # 创建三个Tab页
    tab1, tab2, tab3 = st.tabs([lang["tab1_title"], lang["tab2_title"], "📚 Search History" if st.session_state.language == "en" else "📚 搜索历史"])
    
    with tab1:
        st.header(lang["tab1_title"])
        st.markdown("Please select filtering criteria, the system will call Kimi K2 model to analyze related news" if st.session_state.language == "en" else "请选择筛选条件，系统将调用Kimi K2模型分析相关新闻")
        st.markdown('<div style="font-size: 16px;">💡 Search Tip: You can choose keywords, companies, or both, combined with time range for flexible search</div>' if st.session_state.language == "en" else '<div style="font-size: 16px;">💡 搜索提示：您可以选择关键词、公司或两者都选择，配合时间范围进行灵活搜索</div>', unsafe_allow_html=True)
        
        # 创建三列布局
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader(lang["keywords_title"])
            # 动态获取当前语言的选项
            localized_options = get_localized_options()
            current_keywords = localized_options["keywords"]
            
            # 默认选择第一个关键词
            default_keywords = [current_keywords[0]] if current_keywords else []
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
                    
                    # 第一步：调用Kimi API获取新闻内容
                    st.info("🔍 第一步：正在搜索新闻内容..." if st.session_state.language == "zh" else "🔍 Step 1: Searching for news content...")
                    news_result = call_kimi_api(news_prompt)
                    
                    # 第二步：根据UI语言要求进行语言转换
                    if news_result and not news_result.startswith("❌"):
                        st.info("🔄 第二步：正在根据界面语言要求转换输出语言..." if st.session_state.language == "zh" else "🔄 Step 2: Converting output language according to UI language setting...")
                        
                        # 生成语言转换Prompt
                        language_prompt = generate_language_conversion_prompt(news_result, st.session_state.language)
                        
                        # 调用Kimi API进行语言转换
                        final_result = call_kimi_api(language_prompt)
                        
                        # 显示最终结果
                        st.subheader(lang["analysis_results"])
                        st.markdown(f'<div style="font-size: 18px;">{final_result}</div>', unsafe_allow_html=True)
                        
                        # 保存结果到session state
                        st.session_state.last_news_result = final_result
                        st.session_state.last_prompt = news_prompt
                        st.session_state.last_language_prompt = language_prompt
                        
                        # 添加到历史记录
                        add_to_history(selected_keywords, selected_companies, time_option, final_result, news_prompt)
                    else:
                        # 如果第一步失败，直接显示错误
                        st.subheader(lang["analysis_results"])
                        st.markdown(f'<div style="font-size: 18px;">{news_result}</div>', unsafe_allow_html=True)
                        
                        # 保存结果到session state
                        st.session_state.last_news_result = news_result
                        st.session_state.last_prompt = news_prompt
                        
                        # 添加到历史记录（即使失败也记录）
                        add_to_history(selected_keywords, selected_companies, time_option, news_result, news_prompt)
        
        # 显示上次分析结果
        if 'last_news_result' in st.session_state:
            st.markdown("---")
            st.subheader(lang["last_results"])
            with st.expander(lang["view_last_results"], expanded=False):
                st.markdown(f'<div style="font-size: 18px;">{st.session_state.last_news_result}</div>', unsafe_allow_html=True)
    
    with tab2:
        st.header(lang["tab2_title"])
        st.markdown("Input your custom prompt, the system will call Kimi K2 model for analysis" if st.session_state.language == "en" else "输入您的自定义Prompt，系统将调用Kimi K2模型进行分析")
        
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
            options=["kimi-k2-turbo-preview"],
            index=0,
            help=lang["help_text"]
        )
        
        # 分析按钮
        if st.button(lang["analyze_button"], type="primary", use_container_width=True):
            if not custom_prompt.strip():
                st.markdown(f'<div style="font-size: 16px; color: #ff4b4b;">{lang["error_no_prompt"]}</div>', unsafe_allow_html=True)
            else:
                with st.spinner(lang["analyzing"]):
                    # 第一步：调用Kimi API获取分析结果
                    st.info(lang["step1_analyzing"])
                    initial_result = call_kimi_api(custom_prompt, model_option)
                    
                    # 第二步：根据UI语言要求进行语言转换
                    if initial_result and not initial_result.startswith("❌"):
                        st.info(lang["step2_converting"])
                        
                        # 生成语言转换Prompt
                        language_prompt = generate_language_conversion_prompt(initial_result, st.session_state.language)
                        
                        # 调用Kimi API进行语言转换
                        final_result = call_kimi_api(language_prompt, model_option)
                        
                        # 显示最终结果
                        st.subheader(lang["analysis_results"])
                        st.markdown(f'<div style="font-size: 18px;">{final_result}</div>', unsafe_allow_html=True)
                        
                        # 保存结果到session state
                        st.session_state.last_custom_result = final_result
                        st.session_state.last_custom_prompt = custom_prompt
                        st.session_state.last_custom_language_prompt = language_prompt
                    else:
                        # 如果第一步失败，直接显示错误
                        st.subheader(lang["analysis_results"])
                        st.markdown(f'<div style="font-size: 18px;">{initial_result}</div>', unsafe_allow_html=True)
                        
                        # 保存结果到session state
                        st.session_state.last_custom_result = initial_result
                        st.session_state.last_custom_prompt = custom_prompt
        
        # 显示上次分析结果
        if 'last_custom_result' in st.session_state:
            st.markdown("---")
            st.subheader(lang["last_results"])
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
