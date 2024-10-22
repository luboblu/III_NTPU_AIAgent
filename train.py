import json
import pandas as pd
from sklearn.preprocessing import LabelEncoder
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, Trainer, TrainingArguments
# 讀取 JSON 檔案
with open(r'C:\Users\盧bob\Desktop\AI Agent\response_1728979257127.json', 'r', encoding='utf-8') as f:
    traffic_data = json.load(f)
# 準備訓練數據
train_data = []
for event in traffic_data['LiveEvents']:
    train_data.append({
        'text': event['Description'],  # 事件描述作為輸入
        'label': event['Location']['Other']  # 地點作為標籤
    })
# 將資料轉換為 pandas DataFrame
df = pd.DataFrame(train_data)
# 使用 LabelEncoder 將地點（區名）轉換為數字型標籤
label_encoder = LabelEncoder()
df['label'] = label_encoder.fit_transform(df['label'])
# 使用 Hugging Face datasets 將 DataFrame 轉換為 Dataset 格式
dataset = Dataset.from_pandas(df)
# 加載 tokenizer 和模型
tokenizer = AutoTokenizer.from_pretrained("mixedbread-ai/mxbai-embed-large-v1")
model = AutoModelForSequenceClassification.from_pretrained("mixedbread-ai/mxbai-embed-large-v1", num_labels=len(label_encoder.classes_))
# 進行 tokenization
def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True)
def format_labels(examples):
    # 檢查 examples["label"] 是否已經是 int，如果是則不進行處理
    if isinstance(examples["label"], list):
        examples["label"] = [int(label) for label in examples["label"]]
    else:
        examples["label"] = int(examples["label"])  # 直接轉換為 int
    return examples
# 將數據進行 tokenization
tokenized_datasets = dataset.map(tokenize_function, batched=True)
tokenized_datasets = tokenized_datasets.map(format_labels)
training_args = TrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    evaluation_strategy="epoch",
    save_steps=10_000,
    logging_dir="./logs",
)
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets,
    eval_dataset=tokenized_datasets,  # 可以分割一些數據作為驗證集
)
# 開始訓練
trainer.train()
# 保存微調後的模型
trainer.save_model(r'C:\Users\盧bob\Desktop\AI Agent\fine_tuned_model')

