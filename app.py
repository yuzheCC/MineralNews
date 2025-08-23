import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI

# 配置页面
st.set_page_config(
    page_title="Kimi 关键矿产新闻分析系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kimi API 配置 (根据官方示例)
# 注意：请将此处替换为您从 Kimi 开放平台申请的 API Key
KIMI_API_KEY = "sk-67dOnZAeDuB7nOF20EIM9XZapr1425A3WWuBH5jHUg4wUeql"
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
        current_date_str = current_date.strftime('%Y年%m月%d日')
        
        # 强化的系统提示，强调时间要求和新闻搜索能力
        system_prompt = f"""你是 Kimi，由 Moonshot AI 提供的人工智能助手，你更擅长中文和英文的对话。你会为用户提供安全，有帮助，准确的回答。同时，你会拒绝一切涉及恐怖主义，种族歧视，黄色暴力等问题的回答。Moonshot AI 为专有名词，不可翻译成其他语言。

🎯 新闻搜索专家模式：
你是一个专业的新闻搜索和分析专家，擅长：
- 根据关键词和公司进行精准新闻搜索
- 分析新闻的相关性和重要性
- 提供详细的新闻摘要和内容
- 智能处理时间范围和搜索策略

⚠️ 重要时间要求：
1. 当前日期是 {current_date_str}，这是唯一正确的时间基准
2. 绝对禁止使用2024年、2023年或更早的日期作为"当前时间"
3. 所有时间计算都必须基于 {current_date_str}
4. 如果用户询问"最近2周"、"最近2天"等，必须从 {current_date_str} 开始计算

🔍 新闻搜索策略：
- 优先在指定时间范围内搜索新闻
- 如果时间范围过窄导致新闻较少，可以适当扩大搜索范围
- 确保找到的新闻与搜索条件高度相关
- 提供丰富、详细的新闻信息
- 如果确实没有找到相关新闻，请明确说明

请以新闻专家的身份，为用户提供最全面、最相关的新闻分析。"""
        
        # 调用API
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,  # 提高创造性，增加找到新闻的可能性
            max_tokens=10000,  # 增加输出长度限制
        )
        
        # 返回回复内容
        return completion.choices[0].message.content
        
    except Exception as e:
        error_msg = str(e)
        if "invalid_api_key" in error_msg or "401" in error_msg:
            return "❌ API密钥无效或已过期，请更新您的Kimi API密钥"
        elif "quota" in error_msg:
            return "❌ API配额已用完，请检查您的账户余额"
        else:
            return f"❌ API调用错误: {error_msg}"

def generate_news_prompt(selected_keywords, selected_companies, time_option, custom_start_date=None, custom_end_date=None):
    """生成新闻查询的Prompt"""
    # 处理关键词和公司的显示
    if selected_keywords:
        keywords_str = "、".join(selected_keywords)
        keywords_display = f"关键词：{keywords_str}"
    else:
        keywords_display = "关键词：未指定"
    
    if selected_companies:
        # 区分预定义公司和自定义公司
        predefined_companies = [comp for comp in selected_companies if comp in COMPANIES]
        custom_companies = [comp for comp in selected_companies if comp not in COMPANIES]
        
        companies_parts = []
        if predefined_companies:
            companies_parts.append(f"预定义公司：{', '.join(predefined_companies)}")
        if custom_companies:
            companies_parts.append(f"自定义公司：{', '.join(custom_companies)}")
        
        companies_display = "；".join(companies_parts)
    else:
        companies_display = "公司：未指定"
    
    # 计算动态时间范围
    current_date = datetime.now()
    
    if time_option == "2_weeks":
        start_date = current_date - timedelta(weeks=2)
        time_str = f"最近2周（{start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}）"
    elif time_option == "2_days":
        start_date = current_date - timedelta(days=2)
        time_str = f"最近2天（{start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}）"
    else:
        time_str = f"{custom_start_date} 至 {custom_end_date}"
    
    # 根据选择情况调整Prompt内容
    if selected_keywords and selected_companies:
        search_scope = f"关于以下{keywords_display}和{companies_display}的新闻"
        relevance_instruction = "每条新闻与选中关键词和公司的相关性评分（0-1，1表示最相关）"
    elif selected_keywords:
        search_scope = f"关于以下{keywords_display}的新闻"
        relevance_instruction = "每条新闻与选中关键词的相关性评分（0-1，1表示最相关）"
    elif selected_companies:
        search_scope = f"关于以下{companies_display}的新闻"
        relevance_instruction = "每条新闻与选中公司的相关性评分（0-1，1表示最相关）"
    else:
        # 这种情况不应该发生，因为验证逻辑已经阻止了
        search_scope = "的新闻"
        relevance_instruction = "每条新闻的相关性评分（0-1，1表示最相关）"
    
    prompt = f"""请帮我查找{time_str}{search_scope}：

⚠️ 重要时间要求：
- 当前日期是 {current_date.strftime('%Y年%m月%d日')}
- 时间范围 {time_str} 是基于当前日期计算的
- 绝对不要使用2024年、2023年或更早的日期作为"当前时间"
- 请尽可能找到指定时间范围内的真实新闻，如果时间范围较窄，可以适当放宽时间限制

{keywords_display}
{companies_display}

请提供：
1. 每条新闻的标题、来源、发布时间
2. {relevance_instruction}
3. 新闻摘要
4. 新闻完整内容
5. 按相关性和时效性排序

搜索策略：
- 优先搜索指定时间范围内的新闻
- 如果指定时间范围内新闻较少，可以适当扩大搜索范围
- 确保新闻内容与关键词和公司高度相关
- 如果确实没有找到相关新闻，请说明"在指定时间范围内未找到相关新闻"

请用中文回答，格式要清晰易读，尽可能提供详细的新闻信息。"""
    
    return prompt

def main():
    st.title("🔍 Kimi 关键矿产新闻分析系统")
    st.markdown("---")
    
    # 创建两个Tab页
    tab1, tab2 = st.tabs(["📰 新闻筛选分析", "💬 自定义Prompt"])
    
    with tab1:
        st.header("📰 新闻筛选分析")
        st.markdown("请选择筛选条件，系统将调用Kimi K2模型分析相关新闻")
        st.info("💡 搜索提示：您可以选择关键词、公司或两者都选择，配合时间范围进行灵活搜索")
        
        # 创建三列布局
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("🔑 关键词选择")
            # 默认选择第一个关键词
            default_keywords = [KEYWORDS[0]]
            selected_keywords = st.multiselect(
                "选择关键词（可多选，可选）:",
                options=KEYWORDS,
                default=default_keywords,
                help="选择您感兴趣的关键矿产或相关主题，可以不选择"
            )
            
            # 自定义关键词输入
            custom_keyword = st.text_input("输入自定义关键词:", placeholder="输入其他关键词...")
            if custom_keyword and custom_keyword not in selected_keywords:
                selected_keywords.append(custom_keyword)
        
        with col2:
            st.subheader("🏢 公司选择")
            selected_companies = st.multiselect(
                "选择公司（可多选，可选）:",
                options=list(COMPANIES.keys()),
                default=[],  # 默认不选择任何公司
                help="选择您关注的公司，可以不选择"
            )
            
            # 显示选中公司的中文名称
            if selected_companies:
                st.markdown("**已选公司:**")
                for company in selected_companies:
                    if company in COMPANIES:
                        st.markdown(f"- {company}: {COMPANIES[company]}")
                    else:
                        st.markdown(f"- {company} (自定义)")
            
            # 自定义公司输入
            custom_company = st.text_input("输入自定义公司名称:", placeholder="输入其他公司名称...")
            if custom_company and custom_company not in selected_companies:
                selected_companies.append(custom_company)
        
        with col3:
            st.subheader("⏰ 时间选择")
            time_option = st.selectbox(
                "选择时间范围:",
                options=list(TIME_OPTIONS.keys()),
                index=0
            )
            
            # 显示动态时间范围
            current_date = datetime.now()
            if time_option == "最近2周":
                start_date = current_date - timedelta(weeks=2)
                st.info(f"📅 时间范围: {start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}")
            elif time_option == "最近2天":
                start_date = current_date - timedelta(days=2)
                st.info(f"📅 时间范围: {start_date.strftime('%Y年%m月%d日')} 至 {current_date.strftime('%Y年%m月%d日')}")
            
            if time_option == "自定义时间区间":
                col3a, col3b = st.columns(2)
                with col3a:
                    custom_start_date = st.date_input("开始日期:", value=datetime.now() - timedelta(days=7))
                with col3b:
                    custom_end_date = st.date_input("结束日期:", value=datetime.now())
            else:
                custom_start_date = None
                custom_end_date = None
        
        # 分析按钮
        st.markdown("---")
        if st.button("🚀 开始分析", type="primary", use_container_width=True):
            if not selected_keywords and not selected_companies:
                st.error("请至少选择一个关键词或一个公司！")
                st.warning("💡 提示：只选择时间范围无法进行有效搜索，请选择关键词或公司")
            else:
                with st.spinner("正在调用Kimi API分析新闻..."):
                    # 生成Prompt
                    prompt = generate_news_prompt(
                        selected_keywords, 
                        selected_companies, 
                        TIME_OPTIONS[time_option],
                        custom_start_date,
                        custom_end_date
                    )
                    
                    # 显示生成的Prompt
                    with st.expander("📝 生成的Prompt", expanded=False):
                        st.text(prompt)
                    
                    # 调用Kimi API
                    result = call_kimi_api(prompt)
                    
                    # 显示结果
                    st.subheader("📊 分析结果")
                    st.markdown(result)
                    
                    # 保存结果到session state
                    st.session_state.last_news_result = result
                    st.session_state.last_prompt = prompt
        
        # 显示上次分析结果
        if 'last_news_result' in st.session_state:
            st.markdown("---")
            st.subheader("📋 上次分析结果")
            with st.expander("查看上次结果", expanded=False):
                st.markdown(st.session_state.last_news_result)
    
    with tab2:
        st.header("💬 自定义Prompt")
        st.markdown("输入您的自定义Prompt，系统将调用Kimi K2模型进行分析")
        
        # 示例Prompt选择
        st.subheader("📚 示例Prompt")
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
            "选择示例Prompt:",
            options=["自定义输入"] + example_prompts,
            index=0
        )
        
        if selected_example == "自定义输入":
            custom_prompt = st.text_area(
                "输入您的Prompt:",
                placeholder="请输入您想要分析的Prompt...",
                height=150,
                help="支持中英文输入"
            )
        else:
            custom_prompt = st.text_area(
                "编辑选中的Prompt:",
                value=selected_example,
                height=150
            )
        
        # 模型选择
        model_option = st.selectbox(
            "选择模型:",
            options=["kimi-k2-turbo-preview"],
            index=0,
            help="选择Kimi模型版本 (当前可用模型)"
        )
        
        # 分析按钮
        if st.button("🔍 开始分析", type="primary", use_container_width=True):
            if not custom_prompt.strip():
                st.error("请输入Prompt内容！")
            else:
                with st.spinner("正在调用Kimi API分析..."):
                    # 调用Kimi API
                    result = call_kimi_api(custom_prompt, model_option)
                    
                    # 显示结果
                    st.subheader("📊 分析结果")
                    st.markdown(result)
                    
                    # 保存结果到session state
                    st.session_state.last_custom_result = result
                    st.session_state.last_custom_prompt = custom_prompt
        
        # 显示上次分析结果
        if 'last_custom_result' in st.session_state:
            st.markdown("---")
            st.subheader("📋 上次分析结果")
            with st.expander("查看上次结果", expanded=False):
                st.markdown(st.session_state.last_custom_result)

if __name__ == "__main__":
    main()
