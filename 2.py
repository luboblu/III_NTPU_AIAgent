import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# 設定模型和檔案路徑
model_path = "C:\\Users\\盧bob\\Desktop\\AI Agent\\model"  # 替換為你的GGUF模型路徑

# 載入模型和分詞器
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16)  # 使用 float16 可減少記憶體佔用
tokenizer = AutoTokenizer.from_pretrained(model_path)

# 將模型移至 GPU（如果可用）
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# 定義測試文本
input_text = "請跟我說三峽區學府路的交通狀況"

# 將輸入文本轉換為張量
inputs = tokenizer(input_text, return_tensors="pt").to(device)

# 使用模型生成文本
with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=50,  # 設置生成的最大token數量
        temperature=0.7,    # 設定溫度以控制生成的隨機性
        top_p=0.9,          # 使用 nucleus sampling
        do_sample=True      # 啟用取樣生成
    )

# 解碼生成的文本
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
print("生成的文本: ", generated_text)
