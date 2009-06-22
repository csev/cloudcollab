import urllib

from core import oauth

# example store for one of each thing
class BasicOAuthDataStore(oauth.OAuthDataStore):

    def __init__(self):
        self.consumer = oauth.OAuthConsumer('http://localhost:8083/oauth', 'secret')

    def lookup_consumer(self, key):
        if key == self.consumer.key:
            return self.consumer
        return None

    # We don't do request_tokens
    def lookup_token(self, token_type, token):
        return oauth.OAuthToken(None, None)

    # Trust all nonces
    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        return None

    # We don't do request_tokens
    def fetch_request_token(self, oauth_consumer):
        return None

    # We don't do request_tokens
    def fetch_access_token(self, oauth_consumer, oauth_token):
        return None

    # We don't do request_tokens
    def authorize_request_token(self, oauth_token, user):
        return None
