import os
import asyncio
import json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from db import insert_sentiment, upsert_author_credibility
from credibility_engine import calculate_credibility

# Load credentials
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = 'hypecheck_session'

def load_config():
    """Loads assets from the JSON config."""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)

class TelegramMonitor:
    def __init__(self, session_id=None):
        if not API_ID or not API_HASH:
            print("WARNING: TELEGRAM_API_ID or TELEGRAM_API_HASH not set. Telegram Monitor will be disabled.")
            self.client = None
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.analyzer = SentimentIntensityAnalyzer()
        self.config = load_config()
        self.target_channels = self.config.get('telegram_channels', [])
        self.assets = self.config['assets']
        self.session_id = session_id
        self.message_count = 0

    def identify_asset(self, text):
        """
        Returns the asset symbol if found in text.
        """
        text_lower = text.lower()
        for asset in self.assets:
            # Check keywords
            for kw in asset['keywords']:
                if kw in text_lower:
                    return asset['symbol']
        return None  # Return None if no asset found, catch-all "CRYPTO" logic removed for precision

    async def start(self):
        if not self.client:
            print("Telegram Monitor disabled (no credentials). idling...")
            while True:
                await asyncio.sleep(3600)

        print("Starting Telegram Monitor...")
        print(f"Target Channels: {self.target_channels}")
        
        await self.client.start()
        
        # Register event handler
        @self.client.on(events.NewMessage(chats=self.target_channels))
        async def handler(event):
            await self.process_message(event)
            
        print(f"Listening on channels: {self.target_channels}")
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        try:
            content = event.message.message
            if not content: return

            # Basic Sanitization
            clean_content = content.encode('ascii', 'ignore').decode()
            if len(clean_content) < 5: return # Skip short noise

            # Identify Asset
            asset_symbol = self.identify_asset(clean_content)
            if not asset_symbol:
                return # Skip irrelevant messages

            # VADER Analysis
            sentiment_score = self.analyzer.polarity_scores(clean_content)['compound']
            
            # Meta
            sender = await event.get_sender()
            sender_id = sender.id if sender else 0
            username = sender.username if sender else "Unknown"
            is_bot = sender.bot if sender else False
            
            metadata = {
                'sender_id': sender_id, 
                'username': username, 
                'channel_id': event.chat_id,
                'is_bot': is_bot
            }

            # Credibility
            credibility = calculate_credibility('telegram', metadata, clean_content)

            print(f"[Telegram] {asset_symbol} | {username}: {clean_content[:30]}... | Score: {sentiment_score:.2f} | Cred: {credibility:.2f}")

            # DB Insert with session_id
            from datetime import datetime, timezone
            
            author_id_val = str(sender_id) if sender_id else username
            
            insert_sentiment(
                symbol=asset_symbol,
                source='telegram',
                content=clean_content,
                sentiment=sentiment_score,
                credibility=credibility,
                metadata=metadata,
                event_timestamp=datetime.now(timezone.utc),
                backtest_id=None,
                session_id=self.session_id,
                author_id=author_id_val
            )
            
            # Persist author credibility
            upsert_author_credibility(
                author_id=author_id_val,
                source='telegram',
                credibility_score=credibility,
                is_spam=(credibility < 0.3),
                is_bot=is_bot
            )
            
            self.message_count += 1

        except Exception as e:
            print(f"Error processing message: {e}")

if __name__ == "__main__":
    monitor = TelegramMonitor()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(monitor.start())
