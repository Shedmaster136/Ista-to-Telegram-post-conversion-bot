FROM python:3
RUN apt-get update && apt-get install -y wget unzip
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install -y ./google-chrome-stable_current_amd64.deb
WORKDIR /app
COPY bot.py /app
COPY requirements.txt /app
RUN pip install --no-cache -r requirements.txt
EXPOSE 80 443
CMD ["python", "bot.py"]