import requests
import json

# --- Cấu hình ---
AI_API_BASE = "https://api.thucchien.ai"
AI_API_KEY = "sk-kaN6PBxQdaPJI04ntb7-wA" # Thay bằng API key của bạn

# --- Thực thi ---
url = f"{AI_API_BASE}/chat/completions"
headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {AI_API_KEY}"
}
data = {
  "model": "gemini-2.5-flash",
  "messages": [
      {
          "role": "user",
          "content": "What are the main benefits of using LiteLLM?"
      }
  ],
  "temperature": 0.7
}

response = requests.post(url, headers=headers, data=json.dumps(data))

if response.status_code == 200:
  result = response.json()
  print(result['choices'][0]['message']['content'])
else:
  print(f"Error: {response.status_code}")
  print(response.text)
