# Telegram Stock Bot

[![ChatGPT][ChatGPT.com]][ChatGPT-url] &nbsp; [![Python][Python.com]][Python-url]  &nbsp; [![Pandas][Pandas.com]][Pandas-url] &nbsp; [![Telegram][Telegram.com]][Telegram-url] &nbsp; [![SQLite][SQLite.com]][SQLite-url]

### Summary:

A stock bot that is hosted on Telegram. The stock bot is coded in Python and makes use of the `yfinance` library, converting Yahoo Finance's interface into data for manipulation in Python.
This is then processed and sends users morning digests powered by OpenAI's API and keeps track of saved stock tickers per user.

> **Stock Data**:

Stock data is processed in `stock.py`, where basic ticker data like previous closing price or recent news articles are processed. This file contains functions that gather data about the stock
that is used for morning digests to the user or basic command requests from the user. Morning digests use OpenAI's API for a basic summary of the most recent news article of the morning and a
stock prediction factor of *negative*, *neutral*, or *positive*.

> **Telegram Bot + Database**:

Bot code and logistics are handled in `bot.py`. The bot is deployed on Telegram for ease of access for users. The file contains code for handling user commands, which add or remove stock tickers
for an individual's portfolio. Code is run on a local Ubuntu server to keep the bot up and running. With the use of cron, morning digests are sent to all users registered to the stock bot every morning at 6:40am PST (Monday - Friday)
and recent news articles for each user and their corresponding stock tickers are checked every 25 minutes during the operation times of the stock market. With the use of `Data.py`, a SQL database is updated with the
addition and removal of users along with the addition and removal of stocks in a corresponding user's portfolio.
  
> [!NOTE]
> This project is complete but may still recieve quality of life updates or refactoring for optimizations and readability














[ChatGPT.com]: https://img.shields.io/badge/ChatGPT-74aa9c?style=for-the-badge&logo=openai&logoColor=white
[ChatGPT-url]: https://openai.com
[Python.com]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=fff
[Python-url]: https://www.python.org
[Pandas.com]: https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=fff
[Pandas-url]: https://pandas.pydata.org
[Telegram.com]: https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white
[Telegram-url]: https://telegram.org
[SQLite.com]: https://img.shields.io/badge/SQLite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white
[SQLite-url]: https://sqlite.org
