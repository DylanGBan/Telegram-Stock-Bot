from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from time import gmtime, strftime
from datetime import datetime
import stock
import Data
import os
import atexit
import logging
import zoneinfo 

load_dotenv() 

#! active tmux for this file 

BOT_TOKEN = os.environ.get("BOT_TOKEN")
SUDO = os.environ.get("SUDO")
bot = Bot(token=BOT_TOKEN)

db = Data.Data()
users = []
users_to_text = {}

atexit.register(db.close)

async def startup(application):
    global users
    users = db.startup()

    logging.info("Active Users: " + str(users))

    visited_tickers = []

    #Populating breaking news for the first time
    for user in users:
        tickers = db.get_user_tickers(user)
        for ticker in tickers:
            if ticker not in visited_tickers:
                stock.breaking_news(ticker)
                users_to_text[ticker] = []
                users_to_text[ticker].append(str(user))
                visited_tickers.append(ticker)

    # Testing:
    trigger_test = CronTrigger(minute='*')

    #? got to see if this works
    scheduler = AsyncIOScheduler()
    #Runs every weekday at 6:40am
    trigger = CronTrigger(hour=6, minute=40, day_of_week='mon-fri')
    #Runs everyday, every 25 min between 7am to 12:59pm
    trigger_news_check = CronTrigger(minute='0,20,40', hour='7-12')
    scheduler.add_job(send_morning_text, trigger)
    scheduler.add_job(check_for_breaking_news, trigger_news_check)
    scheduler.start()
    
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #When start command is issued, the chat_id is recorded to save for further texting
    chat_id = update.effective_chat.id

    if chat_id not in users: 
        db.update_user_data(chat_id)
        users.append(chat_id)
        await update.message.reply_text(f"Hi! My name is Stock! It's nice to meet you {update.message.from_user.full_name} :)"
                                    "You can use /help to get more information on what I can do!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"Hello {update.message.from_user.first_name}!", parse_mode="Markdown")

async def peek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if(len(context.args) > 1):
        await update.message.reply_text("Please insert only one valid ticker after a call to /peek command", parse_mode="Markdown")
        return
    elif(len(context.args) == 0):
        await update.message.reply_text("Please insert a valid ticker after a call to /peek command", parse_mode="Markdown")
        return

    ticker = context.args[0].upper().strip()

    if not stock.reality_of_stock(ticker):
        await update.message.reply_text(f"Ticker {ticker} is not a valid ticker!", parse_mode="Markdown")
        return 
    
    name = stock.get_stock_longname(ticker)
    price = stock.get_stock_price(ticker)

    net_change, net_change_perc = stock.stock_net_change(ticker)
    net_message = f'✅ + {net_change} (+{net_change_perc}%)' if net_change >= 0 \
        else f'❗️{net_change} ({net_change_perc}%)'

    message = f"Current price for {name} ({ticker}): {price} | {net_message}"
    await update.message.reply_text(message, parse_mode="Markdown")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    tickers = []
    for arg in context.args:
        tickers.append(arg.upper().strip())

    if not tickers:
        await update.message.reply_text("Please insert ticker(s) after a call to /add command", parse_mode="Markdown")
        return

    #Directly updating news_articles inside of add
    for ticker in tickers:
        if not stock.reality_of_stock(ticker):
            await update.message.reply_text(f"Ticker {ticker} is not a valid ticker!", parse_mode="Markdown")
            tickers.remove(ticker)
            continue
        elif ticker not in stock.news_articles.keys():
            stock.breaking_news(ticker)
            users_to_text[ticker] = [str(chat_id)]
            
    await update.message.reply_text(f"Added {' '.join(tickers)} to your morning summary!", parse_mode="Markdown")
    db.update_user_data(chat_id, tickers)
    await portfolio(update, context)


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    tickers = []
    for arg in context.args:
        tickers.append(arg.upper().strip())

    if not tickers:
        await update.message.reply_text("Please insert ticker(s) after a call to /delete command", parse_mode="Markdown")
        return

    for ticker in tickers:
        message = (f"Removed {ticker} from your portfolio" 
               if db.remove_from_user_data(chat_id, ticker) 
               else f"Couldn't find {ticker} in your portfolio")
    
        if ticker in users_to_text.keys() and str(chat_id) in users_to_text[ticker]:
            users_to_text[ticker].remove(str(chat_id))

        if not users_to_text[ticker]:
            users_to_text.pop(ticker)
            stock.news_articles.pop(ticker)

        await update.message.reply_text(message, parse_mode="Markdown")
    
    await portfolio(update, context)

async def insight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if(len(context.args) > 1):
        await update.message.reply_text("Please insert only one valid ticker after a call to /insight command", parse_mode="Markdown")
        return
    elif(len(context.args) == 0):
        await update.message.reply_text("Please insert a valid ticker after a call to /insight command", parse_mode="Markdown")
        return

    ticker = context.args[0].upper().strip()
    col, val= stock.get_current_recommendation(ticker)

    message = ['Anaylist Recommendation 🔍:\n']
    message.append('------------------------------\n')
    message.append(stock.get_recommendation(ticker))
    message.append('------------------------------\n')
    message.append(f'⚠️ Recommendation -> {col}: {val}')

    await update.message.reply_text(''.join(str(item) for item in message), parse_mode="Markdown")

async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    tickers = db.get_user_tickers(chat_id)
    
    if not tickers:
        await update.message.reply_text("Your portfolio is empty!", parse_mode="Markdown") 
        return

    message = []

    message.append("Here is your current portfolio of stocks for your morning summary!\n")
    message.append("---------------- \n")
    
    counter = 1
    for ticker in tickers:
        message.append(f"{counter}. {ticker} \n")
        counter += 1

    await update.message.reply_text(''.join(str(item) for item in message), parse_mode="Markdown")    

async def recentNews(update:Update, context: ContextTypes.DEFAULT_TYPE):

    if(len(context.args) > 1):
        await update.message.reply_text("Please insert only one valid ticker after a call to /recentNews command", parse_mode="Markdown")
        return
    elif(len(context.args) == 0):
        await update.message.reply_text("Please insert a valid ticker after a call to /recentNews command", parse_mode="Markdown")
        return

    ticker = context.args[0].upper().strip()

    if not stock.reality_of_stock(ticker):
        await update.message.reply_text(f"Ticker {ticker} is not a valid ticker!", parse_mode="Markdown")
        return 
    
    name = stock.get_stock_longname(ticker)
    feedback = stock.recent_news(ticker)
    title = feedback[0]
    url = feedback[1]

    message = (
    f"Most recent news for {name} ({ticker}):\n"
    f"----------- \n"
    f"Title: {title}\n"
    f"----------- \n"
    f"Link: {url}"
    if title is not None and url is not None
    else f"Ticker {ticker} is not a valid alias!"
    )   

    await update.message.reply_text(message, parse_mode="Markdown")

async def help(update:Update, context: ContextTypes.DEFAULT_TYPE):
    message = (
    f"Here are the following commands you can use! 📝 \n"
    f"-------------- \n"
    f'/peek "STOCK-TICKER" ~ I will give you the current price that stock is valued at. \n \n'
    f'/add "STOCK-TICKERS" ~ I will add this stock ticker to your morning summary. To add multiple please seperate by space. \n \n'
    f'/delete "STOCK-TICKERS" ~ I will delete the stock, based on your response, from your portfolio. \n \n'
    f'/recentNews "STOCK-TICKER" ~ I will give the most recent news pertaining to that stock. \n \n'
    f'/portfolio ~ I will show you the current stocks that will appear in your morning summary \n \n'
     f'/insight "STOCK-TICKER" ~ I will show you stock analyst recommendations based on the stock you insert \n \n'
    )

    await update.message.reply_text(message, parse_mode="Markdown")

async def shutdown_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(SUDO):
        await bot.sendMessage(chat_id= update.effective_chat.id, text= "Not sudo! Can't execute this command"
                              , parse_mode="Markdown")
        return

    for chat_id in users:
        await bot.sendMessage(chat_id=chat_id, text = "I will be shutting down for an update in 5 minutes! Please stop all commands!",
                              parse_mode="Markdown")
        
async def startup_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != int(SUDO):
        await bot.sendMessage(chat_id= update.effective_chat.id, text= "Not sudo! Can't execute this command"
                              , parse_mode="Markdown")
        return

    for chat_id in users:
        await bot.sendMessage(chat_id=chat_id, text = "I am back online! 🐣",
                              parse_mode="Markdown")

async def send_morning_text():
    ai_news = {}

    for chat_id in users:
        tickers = db.get_user_tickers(chat_id)

        message_summary = [f"Morning Summary! ☀️\n"]
        message_news = []

        local_zone = zoneinfo.ZoneInfo("America/Los_Angeles")
        now = datetime.now(local_zone)

        current_day_info = now.strftime("%Y-%m-%d | %H:%M:%S")
        
        for ticker in tickers:
            current_price = stock.get_stock_price(ticker)
            ticker_company = stock.get_stock_longname(ticker)
            previous_close = stock.get_previous_close(ticker)

            net_change, net_change_perc = stock.stock_net_change(ticker)
            net_message = f'✅ + {net_change} (+{net_change_perc})' if net_change >= 0 \
            else f'❗️{net_change} ({net_change_perc})'

            message_summary.append("---------------\n")
            message_summary.append(f"Stock: {ticker_company} ({ticker})\n")
            message_summary.append(f"{net_message}\n")
            message_summary.append(f"***Current Price***: {current_price}\n")
            message_summary.append(f"Prev. Close: {previous_close}\n")

        message_summary.append(" ------------------------\n")
        message_summary.append(f"| {current_day_info} | ⏰\n")
        message_summary.append(" ------------------------\n")

        message_news.append("AI news summary for the first few stocks! 📰\n" if len(tickers) >= 2 else "AI news summary! 📰\n")

        #First 4 tickers for AI news
        tickers = tickers[:4]
        for ticker in tickers:

            #Saving the same news summary for the same tickers 
            if ticker not in ai_news.keys():
                condensed_news = stock.condensed_news(ticker)
                ai_news[ticker] = condensed_news
            else:
                condensed_news = ai_news[ticker]

            message_news.append("---------------\n")
            message_news.append(f"**{stock.get_stock_longname(ticker)} ({ticker})** ~ \n" )
            message_news.append(condensed_news)

        message_summary, message_news = ''.join(str(item) for item in message_summary), ''.join(str(item) for item in message_news)

        await bot.send_message(chat_id=chat_id, text=message_summary, parse_mode="Markdown")
        await bot.send_message(chat_id=chat_id, text=message_news, parse_mode="Markdown")

async def check_for_breaking_news():

    global users_to_text

    for chat_id in users:
        tickers = db.get_user_tickers(chat_id)

        for ticker in tickers:
            if ticker not in users_to_text.keys():
                users_to_text[ticker] = []
                stock.breaking_news(ticker)

            if chat_id not in users_to_text.get(ticker):
                users_to_text[ticker].append(chat_id)

    for ticker in users_to_text.keys(): 
        feedback = stock.breaking_news(ticker)

        if feedback is not None:
            title = feedback[0]
            url = feedback[1]

            name = stock.get_stock_longname(ticker)

            message = (
            f"New article for {name} ({ticker}) has arrived:\n"
            f"----------- \n"
            f"Title: {title}\n"
            f"----------- \n"
            f"Link: {url}"
            )
        else: 
            continue
    
        for user in users_to_text[ticker]:
            await bot.send_message(chat_id=user, text=message, parse_mode="Markdown")

'''
TESTING METHODS:
'''

async def test_morning_text(update:Update, context: ContextTypes.DEFAULT_TYPE):
    for chat_id in [int(SUDO)]:
        tickers = db.get_user_tickers(chat_id)

        message_summary = [f"Morning Summary! ☀️\n"]
        message_news = []

        local_zone = zoneinfo.ZoneInfo("America/Los_Angeles")
        now = datetime.now(local_zone)

        current_day_info = now.strftime("%Y-%m-%d | %H:%M:%S")
        
        for ticker in tickers:
            current_price = stock.get_stock_price(ticker)
            ticker_company = stock.get_stock_longname(ticker)
            previous_close = stock.get_previous_close(ticker)

            net_change, net_change_perc = stock.stock_net_change(ticker)
            net_message = f'✅ + {net_change} (+{net_change_perc})' if net_change >= 0 \
            else f'❗️ - {net_change} (-{net_change_perc})'

            message_summary.append("---------------\n")
            message_summary.append(f"Stock: {ticker_company} ({ticker})\n")
            message_summary.append(f"{net_message}\n")
            message_summary.append(f"***Current Price***: {current_price}\n")
            message_summary.append(f"Prev. Close: {previous_close}\n")

        message_summary.append(" ------------------------\n")
        message_summary.append(f"| {current_day_info} | ⏰\n")
        message_summary.append(" ------------------------\n")

        message_news.append("AI news summary for the first few stocks! 📰\n" if len(tickers) >= 2 else "AI news summary! 📰\n")

        #First 4 tickers for AI news
        tickers = tickers[:4]
        for ticker in tickers:
            message_news.append("---------------\n")
            message_news.append(f"**{stock.get_stock_longname(ticker)} ({ticker})** ~ \n" )
            message_news.append(stock.condensed_news(ticker))

        message_summary, message_news = ''.join(str(item) for item in message_summary), ''.join(str(item) for item in message_news)

        await bot.send_message(chat_id=chat_id, text=message_summary, parse_mode="Markdown")
        await bot.send_message(chat_id=chat_id, text=message_news, parse_mode="Markdown")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(startup).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("peek", peek))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("delete", delete))
    app.add_handler(CommandHandler("insight", insight))
    app.add_handler(CommandHandler("portfolio", portfolio))
    app.add_handler(CommandHandler("recentNews", recentNews))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("testMorning", test_morning_text))
    app.add_handler(CommandHandler("shutdown", shutdown_announcement))
    app.add_handler(CommandHandler("startup", startup_announcement))
    app.run_polling()

if __name__ == "__main__":
    main()