from openai import OpenAI

client = OpenAI(
    base_url='http://192.168.0.104:8765/v1',
    api_key='dummy-key'  # Any string works
)

response = client.chat.completions.create(
    model='gemini-2.5-pro',
    messages=[
        {'role': 'user', 'content': 'Hello!'}
    ],
)

print(response.choices[0].message.content)
