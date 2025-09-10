from openai import OpenAI
from time import gmtime, strftime
from dotenv import load_dotenv
from newspaper import Article
from datetime import datetime
import yfinance as yf
import pandas as pd
import os
import logging
import zoneinfo 

load_dotenv()

client_ai = OpenAI(os.environ.get("OPENAI_API_KEY"))
news_articles = {}


#! for filtering out prem news:
# free_article = False
#         news = stock.news

#         #checking and filtering out premium news
#         while not free_article :
#             newest_paper = max(news, key=lambda a: a['content']['pubDate'])

#             prem_news = newest_paper.get("content").get("finance").get("premiumFinance").get("isPremiumNews")
#             prem_news_for_free = newest_paper.get("content").get("finance").get("premiumFinance").get("isPremiumFreeNews")

#             if prem_news and prem_news_for_free or not prem_news:
#                 free_article = True
#             else:
#                 news.remove(newest_paper)



# def stock_news(stock):
#     urls = []
#     full_news = ""

#     news_info = []
#     news = stock.news
#     articles = news[:3]

#     for article in articles:
#         title = article.get("content").get("title")
#         url = article.get("content").get("clickThroughUrl").get("url")
#         urls.append(url)
#         news_info.append(f"Title: {title} | URL: {url}\n")
        
#     full_news = ''.join(str(item) for item in news_info)

#     return urls, full_news

# def summarize_full_news(ticker):

#     feedback = []

#     stock = yf.Ticker(ticker)
#     company_name = stock.info.get('longName', ticker)
#     urls, full_news = stock_news(stock)

#     for url in urls:
#         article = Article(url)
#         article.download()
#         article.parse()
#         content = article.text

#         prompt = (
#         f"Summarize the following news article in 2-3 sentences. "
#         f"Then give stock impact prediction only on {company_name} (Positive, Negative, Neutral):\n\n{content}"
#         f"The format should be: Summary: 'summary' | Predicition: 'predicition' "
#         )

#         response = client_ai.responses.create(
#             model="gpt-4",
#             input=[{"role": "user", "content": prompt}]
#         )
        
#         feedback.append(response.output_text + "\n")
#         feedback.append("\n")
    
#     return "".join(str(item) for item in feedback)

def get_stock_longname(ticker):
    return yf.Ticker(ticker).info.get('longName', ticker)

def get_stock_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        price = round(stock.fast_info["lastPrice"],2)
    except (Exception, KeyError) as e:
        price = None
        
    return price

def get_previous_close(ticker):
    return round(yf.Ticker(ticker).fast_info.get('regularMarketPreviousClose'), 2)

def get_recommendation(ticker):
    stock = yf.Ticker(ticker)
    
    data = pd.DataFrame(stock.recommendations_summary)
    data = data.drop('period', axis=1)
    data = data.rename(columns={'strongBuy':'Strong Buy', 'buy':'Buy', 'hold':'Hold', 'sell':'Sell', 'strongSell':'Strong Sell'})
    data.index = ['Current Month', '1 Month Ago', '2 Months Ago']

    lines = []
    for idx, row in data.iterrows():
        lines.append(f"{idx}:")
        for col, val in row.items():
            lines.append(f"    {col}: {val}")
        lines.append("")  

    return "\n".join(lines)

def get_current_recommendation(ticker):
    stock = yf.Ticker(ticker)
    
    data = pd.DataFrame(stock.recommendations_summary)
    data = data.drop('period', axis=1)
    data = data.rename(columns={'strongBuy':'Strong Buy', 'buy':'Buy', 'hold':'Hold', 'sell':'Sell', 'strongSell':'Strong Sell'})
    data.index = ['Current Month', '1 Month Ago', '2 Months Ago']

    row = data.iloc[[0]]
    row_series = row.iloc[0]

    max_col = row_series.idxmax() 
    max_val = row_series.max()   

    return max_col, str(max_val)

def stock_net_change(ticker):
    stock = yf.Ticker(ticker)
    previous_close = round(stock.fast_info.get('regularMarketPreviousClose'),2)
    current_price = get_stock_price(ticker)

    net_change = round(current_price - previous_close, 2)
    net_change_perc = round(((current_price / previous_close) - 1) * 100, 2)

    return net_change, net_change_perc

def reality_of_stock(ticker):
    stock = yf.Ticker(ticker)
    try:
        vals = stock.fast_info.values()
    except KeyError as e:
        return False
    
    return True

def recent_news(ticker):
    global newest_paper

    #Confusing naming but stock is either a yf.Ticker type or string (overloading)
    stock = yf.Ticker(ticker)

    try:
        newest_paper = max(stock.news, key=lambda a: a['content']['pubDate'])

        prem_news = newest_paper.get("content").get("finance").get("premiumFinance").get("isPremiumNews")
        prem_news_for_free = newest_paper.get("content").get("finance").get("premiumFinance").get("isPremiumFreeNews")

        if prem_news and prem_news_for_free or not prem_news:
            free_article = True
        else:
            free_article = False
        
        title = newest_paper.get("content").get("title")

        if newest_paper.get("content").get("clickThroughUrl") is None:
            url = newest_paper.get("content").get("canonicalUrl").get("url")
            free_article = False
        else:
            url = newest_paper.get("content").get("clickThroughUrl").get("url")

        date = newest_paper.get('content').get('pubDate').split('T')[0]
        id = newest_paper.get('id')

        #Setting the most recent paper to corresponding ticker
        newest_paper[stock.ticker] = id
    except Exception as e:
        logging.error("Error in recent_news(): ", e)
        title = None
        url = None
        date =  None
        free_article = None
        id = None

    return title, url, date, free_article, id

def condensed_news(ticker):
    stock = yf.Ticker(ticker)
    company_name = stock.info.get('longName', ticker)
    title, url, date, free_article, id = recent_news(ticker)

    if not free_article:
        message = (
            f"The most recent news article for {company_name} ({ticker}) is a premimum article.\n"
            f"I cannot give you my insight on the article! Here is the title and url for the article.\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"{date}\n"
        )

        return message

    article = Article(url)
    article.download()
    article.parse()
    content = article.text

    prompt = (
    f"Summarize the following news article in 2-3 sentences."
    f"Then give stock impact prediction only on {company_name} (Positive, Negative, Neutral):\n\n{content}"
    f"The format should be: Summary: 'summary' | Predicition: 'predicition' "
    )

    response = client_ai.responses.create(
        model="gpt-4",           
        input=[{"role": "user", "content": prompt}]
    )

    return response.output_text + f"\n {date} \n" 

def breaking_news(ticker):
    global news_articles
    
    feedback = recent_news(ticker)
    title = feedback[0]
    url = feedback[1]
    newspaper_id = feedback[4]

    if ticker not in news_articles.keys():
        news_articles[ticker] = newspaper_id
        # print(f"Added {ticker} to breaking news watch")
    else:
        if str(newspaper_id) != news_articles[ticker]:
            news_articles[ticker] = newspaper_id
            return title, url

    return None

def summarize_stock(ticker):
    stock = yf.Ticker(ticker)

    current_day_info = strftime("%Y-%m-%d | %H:%M:%S", gmtime())
    current_price = round(stock.fast_info["lastPrice"],2)
    ticker_company = stock.info.get('longName', ticker)

    message =(
        f"Stock: {ticker_company} ({ticker})\n"
        f"***Current Price***: {current_price}\n"
        f"Prev. Close: {stock.fast_info['regularMarketPreviousClose']}\n"
        f"Current Date & 24-Time: {current_day_info}"
        )
    
def hot_stock():
        
    feedback = []
    prompt = (
    f"Summarize the following news article in 2-3 sentences. "
    f"Then give stock impact prediction only on {company_name} (Positive, Negative, Neutral):\n\n{content}"
    f"The format should be: Summary: 'summary' | Predicition: 'predicition' "
    )

    response = client_ai.responses.create(
        model="gpt-4",
        input=[{"role": "user", "content": prompt}]
    )
        
    feedback.append(response.output_text + "\n")
    feedback.append("\n")

    return feedback