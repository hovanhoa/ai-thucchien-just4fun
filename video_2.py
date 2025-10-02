#!/usr/bin/env python3
"""
Complete example for Veo video generation through LiteLLM proxy.

This script demonstrates how to:
1. Generate videos using Google's Veo model
2. Poll for completion status
3. Download the generated video file

Requirements:
- LiteLLM proxy running with Google AI Studio pass-through configured
- Google AI Studio API key with Veo access

# This file is forked and adapted from: https://github.com/BerriAI/litellm/blob/main/docs/my-website/docs/proxy/veo_video_generation.md .Please refer to the original for license details.
"""

import json
import os
import time
import requests
from typing import Optional
import base64


class VeoVideoGenerator:
  """Complete Veo video generation client using LiteLLM proxy."""
  
  def __init__(self, base_url: str = "https://api.thucchien.ai/gemini/v1beta", 
               api_key: str = "sk-1234"):
      """
      Initialize the Veo video generator.
      
      Args:
          base_url: Base URL for the LiteLLM proxy with Gemini pass-through
          api_key: API key for LiteLLM proxy authentication
      """
      self.base_url = base_url
      self.api_key = api_key
      self.headers = {
          "x-goog-api-key": api_key,
          "Content-Type": "application/json"
      }
  
  def generate_video(self, prompt: str) -> Optional[str]:
      """
      Initiate video generation with Veo.
      
      Args:
          prompt: Text description of the video to generate
          
      Returns:
          Operation name if successful, None otherwise
      """
      print(f"🎬 Generating video with prompt: '{prompt}'")
      
      url = f"{self.base_url}/models/veo-3.0-generate-001:predictLongRunning"

      # Read and base64-encode local image to include in request payload
      image_dict = None
      try:
          image_path = os.path.join(os.path.dirname(__file__), "generated_image_1.png")
          if os.path.exists(image_path):
              with open(image_path, "rb") as img_file:
                  encoded = base64.b64encode(img_file.read()).decode("utf-8")
              image_dict = {
                  "bytesBase64Encoded": encoded,
                  "mimeType": "image/png"
              }
          else:
              print(f"⚠️ Image not found at {image_path}. Proceeding without image.")
      except Exception as e:
          print(f"⚠️ Failed to encode image: {e}. Proceeding without image.")

      instance = {"prompt": prompt}
      if image_dict is not None:
          instance["image"] = image_dict

      payload = {
          "instances": [instance]
      }

      print(f"Payload: {json.dumps(payload, indent=2)}")
      
      try:
          response = requests.post(url, headers=self.headers, json=payload)
          response.raise_for_status()
          
          data = response.json()
          operation_name = data.get("name")
          
          if operation_name:
              print(f"✅ Video generation started: {operation_name}")
              return operation_name
          else:
              print("❌ No operation name returned")
              print(f"Response: {json.dumps(data, indent=2)}")
              return None
              
      except requests.RequestException as e:
          print(f"❌ Failed to start video generation: {e}")
          if hasattr(e, 'response') and e.response is not None:
              try:
                  error_data = e.response.json()
                  print(f"Error details: {json.dumps(error_data, indent=2)}")
              except:
                  print(f"Error response: {e.response.text}")
          return None
  
  def wait_for_completion(self, operation_name: str, max_wait_time: int = 600) -> Optional[str]:
      """
      Poll operation status until video generation is complete.
      
      Args:
          operation_name: Name of the operation to monitor
          max_wait_time: Maximum time to wait in seconds (default: 10 minutes)
          
      Returns:
          Video URI if successful, None otherwise
      """
      print("⏳ Waiting for video generation to complete...")
      
      operation_url = f"{self.base_url}/{operation_name}"
      start_time = time.time()
      poll_interval = 10  # Start with 10 seconds
      
      while time.time() - start_time < max_wait_time:
          try:
              print(f"🔍 Polling status... ({int(time.time() - start_time)}s elapsed)")
              
              response = requests.get(operation_url, headers=self.headers)
              response.raise_for_status()
              
              data = response.json()
              
              # Check for errors
              if "error" in data:
                  print("❌ Error in video generation:")
                  print(json.dumps(data["error"], indent=2))
                  return None
              
              # Check if operation is complete
              is_done = data.get("done", False)
              
              if is_done:
                  print("🎉 Video generation complete!")
                  
                  try:
                      # Extract video URI from nested response
                      video_uri = data["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
                      print(f"📹 Video URI: {video_uri}")
                      return video_uri
                  except KeyError as e:
                      print(f"❌ Could not extract video URI: {e}")
                      print("Full response:")
                      print(json.dumps(data, indent=2))
                      return None
              
              # Wait before next poll, with exponential backoff
              time.sleep(poll_interval)
              poll_interval = min(poll_interval * 1.2, 30)  # Cap at 30 seconds
              
          except requests.RequestException as e:
              print(f"❌ Error polling operation status: {e}")
              time.sleep(poll_interval)
      
      print(f"⏰ Timeout after {max_wait_time} seconds")
      return None
  
  def download_video(self, video_uri: str, output_filename: str = "generated_video.mp4") -> bool:
      """
      Download the generated video file.
      
      Args:
          video_uri: URI of the video to download (from Google's response)
          output_filename: Local filename to save the video
          
      Returns:
          True if download successful, False otherwise
      """
      print(f"⬇️  Downloading video...")
      print(f"Original URI: {video_uri}")
      
      # Convert Google URI to LiteLLM proxy URI
      # Example: https://generativelanguage.googleapis.com/v1beta/files/abc123 -> /gemini/download/v1beta/files/abc123:download?alt=media
      if video_uri.startswith("https://generativelanguage.googleapis.com/"):
          relative_path = video_uri.replace(
              "https://generativelanguage.googleapis.com/",
              ""
          )
      else:
          relative_path = video_uri

      # base_url: https://api.thucchien.ai/gemini/v1beta
      if self.base_url.endswith("/v1beta"):
          base_path = self.base_url.replace("/v1beta", "/download")
      else:
          base_path = self.base_url

      litellm_download_url = f"{base_path}/{relative_path}"
      print(f"Download URL: {litellm_download_url}")
      
      try:
          # Download with streaming and redirect handling
          response = requests.get(
              litellm_download_url, 
              headers=self.headers, 
              stream=True,
              allow_redirects=True  # Handle redirects automatically
          )
          response.raise_for_status()
          
          # Save video file
          with open(output_filename, 'wb') as f:
              downloaded_size = 0
              for chunk in response.iter_content(chunk_size=8192):
                  if chunk:
                      f.write(chunk)
                      downloaded_size += len(chunk)
                      
                      # Progress indicator for large files
                      if downloaded_size % (1024 * 1024) == 0:  # Every MB
                          print(f"📦 Downloaded {downloaded_size / (1024*1024):.1f} MB...")
          
          # Verify file was created and has content
          if os.path.exists(output_filename):
              file_size = os.path.getsize(output_filename)
              if file_size > 0:
                  print(f"✅ Video downloaded successfully!")
                  print(f"📁 Saved as: {output_filename}")
                  print(f"📏 File size: {file_size / (1024*1024):.2f} MB")
                  return True
              else:
                  print("❌ Downloaded file is empty")
                  os.remove(output_filename)
                  return False
          else:
              print("❌ File was not created")
              return False
              
      except requests.RequestException as e:
          print(f"❌ Download failed: {e}")
          if hasattr(e, 'response') and e.response is not None:
              print(f"Status code: {e.response.status_code}")
              print(f"Response headers: {dict(e.response.headers)}")
          return False
  
  def generate_and_download(self, prompt: str, output_filename: str = None) -> bool:
      """
      Complete workflow: generate video and download it.
      
      Args:
          prompt: Text description for video generation
          output_filename: Output filename (auto-generated if None)
          
      Returns:
          True if successful, False otherwise
      """
      # Auto-generate filename if not provided
      if output_filename is None:
          timestamp = int(time.time())
          safe_prompt = "".join(c for c in prompt[:30] if c.isalnum() or c in (' ', '-', '_')).rstrip()
          output_filename = f"veo_video_{safe_prompt.replace(' ', '_')}_{timestamp}.mp4"
      
      print("=" * 60)
      print("🎬 VEO VIDEO GENERATION WORKFLOW")
      print("=" * 60)
      
      # Step 1: Generate video
      operation_name = self.generate_video(prompt)
      if not operation_name:
          return False
      
      # Step 2: Wait for completion
      video_uri = self.wait_for_completion(operation_name)
      if not video_uri:
          return False
      
      # Step 3: Download video
      success = self.download_video(video_uri, output_filename)
      
      if success:
          print("=" * 60)
          print("🎉 SUCCESS! Video generation complete!")
          print(f"📁 Video saved as: {output_filename}")
          print("=" * 60)
      else:
          print("=" * 60)
          print("❌ FAILED! Video generation or download failed")
          print("=" * 60)
      
      return success


def generate_vtv_news_prompt() -> str:
    """
    Generate a comprehensive prompt for VTV-style news broadcast video.
    
    Returns:
        Detailed prompt for creating a 3-minute VTV news broadcast
    """
    return """
Professional VTV news broadcast video, 3 minutes (180 seconds), Full HD 1920x1080, MP4 format.

SETTING: Professional VTV television studio with:
- Modern news desk with VTV logo prominently displayed
- Professional lighting setup with key, fill, and back lights
- Blue and red VTV color scheme throughout
- Multiple camera angles (wide shot, medium shot, close-up)
- News ticker at bottom of screen
- Professional backdrop with subtle VTV branding

REFERENCE ASSET TO USE IN VIDEO:
- Integrate the local image file "generated_image_1.png" as an in-studio visual.
- Show it prominently on the LED wall/background screens during opening and main content.
- Use it once as a picture-in-picture on-screen graphic when the MC references visuals.
- Ensure the image is cleanly composited with correct perspective, mild screen reflections, and studio moiré suppression.

VIRTUAL MC REQUIREMENTS:
- Professional Vietnamese female news anchor, 25-35 years old
- Wearing formal business attire (dark suit, white blouse)
- Professional makeup and hairstyle
- Confident, authoritative speaking style
- Clear Vietnamese pronunciation
- Natural hand gestures and expressions
- Consistent appearance throughout the 3-minute broadcast

CONTENT STRUCTURE:
1. OPENING (0-15 seconds):
   - MC introduces: "Chào mừng quý vị và các bạn đến với bản tin đặc biệt"
   - Professional VTV studio background
   - VTV logo animation

2. MAIN CONTENT (15-165 seconds):
   - MC delivers comprehensive summary of 80th National Day (2/9/2025) celebrations
   - Cover activities across Vietnam including:
     * Official ceremonies in Hanoi
     * Local celebrations in major cities
     * Cultural performances and parades
     * Community events and festivals
     * Youth activities and educational programs
   - Include the mandatory phrase: "Đây là sản phẩm của cuộc thi AI Thực Chiến"
   - Use professional news graphics and overlays
   - Show images from Communist Party newspaper (dangcongsan.vn) as background visuals
   - Maintain professional news tone throughout

3. CLOSING (165-180 seconds):
   - MC concludes with summary statement
   - VTV sign-off with logo
   - Professional fade to black

TECHNICAL REQUIREMENTS:
- Professional broadcast quality
- Smooth camera movements and transitions
- Consistent lighting throughout
- Clear audio with MC's voice
- No copyrighted material from internet
- All visual elements must be generated, not sourced from existing videos
- Professional news graphics and text overlays
- VTV-style visual identity maintained throughout

STYLE: Authentic VTV news broadcast with professional production values, authoritative tone, and comprehensive coverage of National Day celebrations across Vietnam.
"""


def generate_vtv_news_video():
    """
    Generate the VTV-style news broadcast video using the comprehensive prompt.
    """
    # Configuration from environment or defaults
    base_url = os.getenv("LITELLM_BASE_URL", "https://api.thucchien.ai/gemini/v1beta")
    api_key = os.getenv("LITELLM_API_KEY", "sk-LDIQS-10jQbMC7qeo7r7MQ")
    
    print("🚀 Starting VTV News Broadcast Video Generation")
    print(f"📡 Using LiteLLM proxy at: {base_url}")
    
    # Initialize generator
    generator = VeoVideoGenerator(base_url=base_url, api_key=api_key)
    
    # Generate the VTV news prompt
    vtv_prompt = generate_vtv_news_prompt()
    
    print("📺 Generating VTV-style news broadcast...")
    print("=" * 60)
    print("VTV NEWS BROADCAST SPECIFICATIONS:")
    print("• Duration: 3 minutes (180 seconds)")
    print("• Format: MP4, Full HD (1920x1080)")
    print("• Style: VTV news broadcast simulation")
    print("• Content: 80th National Day celebrations summary")
    print("• MC: Virtual Vietnamese news anchor")
    print("• Studio: Professional VTV-style set")
    print("=" * 60)
    
    # Generate and download video
    output_filename = "vtv_news_broadcast_80th_national_day.mp4"
    success = generator.generate_and_download(vtv_prompt, output_filename)
    
    if success:
        print("=" * 60)
        print("🎉 SUCCESS! VTV News Broadcast generated!")
        print(f"📁 Video saved as: {output_filename}")
        print("📺 Ready for submission to AI Thực Chiến competition")
        print("=" * 60)
    else:
        print("=" * 60)
        print("❌ FAILED! Video generation failed")
        print("🔧 Check your API configuration and try again")
        print("=" * 60)
    
    return success


def main():
  """
  Example usage of the VeoVideoGenerator.
  
  Configure these environment variables:
  - LITELLM_BASE_URL: Your LiteLLM proxy URL (default: https://api.thucchien.ai/gemini/v1beta)
  - LITELLM_API_KEY: Your LiteLLM API key (default: sk-1234)
  """
  
  # Configuration from environment or defaults
  base_url = os.getenv("LITELLM_BASE_URL", "https://api.thucchien.ai/gemini/v1beta")
  api_key = os.getenv("LITELLM_API_KEY", "sk-LDIQS-10jQbMC7qeo7r7MQ")
  
  print("🚀 Starting Veo Video Generation Example")
  print(f"📡 Using LiteLLM proxy at: {base_url}")
  
  # Initialize generator
  generator = VeoVideoGenerator(base_url=base_url, api_key=api_key)
  
  # Choose which video to generate
  print("\n🎬 Choose video type:")
  print("1. VTV News Broadcast (AI Thực Chiến competition)")
  print("2. Example Cat Videos (demo)")
  
  choice = input("Enter choice (1 or 2): ").strip()
  
  if choice == "1":
      # Generate VTV news broadcast
      generate_vtv_news_video()
  else:
      # Original example prompts - consistent 4-part video series
      example_prompts = [
            "Epic cinematic shot: A majestic orange tabby cat with large white angel wings soaring through dramatic storm clouds, with WWII fighter planes rushing past at high speed, explosions in the distance. The cat has distinctive white markings on its face and chest. Dark stormy sky background with lightning. (Scene 1 of 4)",
            "Epic cinematic shot: The same orange tabby cat with white angel wings performs acrobatic maneuvers dodging missiles and weaving through thick black smoke trails as the aerial war intensifies. Same stormy sky background with lightning. The cat maintains its distinctive white face and chest markings. (Scene 2 of 4)",
            "Epic cinematic shot: Massive dogfight around the same orange tabby cat with white angel wings, bombers drop payloads, fire bursts across the stormy sky as chaos unfolds. Consistent dark stormy background with lightning. The cat's distinctive white markings remain visible. (Scene 3 of 4)",
            "Epic cinematic shot: The same orange tabby cat with white angel wings heroically flies through flaming wreckage, lightning flashes, explosions light up the stormy sky. Consistent dark stormy background. The cat's white face and chest markings are clearly visible. (Scene 4 of 4)"
      ]
      
      # Use first example or get from user
      for i, prompt in enumerate(example_prompts):
          print(f"🎬 Using prompt: '{prompt}' - {i+1}/{len(example_prompts)}")
          
          # Generate and download video
          success = generator.generate_and_download(prompt)
          
          if success:
              print("✅ Example completed successfully!")
              print("💡 Try modifying the prompt in the script for different videos!")
          else:
              print("❌ Example failed!")
              print("🔧 Check your API Configuration")

if __name__ == "__main__":
  main()
