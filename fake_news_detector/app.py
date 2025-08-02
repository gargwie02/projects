from flask import Flask, render_template, request
import joblib

app = Flask(__name__)

model = joblib.load('fake_news_model.pkl')
vectorizer = joblib.load('vectorizer.pkl')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    news_text = request.form['news_text']
    vectorized_input = vectorizer.transform([news_text])
    prediction = model.predict(vectorized_input)
    
    return render_template('index.html', prediction_text=f"The news is: {prediction[0]}")

if __name__ == "__main__":
    app.run(debug=True)
