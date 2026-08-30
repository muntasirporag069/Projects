import pandas as pd
import numpy as np
import re
import torch
from sklearn.model_selection import train_test_split
from transformers import (
    BertForSequenceClassification,
    BertTokenizer,
    Trainer,
    TrainingArguments
)
from sklearn.metrics import accuracy_score , precision_recall_fscore_support
import os

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"\nUsing device: {device}")
if device.type =='cuda':
    print(f'GPU: {torch.cuda.get_device_name(0)}\n')

def preprocessing_text(text):
    if not isinstance(text,str):
        return ''
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags = re.MULTILINE)
    text = re.sub(r'\@\w+|\#' , '' , text)
    text = re.sub(r'\W',' ',text)
    text = re.sub(r'\d',' ',text)
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

class TweetDataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self,idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item['labels'] = torch.tensor(self.labels[idx])
        return item
    
    def __len__(self):
        return len(self.labels)
    
def compute_metrics(pred):
    labels = pred.label_ids
    preds = np.argmax(pred.predictions, axis = 1)
    precision , recall , f1 , _ = precision_recall_fscore_support(labels , preds , average = 'weighted')
    acc = accuracy_score(labels , preds)
    return {
        'accuracy': acc,
        'f1': f1,
        'precision': precision,
        'recall': recall
    }

def train_and_save_model(data_path = 'Tweets.csv', save_dir='bert_sentiment_model'):
    df = pd.read_csv(data_path)
    df['clean_text'] = df['text'].apply(preprocessing_text)
    df = df.dropna(subset=['clean_text','airline_sentiment'])

    sentiment_map = {'negative': 0, 'neutral': 1, 'positive': 2}
    df['label'] = df['airline_sentiment'].map(sentiment_map)

    X_train , X_test , y_train , y_test = train_test_split(
        df['clean_text'],
        df['label'], 
        test_size=0.2, 
        random_state=42,
        stratify = df['label']

    )

    tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

    train_encodings = tokenizer(
        X_train.tolist(),
        truncation=True,
        padding = True,
        max_length = 128
    )

    test_encodings = tokenizer(
        X_test.tolist(),
        truncation=True,
        padding = True,
        max_length = 128
    )

    train_dataset = TweetDataset(train_encodings , y_train.tolist())
    test_dataset = TweetDataset(test_encodings , y_test.tolist())

    model = BertForSequenceClassification.from_pretrained(
        'bert-base-uncased',
        num_labels = 3,
    ).to(device)

    training_args = TrainingArguments(
        output_dir = './results',
        per_device_train_batch_size = 16,
        per_device_eval_batch_size = 16,
        num_train_epochs = 5,
        fp16=True,
        learning_rate = 0.00002,
        weight_decay = 0.01,
        report_to = []
    )

    trainer = Trainer(
        model = model ,
        args = training_args ,
        train_dataset = train_dataset ,
        eval_dataset = test_dataset ,
        compute_metrics = compute_metrics ,
    )

    print('Starting Training...................')
    trainer.train()

    os.makedirs(save_dir , exist_ok=True)

    model.save_pretrained(save_dir)
    tokenizer.save_pretrained(save_dir)
    print(f"Model save to {save_dir}")

    torch.cuda.empty_cache()
    return model , tokenizer

if __name__ == "__main__":
    train_and_save_model()

