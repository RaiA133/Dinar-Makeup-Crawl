from google import genai
from google.genai import types
import pathlib
import httpx

# CODE INI MELAKUKAN QUERY KE GEMINI API DENGAN DOKUMEN DARI ./knowledge/dinar_makeup_LLM_Knowladge.md SEBAGAI SUMBER LLM KNOWLADGE

client = genai.Client(api_key="")

file_path = pathlib.Path('./knowledge/dinar_makeup_LLM_Knowladge.md')

# Upload File
sample_file = client.files.upload(
  file=file_path,
)

prompt="berapa harga paket bronze ?"

response = client.models.generate_content(
  model="gemini-2.5-flash",
  contents=[sample_file, prompt])
print(response.text)
