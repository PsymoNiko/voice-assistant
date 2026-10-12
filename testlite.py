import openai

client = openai.OpenAI(
	api_key="4ed0048cf417426ee0fd88441d3324e1766245f8b4d367ddbeb9c922e1e57a3c",
	base_url="http://127.0.0.1:4000"
)

import base64

# Helper function to encode images to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Example with text only
response = client.chat.completions.create(
    model="coding",
    messages=[
    {
        "role": "user",
        "content": "Hello, how are you?"
    }
]
)

print(response)

# Example with image or PDF (uncomment and provide file path to use)
# base64_file = encode_image("path/to/your/file.jpg")  # or .pdf
# response_with_file = client.chat.completions.create(
#     model="coding",
#     messages=[
#         {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "Hello, how are you?"
#                 },
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url": f"data:image/jpeg;base64,{base64_file}"  # or data:application/pdf;base64,{base64_file}
#                     }
#                 }
#             ]
#         }
#     ]
# )
# print(response_with_file)

