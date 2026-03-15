from openai import OpenAI

client = OpenAI(
    api_key="sk-rruuhjnqawsvduyxlcqckbtgwkprctgkvwcelenooixbhthy",
    base_url="https://api.siliconflow.cn/v1"
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V3.2",
    messages=[
        {"role": "system", "content": "你是一个有用的助手"},
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
)
print(response.choices[0].message.content)
