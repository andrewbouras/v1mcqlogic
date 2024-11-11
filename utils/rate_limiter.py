import tiktoken
import time
from collections import deque
from flask import current_app
import logging
class AdaptiveRateLimiter:
    def __init__(self, total_tokens_per_minute):
        self.total_tokens_per_minute = total_tokens_per_minute
        self.endpoint_limits = {
            'qa_generation': 400000,
            'mcq_generation': 400000,
            'default': 200000
        }
        self.endpoint_queues = {endpoint: deque() for endpoint in self.endpoint_limits}
        self.last_reset = time.time()
        self.usage_history = deque(maxlen=60)  # Store last 60 seconds of usage
        self.encoder = None

    def get_encoder(self):
        if self.encoder is None:
            try:
                from flask import current_app
                encoding_name = current_app.config['TOKEN_ENCODING']
                logging.info(f"Initializing encoder with encoding: {encoding_name}")
                self.encoder = tiktoken.get_encoding(encoding_name)
            except Exception as e:
                logging.error(f"Error initializing encoder: {str(e)}")
                raise
        return self.encoder

    def count_tokens(self, text):
        try:
            encoder = self.get_encoder()
            return len(encoder.encode(text))
        except Exception as e:
            logging.error(f"Error in count_tokens: {str(e)}")
            raise
    def add_request(self, endpoint, text):
        tokens = self.count_tokens(text)
        current_time = time.time()
        self._reset_if_necessary(current_time)

        limit = self.endpoint_limits.get(endpoint, self.endpoint_limits['default'])
        queue = self.endpoint_queues[endpoint if endpoint in self.endpoint_limits else 'default']

        queue.append((current_time, tokens))

        while queue and current_time - queue[0][0] >= 60:
            queue.popleft()

        if sum(tokens for _, tokens in queue) + tokens > limit:
            raise Exception(f"Rate limit exceeded for endpoint {endpoint}")

        total_tokens = sum(sum(tokens for _, tokens in q) for q in self.endpoint_queues.values())
        if total_tokens + tokens > self.total_tokens_per_minute:
            raise Exception("Total rate limit exceeded across all endpoints")

        self.usage_history.append(total_tokens)
        self._adjust_limits()

        return tokens

    def _reset_if_necessary(self, current_time):
        if current_time - self.last_reset >= 60:
            for queue in self.endpoint_queues.values():
                queue.clear()
            self.last_reset = current_time

    def _adjust_limits(self):
        if not self.usage_history:
            return
        
        avg_usage = sum(self.usage_history) / len(self.usage_history)
        if avg_usage > 0.9 * self.total_tokens_per_minute:
            self.endpoint_limits = {k: int(v * 0.9) for k, v in self.endpoint_limits.items()}
        elif avg_usage < 0.5 * self.total_tokens_per_minute:
            self.endpoint_limits = {k: min(int(v * 1.1), self.total_tokens_per_minute) for k, v in self.endpoint_limits.items()}