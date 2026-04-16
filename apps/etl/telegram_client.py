"""
Telegram Monitor

Listens to a configured set of Telegram channels using the Telethon async client
and processes incoming messages in real-time. For each message, the monitor:
  1. Sanitises and filters the raw text.
  2. Identifies the relevant tracked asset via keyword matching.
  3. Computes a VADER compound sentiment score.
  4. Scores the author's credibility via the credibility engine.
  5. Persists the sentiment record and updates author reputation in PostgreSQL.

The event handler registered via @client.on(events.NewMessage) follows the
Observer pattern — Telethon acts as the subject and TelegramMonitor.process_message
is the concrete observer callback.
"""

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
    """
    Loads the asset registry and Telegram channel list from config/assets.json.

    Returns:
        dict: Parsed JSON config with 'assets' and 'telegram_channels' keys.
    """
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'assets.json')
    with open(config_path, 'r') as f:
        return json.load(f)


class TelegramMonitor:
    """
    Real-time Telegram message listener and sentiment processor.

    Connects to the Telegram API via Telethon and registers an event handler
    (Observer pattern) that fires on every new message in the configured channels.
    If credentials are absent, the monitor idles gracefully rather than crashing.

    Attributes:
        client (TelegramClient | None): Telethon client, or None if unconfigured.
        analyzer (SentimentIntensityAnalyzer): VADER sentiment scorer.
        target_channels (list[str]): Telegram channel identifiers to subscribe to.
        assets (list[dict]): Active asset configs used for keyword matching.
        session_id (int | None): ID of the active live_sessions record.
        message_count (int): Running count of successfully processed messages.
    """

    def __init__(self, session_id=None):
        """
        Initialises the monitor. Skips Telethon setup if API credentials are missing.

        Args:
            session_id (int, optional): Live session ID to tag sentiment records with.
        """
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
        Identifies the tracked asset mentioned in a message via keyword matching.

        Iterates over all configured assets and checks whether any keyword
        appears (case-insensitive) in the message text. Returns the first match.

        Args:
            text (str): The sanitised message content to search.

        Returns:
            str | None: The matched asset symbol (e.g., 'BTC'), or None if no match.
        """
        text_lower = text.lower()
        for asset in self.assets:
            # Check keywords
            for kw in asset['keywords']:
                if kw in text_lower:
                    return asset['symbol']
        return None  # Return None if no asset found, catch-all "CRYPTO" logic removed for precision

    async def start(self):
        """
        Starts the Telethon client and registers the NewMessage event handler.

        If the client is not configured (missing credentials), idles indefinitely
        to keep the event loop alive without disrupting other async tasks.
        """
        if not self.client:
            print("Telegram Monitor disabled (no credentials). idling...")
            while True:
                await asyncio.sleep(3600)

        print("Starting Telegram Monitor...")
        print(f"Target Channels: {self.target_channels}")

        await self.client.start()

        # Register event handler — Observer pattern: Telethon notifies on NewMessage
        @self.client.on(events.NewMessage(chats=self.target_channels))
        async def handler(event):
            await self.process_message(event)

        print(f"Listening on channels: {self.target_channels}")
        await self.client.run_until_disconnected()

    async def process_message(self, event):
        """
        Processes a single incoming Telegram message.

        Performs sanitisation, asset identification, VADER sentiment scoring,
        credibility calculation, and database persistence. Short or irrelevant
        messages are discarded early to reduce noise.

        Args:
            event: Telethon NewMessage event object.
        """
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
