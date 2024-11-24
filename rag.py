from sentence_transformers import SentenceTransformer, util
import torch
import json
import sys

# Load the embedding model
model = SentenceTransformer('TencentBAC/Conan-embedding-v1')

# Load JSON data
json_file_path = 'C:\\Users\\盧bob\\Desktop\\AI Agent\\sanxia_100_news_format.json'
with open(json_file_path, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Extract relevant fields from JSON
titles_and_descriptions = [entry['Title'] + " " + entry['Description'] for entry in data['Newses']]

# Compute embeddings for the titles and descriptions
instruction_embeddings = model.encode(titles_and_descriptions)
def split_text_into_chunks(text, chunksize=100, overlap=20):
    """Splits the text into chunks of specified size with an overlap."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunksize
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunksize - overlap  # Move start index to create overlap
    return chunks
def find_relevant_info(user_input, chunksize=100, overlap=20):
    """Find relevant traffic information from the JSON data based on user input."""
    # Split the user input into chunks
    input_chunks = split_text_into_chunks(user_input, chunksize, overlap)

    # Embed each chunk and find the highest similarity
    max_similarity = 0
    best_chunk_idx = -1

    for i, chunk in enumerate(input_chunks):
        user_input_embedding = model.encode([chunk])
        similarities = util.cos_sim(user_input_embedding, instruction_embeddings)
        max_chunk_similarity = torch.max(similarities).item()
        
        if max_chunk_similarity > max_similarity:
            max_similarity = max_chunk_similarity
            best_chunk_idx = torch.argmax(similarities).item()

    if best_chunk_idx != -1:
        # Retrieve the corresponding output
        relevant_output = data['Newses'][best_chunk_idx]
        return relevant_output
    else:
        return None

# Example usage
if __name__ == "__main__":
    user_input = input("請輸入查詢內容：")
    result = find_relevant_info(user_input)
    
    if result:
        print("\n查詢結果：")
        print(f"事件: {result['Title']}")
        print(f"描述: {result['Description']}")
        print(f"開始時間: {result['StartTime']}")
        print(f"結束時間: {result['EndTime']}")
    else:
        print("找不到相關的交通資訊。")

