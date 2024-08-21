import logging
from telegram import Update, InputMediaPhoto, InputMediaVideo
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as Ec
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException


loop = asyncio.get_event_loop()
executor = ThreadPoolExecutor()
TEXT = 0
MEDIA = 1

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Send me a link to insta page, I will send you back the contents of the page",
    )


def getMedia(url):
    content_urls = []
    content_media = []
    try:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            driver = webdriver.Chrome(options=options)
        except: 
            return {"Type": TEXT, "Content": "Could not access browser"}
        driver.get(url)
        # Check if the page has next button
        try:
            next_button = WebDriverWait(driver, 2).until(
                Ec.presence_of_element_located(
                    (By.XPATH, "//main//button[@aria-label='Next']")
                )
            )
            # Get all media from the page
            contents = next_button.find_elements(
                By.XPATH, "parent::div/descendant::img | parent::div/descendant::video"
            )
            content_urls += [content.get_attribute("src") for content in contents]
            while True:
                try:
                    next_button = driver.find_element(
                        By.XPATH, "//main//button[@aria-label='Next']"
                    )
                    next_button.click()
                    contents = next_button.find_elements(
                        By.XPATH,
                        "parent::div/descendant::img | parent::div/descendant::video",
                    )
                except StaleElementReferenceException:
                    break
                content_urls.append(contents[-1].get_attribute("src"))
            # get rid of duplicates
            content_urls = list(set(content_urls))
        except TimeoutException:
            pass
        # Try fetching the first image or video
        if len(content_urls) == 0:
            content = driver.find_element(By.XPATH, "//main//video | //main//img")
            content_urls.append(content.get_attribute("src"))
        for url in content_urls:
            response = requests.get(url)
            if response.status_code == 200:
                content_media.append(response.content)
        caption = driver.find_element(By.XPATH, "//main//h1")
        return {"Type": MEDIA, "Content": content_media, "Caption": caption.text}
    except requests.exceptions.InvalidSchema:
        return {"Type": TEXT, "Content": "Cannot get media"}
    except:
        return {"Type": TEXT, "Content": "Error"}
    finally:
        driver.quit()


async def Content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    templatePost = "https://www.instagram.com/p/"
    templateReels = "https://www.instagram.com/reel/"
    template = ""
    caption_max_len = 1024
    if message.startswith(templatePost):
        template = templatePost
    elif message.startswith(templateReels):
        template = templateReels
    else:
        await update.message.reply_text("Send valid URL")
        return
    end_index = message.find("/", len(template) + 1)
    message = message[:end_index:]
    answer = loop.run_in_executor(executor, getMedia, message)
    result = await answer
    if result["Type"] == TEXT:
        await update.message.reply_text(result["Content"])
    if result["Type"] == MEDIA:
        separate_message = ""
        caption = result["Caption"]
        if len(caption) > caption_max_len:
            i = caption_max_len
            if " " in caption[:caption_max_len:]:
                while caption[i] != " ":
                    i -= 1
            separate_message = caption[i::]
            caption = caption[:i:]
        medias = [
            (
                InputMediaVideo(media)
                if media.startswith(b"\x00\x00\x00 ftyp")
                else InputMediaPhoto(media)
            )
            for media in result["Content"]
        ]
        await update.message.reply_media_group(medias, caption=caption)
        if separate_message != "":
            await update.message.reply_text(separate_message)


if __name__ == "__main__":
    application = (
        ApplicationBuilder()
        .token("7123098743:AAEMNj1IUhjzWxksQlig40MPW80z9PiJ-WM")
        .build()
    )
    start_handler = CommandHandler("start", start)
    content_handler = MessageHandler(None, Content)
    application.add_handler(start_handler)
    application.add_handler(content_handler)
    application.run_polling()
