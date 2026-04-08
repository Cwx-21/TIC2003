import os
import re
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from db import insert_sentiment, upsert_author_credibility
from config_loader import load_config
from asset_matcher import identify_asset as match_asset

# Load credentials
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
SESSION_NAME = 'hypecheck_session'

_URL_RE = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)

def strip_urls(text: str) -> str:
    return _URL_RE.sub('', text).strip()

# Maps announcement channel username (lowercase) → default asset symbol
CHANNEL_ASSET_FALLBACK = {
    'bitcoin':            'BTC',
    'cointelegraph':      'BTC',
    'cryptoworldnews':    'BTC',
    'cryptocurrency':     'BTC',
    'ethupdates':         'ETH',
    'whale_alert_io':     'BTC',
    'wallstreetbetslive': 'GME',
}

# Finance/crypto-specific sentiment overrides for VADER
_CRYPTO_LEXICON = {
    'bullish': 2.5,    'bearish': -2.5,
    'moon': 2.0,       'mooning': 2.0,
    'dump': -2.0,      'dumping': -2.0,
    'rekt': -2.5,      'rug': -3.0,      'rugpull': -3.0,
    'fud': -1.5,       'fomo': 1.5,
    'hodl': 1.0,       'dip': -1.0,
    'pump': 1.5,       'crash': -2.5,
    'hack': -2.5,      'exploit': -2.0,  'scam': -3.0,
    'rally': 2.0,      'surge': 2.0,     'soar': 2.5,
    'plunge': -2.0,    'whale': 0.0,
    'halving': 1.5,    'adoption': 1.5,
    'sec': -1.0,       'lawsuit': -1.5,  'ban': -2.0,
    'etf': 1.5,        'approval': 1.5,
}

class TelegramMonitor:
    def __init__(self, session_id=None):
        if not API_ID or not API_HASH:
            print("WARNING: TELEGRAM_API_ID or TELEGRAM_API_HASH not set. Telegram Monitor will be disabled.")
            self.client = None
        else:
            self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        
        self.analyzer = SentimentIntensityAnalyzer()
        self.analyzer.lexicon.update(_CRYPTO_LEXICON)
        self.config = load_config()
        self.target_channels = self.config.get('telegram_channels', [])
        self.assets = self.config['assets']
        self.session_id = session_id
        self.message_count = 0

    def identify_asset(self, text):
        """Delegates to shared asset_matcher module."""
        return match_asset(text, self.assets)

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
            if len(clean_content) < 5: return

            # Strip URLs before scoring (news messages are full of links)
            scoreable_content = strip_urls(clean_content)
            if len(scoreable_content) < 5: return

            # Identify Asset — keyword match first, then channel fallback
            asset_symbol = self.identify_asset(scoreable_content)
            if not asset_symbol:
                channel_username = getattr(event.chat, 'username', '') or ''
                asset_symbol = CHANNEL_ASSET_FALLBACK.get(channel_username.lower())
            if not asset_symbol:
                return

            # VADER Analysis on URL-stripped text
            sentiment_score = self.analyzer.polarity_scores(scoreable_content)['compound']

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

            # Flat credibility for announcement channels — source is the credibility
            credibility = 1.0

            print(f"[Telegram] {asset_symbol} | {username}: {scoreable_content[:50]}... | Score: {sentiment_score:.2f}")

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
                is_spam=False,
                is_bot=is_bot
            )

            self.message_count += 1

        except Exception as e:
            print(f"Error processing message: {e}")

if __name__ == "__main__":
    monitor = TelegramMonitor()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(monitor.start())
