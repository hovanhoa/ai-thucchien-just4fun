import requests
import json
import base64

# --- Cấu hình ---
AI_API_BASE = "https://api.thucchien.ai/v1"
AI_API_KEY = "sk-LDIQS-10jQbMC7qeo7r7MQ"

# --- Gọi API để tạo hình ảnh ---
url = f"{AI_API_BASE}/images/generations"
headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {AI_API_KEY}"
}
data = {
  "model": "imagen-4",
  "prompt": "Style: Simulated VTV television news broadcast. Required content: clearly display on-screen the Vietnamese sentence: \"đây là sản phẩm của cuộc thi AI Thực Chiến\". MC: include at least one virtual presenter (master of ceremonies) wearing a T-shirt featuring the Vietnamese national flag (red with a yellow star). Setting: VTV news studio with the VTV logo visible on background screens, professional studio lighting, TV cameras, news desk. Composition: 16:9 widescreen, clean broadcast graphics (lower thirds), professional color grading, high detail, 4k",
  "n": 2, # Yêu cầu 2 ảnh
}

try:
  response = requests.post(url, headers=headers, data=json.dumps(data))
  response.raise_for_status()

  result = response.json()
  
  # --- Xử lý và lưu từng ảnh ---
  for i, image_obj in enumerate(result['data']):
      b64_data = image_obj['b64_json']
      image_data = base64.b64decode(b64_data)
      
      save_path = f"generated_image_{i+1}.png"
      with open(save_path, 'wb') as f:
          f.write(image_data)
      print(f"Image saved to {save_path}")

except requests.exceptions.RequestException as e:
  print(f"An error occurred: {e}")
  print(f"Response body: {response.text if 'response' in locals() else 'No response'}")
