import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.metrics import accuracy_score
import joblib

# Load data
True_df = pd.read_csv('True.csv')
False_df = pd.read_csv('Fake.csv')

True_df['label'] = 'REAL'
False_df['label'] = 'FAKE'

df = pd.concat([True_df, False_df])
df = df.sample(frac=1).reset_index(drop=True)
# Split data
X_train, X_test, y_train, y_test = train_test_split(df['text'], df['label'], test_size=0.2, random_state=7)

# Text Vectorization
tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_df=0.7)
tfidf_train = tfidf_vectorizer.fit_transform(X_train)
tfidf_test = tfidf_vectorizer.transform(X_test)

# Model Training
pac = PassiveAggressiveClassifier(max_iter=50)
pac.fit(tfidf_train, y_train)

# Test Accuracy
y_pred = pac.predict(tfidf_test)
print(f"Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")

# Save model and vectorizer
joblib.dump(pac, 'fake_news_model.pkl')
joblib.dump(tfidf_vectorizer, 'vectorizer.pkl')
