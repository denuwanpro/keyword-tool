from flask import Flask, render_template, request, redirect, url_for, flash
from pytrends.request import TrendReq
import pandas as pd
import time
import random
from pytrends.exceptions import TooManyRequestsError

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Fetch data function with retry mechanism
def fetch_data(keywords, country):
    pytrends = TrendReq(hl='en-US', tz=360)
    result = []
    max_retries = 5
    delay = 10

    for _ in range(max_retries):
        try:
            pytrends.build_payload(keywords, cat=0, timeframe='now 7-d', geo=country, gprop='')
            related_queries = pytrends.related_queries()
            
            for keyword in related_queries:
                keyword_data = {
                    'keyword': keyword,
                    'rising': [],
                    'top': []
                }
                
                # Fetch rising queries
                rising_queries = related_queries[keyword]['rising']
                if rising_queries is not None:
                    for i, row in rising_queries.head(50).iterrows():
                        keyword_data['rising'].append({'query': row['query'], 'value': row['value']})
                
                # Fetch top queries
                top_queries = related_queries[keyword]['top']
                if top_queries is not None:
                    for i, row in top_queries.head(50).iterrows():
                        keyword_data['top'].append({'query': row['query'], 'value': row['value']})
                
                result.append(keyword_data)
            
            return result

        except TooManyRequestsError:
            time.sleep(delay)
            delay += random.randint(1, 10)  # Increment delay and add a random factor

    flash('Failed to fetch data after multiple attempts due to rate limiting.')
    return result

# Home route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keywords = request.form['keywords'].split(',')
        country = request.form['country']
        
        if not keywords or not country:
            flash('Please enter keywords and select a country.')
            return redirect(url_for('index'))
        
        data = fetch_data(keywords, country)
        return render_template('index.html', data=data, keywords=keywords, country=country)
    
    return render_template('index.html', data=None)

# Route to export data to CSV
@app.route('/export', methods=['POST'])
def export():
    data = request.form['data']
    if not data:
        flash('No data to export.')
        return redirect(url_for('index'))
    
    data = eval(data)
    df_list = []
    for entry in data:
        df = pd.DataFrame(entry['rising'])
        df['keyword'] = entry['keyword']
        df['type'] = 'rising'
        df_list.append(df)
        
        df = pd.DataFrame(entry['top'])
        df['keyword'] = entry['keyword']
        df['type'] = 'top'
        df_list.append(df)
    
    final_df = pd.concat(df_list)
    final_df.to_csv('keyword_data.csv', index=False)
    flash('Data exported to keyword_data.csv successfully.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
