import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
import urllib.error
import datetime
import http.server
import socketserver

# Ensure UTF-8 printing on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Global Constants & Variables
CURRENT_PROFILE = ""
CONFIG_FILE = "config.json"
RULES_FILE = "rules.json"
CACHE_FILE = "sent_comments.json"
LOG_FILE = "auto_dm.log"
API_VERSION = "v20.0"

# --- Logging Helper ---
def log(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    try:
        print(formatted)
    except UnicodeEncodeError:
        try:
            print(formatted.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))
        except Exception:
            try:
                print(formatted.encode('ascii', errors='replace').decode('ascii'))
            except Exception:
                pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception as e:
        try:
            print(f"Error writing to log file: {e}")
        except Exception:
            pass

# --- Helper to load JSON files safely ---
def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"Error loading {filepath}: {e}")
    return default_value

# --- Helper to save JSON files ---
def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        log(f"Error saving {filepath}: {e}")
        return False

# --- Core Configuration Class ---
class InstagramBot:
    def __init__(self, profile=""):
        self.profile = profile or CURRENT_PROFILE
        self.config_file = f"config_{self.profile}.json" if self.profile else CONFIG_FILE
        self.cache_file = f"sent_comments_{self.profile}.json" if self.profile else CACHE_FILE
        self.rules_file = RULES_FILE
        self.log_file = f"auto_dm_{self.profile}.log" if self.profile else LOG_FILE

        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
        self.instagram_business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
        self.facebook_page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
        self.webhook_verify_token = os.environ.get("WEBHOOK_VERIFY_TOKEN", "my_secure_token")
        self.max_media_to_scan = int(os.environ.get("MAX_MEDIA_TO_SCAN", 20))
        self.max_comments_per_media = int(os.environ.get("MAX_COMMENTS_PER_MEDIA", 50))
        self.comment_lookback_hours = int(os.environ.get("COMMENT_LOOKBACK_HOURS", 24))

        # Load local config if env variables are not present
        self.load_local_config()
        self.rules = load_json_file(self.rules_file, [])
        self.sent_comments = load_json_file(self.cache_file, [])

    def load_local_config(self):
        config = load_json_file(self.config_file, {})
        if config:
            if not self.access_token:
                self.access_token = config.get("access_token", "")
            if not self.instagram_business_account_id:
                self.instagram_business_account_id = config.get("instagram_business_account_id", "")
            if not self.facebook_page_id:
                self.facebook_page_id = config.get("facebook_page_id", "")
            if self.webhook_verify_token == "my_secure_token":
                self.webhook_verify_token = config.get("webhook_verify_token", "my_secure_token")
            if not os.environ.get("MAX_MEDIA_TO_SCAN"):
                self.max_media_to_scan = config.get("max_media_to_scan", 20)
            if not os.environ.get("MAX_COMMENTS_PER_MEDIA"):
                self.max_comments_per_media = config.get("max_comments_per_media", 50)
            if not os.environ.get("COMMENT_LOOKBACK_HOURS"):
                self.comment_lookback_hours = config.get("comment_lookback_hours", 24)

    def save_local_config(self, config_data):
        self.access_token = config_data.get("access_token", "")
        self.instagram_business_account_id = config_data.get("instagram_business_account_id", "")
        self.facebook_page_id = config_data.get("facebook_page_id", "")
        self.webhook_verify_token = config_data.get("webhook_verify_token", "my_secure_token")
        self.max_media_to_scan = int(config_data.get("max_media_to_scan", 20))
        self.max_comments_per_media = int(config_data.get("max_comments_per_media", 50))
        self.comment_lookback_hours = int(config_data.get("comment_lookback_hours", 24))
        
        # Save to local file
        return save_json_file(self.config_file, config_data)

    def get_api_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    # --- HTTP Request Utility ---
    def make_request(self, url, method="GET", payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        
        req = urllib.request.Request(
            url,
            data=data,
            headers=self.get_api_headers(),
            method=method
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                return {
                    "success": True,
                    "status": response.status,
                    "data": json.loads(response.read().decode("utf-8"))
                }
        except urllib.error.HTTPError as e:
            try:
                error_body = e.read().decode("utf-8")
                error_data = json.loads(error_body)
            except Exception:
                error_data = {"error": {"message": f"HTTP error {e.code}"}}
            return {
                "success": False,
                "status": e.code,
                "error": error_data
            }
        except Exception as e:
            return {
                "success": False,
                "status": 500,
                "error": {"error": {"message": str(e)}}
            }

    # --- Test Credentials API Connection ---
    def test_connection(self):
        if not self.access_token or not self.instagram_business_account_id:
            return {"success": False, "message": "Missing Access Token or Instagram Business Account ID."}
        
        url = f"https://graph.facebook.com/{API_VERSION}/{self.instagram_business_account_id}?fields=username"
        res = self.make_request(url)
        if res["success"]:
            username = res["data"].get("username", "Unknown")
            log(f"Connection test successful: Authenticated as @{username}")
            return {
                "success": True,
                "username": username,
                "message": f"Successfully connected! Authenticated as @{username}."
            }
        else:
            err_msg = res["error"].get("error", {}).get("message", "API connection failed.")
            log(f"Connection test failed: {err_msg}")
            return {"success": False, "message": err_msg}

    # --- Fetch Username ---
    def get_self_username(self):
        url = f"https://graph.facebook.com/{API_VERSION}/{self.instagram_business_account_id}?fields=username"
        res = self.make_request(url)
        if res["success"]:
            return res["data"].get("username", "")
        else:
            err_msg = res.get("error", {}).get("error", {}).get("message", "Unknown Graph API error")
            log(f"API Error fetching self username: {err_msg}")
        return ""

    # --- Process a single comment ---
    def process_comment(self, comment, self_username):
        comment_id = comment.get("id")
        comment_text = comment.get("text", "")
        commenter_username = comment.get("username", "")

        # Skip if already processed
        if comment_id in self.sent_comments:
            return False

        # Skip if comment is made by the account itself to prevent endless loops
        if commenter_username == self_username or not commenter_username:
            return False

        # Skip if comment is older than lookback window (default 24 hours)
        timestamp_str = comment.get("timestamp")
        if timestamp_str:
            try:
                # Convert +HHMM or -HHMM offsets to +HH:MM / -HH:MM format for Python ISO parser compatibility
                if len(timestamp_str) >= 5 and (timestamp_str[-5] == "+" or timestamp_str[-5] == "-") and ":" not in timestamp_str[-4:]:
                    timestamp_str = timestamp_str[:-2] + ":" + timestamp_str[-2:]
                elif timestamp_str.endswith("Z"):
                    timestamp_str = timestamp_str[:-1] + "+00:00"
                
                comment_dt = datetime.datetime.fromisoformat(timestamp_str)
                current_dt = datetime.datetime.now(datetime.timezone.utc)
                age_seconds = (current_dt - comment_dt).total_seconds()
                
                max_age_seconds = self.comment_lookback_hours * 3600
                if age_seconds > max_age_seconds:
                    return False
            except Exception as e:
                log(f"Warning: Failed to parse comment timestamp '{timestamp_str}': {e}")

        log(f"New comment detected from @{commenter_username}: \"{comment_text}\"")

        # Normalize comment text for matching
        normalized_text = comment_text.lower().strip()
        matched_rule = None

        # Check keyword rules first
        for rule in self.rules:
            if not rule.get("active", False):
                continue
            if rule.get("trigger_type") == "keyword":
                keywords = [kw.lower().strip() for kw in rule.get("keywords", [])]
                # Check if any keyword matches
                if any(re.search(r'\b' + re.escape(kw) + r'\b', normalized_text) for kw in keywords):
                    matched_rule = rule
                    break

        # Fallback to universal catch-all rule if active and no keyword matched
        if not matched_rule:
            for rule in self.rules:
                if rule.get("active", False) and rule.get("trigger_type") == "all":
                    matched_rule = rule
                    break

        if matched_rule:
            log(f"Matched rule: \"{matched_rule.get('name')}\"")
            success = self.trigger_reply(comment_id, matched_rule, commenter_username)
            if success:
                # Add to processed cache
                self.sent_comments.append(comment_id)
                # Keep cache bounded to last 1000 items
                if len(self.sent_comments) > 1000:
                    self.sent_comments = self.sent_comments[-1000:]
                save_json_file(self.cache_file, self.sent_comments)
                return True
        else:
            # No matching active rule, but we still mark it processed so we don't scan it again
            log("No active matching rules found for this comment.")
            self.sent_comments.append(comment_id)
            if len(self.sent_comments) > 1000:
                self.sent_comments = self.sent_comments[-1000:]
            save_json_file(self.cache_file, self.sent_comments)
        
        return False

    # --- Send Public & Private Replies ---
    def trigger_reply(self, comment_id, rule, username):
        dm_template = rule.get("dm_template", "")
        public_reply_template = rule.get("public_reply_template", "")
        
        # Replace template placeholders
        dm_text = dm_template.replace("{username}", username)
        public_text = public_reply_template.replace("{username}", username)

        dm_success = False
        public_success = False

        # 1. Send Private DM Reply
        if dm_text and self.facebook_page_id:
            url = f"https://graph.facebook.com/{API_VERSION}/{self.facebook_page_id}/messages"
            payload = {
                "recipient": {"comment_id": comment_id},
                "message": {"text": dm_text}
            }
            res = self.make_request(url, method="POST", payload=payload)
            if res["success"]:
                log(f"-> Successfully sent DM to @{username}")
                dm_success = True
            else:
                err_msg = res["error"].get("error", {}).get("message", "Unknown error")
                log(f"-> Failed to send DM to @{username}: {err_msg}")
        else:
            log("-> Skipping DM reply (template empty or Page ID missing)")
            dm_success = True # Count as success if empty template is intended

        # 2. Send Public Comment Reply (Only if DM was sent successfully, or we skipped it)
        if dm_success and public_text:
            url = f"https://graph.facebook.com/{API_VERSION}/{comment_id}/replies"
            payload = {"message": public_text}
            res = self.make_request(url, method="POST", payload=payload)
            if res["success"]:
                log(f"-> Successfully replied publicly to @{username}")
                public_success = True
            else:
                err_msg = res["error"].get("error", {}).get("message", "Unknown error")
                log(f"-> Failed to reply publicly to @{username}: {err_msg}")
        else:
            public_success = True # Count as success if empty template is intended

        return dm_success and public_success

    # --- Polling Runner ---
    def run_polling(self):
        log("Starting Instagram comments polling...")
        
        if not self.access_token or not self.instagram_business_account_id:
            log("Error: Missing credentials (Access Token or Business Account ID). Aborting.")
            return {"success": False, "message": "Missing credentials."}

        self_username = self.get_self_username()
        if not self_username:
            log("Error: Could not retrieve own username. Invalid Access Token? Aborting.")
            return {"success": False, "message": "Could not connect to API."}

        log(f"Authenticated as @{self_username}. Scanning recent posts...")

        # 1. Get recent media with expanded comments
        url = f"https://graph.facebook.com/{API_VERSION}/{self.instagram_business_account_id}/media?fields=id,caption,permalink,timestamp,comments_count,comments{{id,text,username,timestamp}}&limit={self.max_media_to_scan}"
        res = self.make_request(url)
        if not res["success"]:
            err_msg = res["error"].get("error", {}).get("message", "Failed to retrieve media.")
            log(f"Error fetching media: {err_msg}")
            return {"success": False, "message": err_msg}

        media_list = res["data"].get("data", [])
        log(f"Found {len(media_list)} recent media posts/reels. Checking comments...")

        processed_count = 0
        replied_count = 0

        # 2. Iterate media and check comments
        for media in media_list:
            media_id = media.get("id")
            permalink = media.get("permalink", "")
            comments_count = media.get("comments_count", 0)
            log(f"Scanning media: {permalink} (Comments count: {comments_count})")

            if comments_count == 0:
                comments = []
            else:
                # Try to get comments from the expanded comments field
                comments_node = media.get("comments")
                if comments_node and "data" in comments_node:
                    comments = comments_node["data"]
                else:
                    # Fallback to individual request if comments weren't expanded
                    url_comments = f"https://graph.facebook.com/{API_VERSION}/{media_id}/comments?fields=id,text,username,timestamp&limit={self.max_comments_per_media}"
                    res_comments = self.make_request(url_comments)
                    if not res_comments["success"]:
                        log(f"Warning: Failed to fetch comments for media {media_id}")
                        continue
                    comments = res_comments["data"].get("data", [])

            for comment in comments:
                processed_count += 1
                if self.process_comment(comment, self_username):
                    replied_count += 1
                    # Small delay between API calls to avoid rate limits
                    time.sleep(1)

        summary = f"Polling complete. Scanned {processed_count} comments. Sent DMs for {replied_count} comments."
        log(summary)
        return {"success": True, "message": summary}

    # --- Webhook Request Handler ---
    def handle_webhook_payload(self, data):
        # We need to process incoming webhook events for instagram comments
        # Webhook formats: https://developers.facebook.com/docs/instagram-api/guides/webhooks/
        if data.get("object") != "instagram":
            return False

        entries = data.get("entry", [])
        self_username = self.get_self_username()

        replied_count = 0
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                field = change.get("field")
                value = change.get("value", {})
                
                # Check for comment events
                if field == "comments":
                    comment_id = value.get("id")
                    comment_text = value.get("text", "")
                    commenter_username = value.get("from", {}).get("username", "")

                    if comment_id and comment_text:
                        comment_obj = {
                            "id": comment_id,
                            "text": comment_text,
                            "username": commenter_username
                        }
                        if self.process_comment(comment_obj, self_username):
                            replied_count += 1
        
        return replied_count


# --- Web Webhook / Dashboard Server Handler ---
class DashboardAPIHandler(http.server.SimpleHTTPRequestHandler):
    profile = ""

    def __init__(self, *args, **kwargs):
        # Default web root is in "./web" directory
        web_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "web")
        super().__init__(*args, directory=web_dir, **kwargs)

    def do_GET(self):
        # Route APIs
        if self.path.startswith("/api/profile"):
            self.send_json({"profile": self.profile})
        elif self.path.startswith("/api/config"):
            bot = InstagramBot(profile=self.profile)
            self.send_json(load_json_file(bot.config_file, {}))
        elif self.path.startswith("/api/rules"):
            bot = InstagramBot(profile=self.profile)
            self.send_json(load_json_file(bot.rules_file, []))
        elif self.path.startswith("/api/sent_comments"):
            bot = InstagramBot(profile=self.profile)
            self.send_json(load_json_file(bot.cache_file, []))
        elif self.path.startswith("/api/logs"):
            bot = InstagramBot(profile=self.profile)
            logs = []
            if os.path.exists(bot.log_file):
                try:
                    with open(bot.log_file, "r", encoding="utf-8") as f:
                        # Return last 100 lines
                        logs = f.readlines()[-100:]
                except Exception as e:
                    logs = [f"Error reading logs: {e}"]
            self.send_json({"logs": [line.strip() for line in logs]})
        else:
            # Serve Static UI files
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Determine payload
        payload = {}
        if post_data:
            try:
                payload = json.loads(post_data)
            except Exception as e:
                self.send_json({"success": False, "message": f"Invalid JSON payload: {e}"}, status=400)
                return

        bot = InstagramBot(profile=self.profile)

        # Handle Webhook Callback Validation (GET is standard, but POST is webhook events)
        if self.path == "/webhook":
            # Process webhook notification
            replies = bot.handle_webhook_payload(payload)
            self.send_json({"success": True, "processed_replies": replies})
            return

        # Route Admin Dashboard APIs
        if self.path == "/api/config":
            success = bot.save_local_config(payload)
            if success:
                self.send_json({"success": True, "message": "Configuration saved successfully."})
            else:
                self.send_json({"success": False, "message": "Failed to save configuration."}, status=500)
        
        elif self.path == "/api/retrieve-tokens":
            app_id = payload.get("app_id", "").strip()
            app_secret = payload.get("app_secret", "").strip()
            user_token = payload.get("user_token", "").strip()
            
            if not app_id or not app_secret or not user_token:
                log("Token retrieval failed: Missing App ID, App Secret, or User Token.")
                self.send_json({"success": False, "message": "Missing App ID, App Secret, or User Token."}, status=400)
                return
            
            log(f"Exchanging short-lived user token for long-lived user token (App ID: {app_id})...")
            # Step 1: Exchange short-lived token for long-lived token
            exchange_url = f"https://graph.facebook.com/{API_VERSION}/oauth/access_token?grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&fb_exchange_token={user_token}"
            
            req = urllib.request.Request(exchange_url, method="GET")
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    long_lived_token = res_data.get("access_token")
            except urllib.error.HTTPError as e:
                try:
                    err_body = e.read().decode("utf-8")
                    err_data = json.loads(err_body)
                    err_msg = err_data.get("error", {}).get("message", f"HTTP error {e.code}")
                except Exception:
                    err_msg = f"HTTP error {e.code}"
                log(f"Token exchange failed: {err_msg}")
                self.send_json({"success": False, "message": f"Failed to exchange token: {err_msg}"}, status=400)
                return
            except Exception as e:
                log(f"Token exchange connection error: {str(e)}")
                self.send_json({"success": False, "message": f"Connection error: {str(e)}"}, status=500)
                return
                
            if not long_lived_token:
                log("Token exchange failed: No token returned in response.")
                self.send_json({"success": False, "message": "Failed to exchange token: No token returned in response."}, status=400)
                return
                
            log("Fetching Facebook pages and linked Instagram accounts...")
            # Step 2: Fetch user accounts
            accounts_url = f"https://graph.facebook.com/{API_VERSION}/me/accounts?fields=access_token,name,id,instagram_business_account{{id,username}}&access_token={long_lived_token}"
            req_accounts = urllib.request.Request(accounts_url, method="GET")
            try:
                with urllib.request.urlopen(req_accounts) as response:
                    accounts_data = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                try:
                    err_body = e.read().decode("utf-8")
                    err_data = json.loads(err_body)
                    err_msg = err_data.get("error", {}).get("message", f"HTTP error {e.code}")
                except Exception:
                    err_msg = f"HTTP error {e.code}"
                log(f"Accounts fetch failed: {err_msg}")
                self.send_json({"success": False, "message": f"Failed to fetch accounts: {err_msg}"}, status=400)
                return
            except Exception as e:
                log(f"Accounts fetch connection error: {str(e)}")
                self.send_json({"success": False, "message": f"Connection error: {str(e)}"}, status=500)
                return
                
            pages = accounts_data.get("data", [])
            results = []
            for p in pages:
                page_info = {
                    "page_name": p.get("name"),
                    "page_id": p.get("id"),
                    "page_access_token": p.get("access_token"),
                }
                ig_account = p.get("instagram_business_account")
                if ig_account:
                    page_info["instagram_account"] = {
                        "id": ig_account.get("id"),
                        "username": ig_account.get("username")
                    }
                results.append(page_info)
                
            log(f"Successfully discovered {len(results)} pages/accounts.")
            self.send_json({"success": True, "pages": results})
        
        elif self.path == "/api/rules":
            success = save_json_file(bot.rules_file, payload)
            if success:
                self.send_json({"success": True, "message": "Auto-DM rules saved successfully."})
            else:
                self.send_json({"success": False, "message": "Failed to save rules."}, status=500)
        
        elif self.path == "/api/sent_comments":
            success = save_json_file(bot.cache_file, payload)
            if success:
                self.send_json({"success": True, "message": "Cache database updated successfully."})
            else:
                self.send_json({"success": False, "message": "Failed to update cache database."}, status=500)
        
        elif self.path == "/api/test-connection":
            # Test bot connection with values provided in the request (allows testing before saving)
            temp_bot = InstagramBot()
            temp_bot.access_token = payload.get("access_token", temp_bot.access_token)
            temp_bot.instagram_business_account_id = payload.get("instagram_business_account_id", temp_bot.instagram_business_account_id)
            res = temp_bot.test_connection()
            if res["success"]:
                self.send_json(res)
            else:
                self.send_json(res, status=400)

        elif self.path == "/api/trigger-poll":
            res = bot.run_polling()
            if res["success"]:
                self.send_json(res)
            else:
                self.send_json(res, status=500)
        
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET_webhook_verify(self, params):
        # Verify Token validation endpoint for Meta Webhooks
        # Path query should contain hub.mode, hub.challenge, hub.verify_token
        mode = params.get("hub.mode", [""])[0]
        token = params.get("hub.verify_token", [""])[0]
        challenge = params.get("hub.challenge", [""])[0]

        bot = InstagramBot(profile=self.profile)
        if mode == "subscribe" and token == bot.webhook_verify_token:
            log("Webhook verification SUCCESSFUL!")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode("utf-8"))
        else:
            log("Webhook verification FAILED! Tokens did not match.")
            self.send_response(403)
            self.end_headers()

    # Override standard GET handler to support queries (like webhook challenge)
    def dispatch_get(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == "/webhook":
            # Handle Webhook challenges (GET method)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            self.do_GET_webhook_verify(query_params)
        else:
            # Fallback to default GET router
            self.do_GET()

    # Hook query parameters on GET
    def handle_one_request(self):
        try:
            # Redirect request validation to intercept URL params on GET
            super().handle_one_request()
        except Exception:
            pass

    # Wrap standard request router for queries support
    def send_json(self, data, status=200):
        response_bytes = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(response_bytes)

# Override GET in BaseServer class
class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

# Extend request parsing for webhook GET support
class CustomServerHandler(DashboardAPIHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == "/webhook":
            query_params = urllib.parse.parse_qs(parsed_url.query)
            self.do_GET_webhook_verify(query_params)
        else:
            super().do_GET()


# --- CLI Main Router ---
def main():
    global CURRENT_PROFILE, LOG_FILE

    if len(sys.argv) < 2:
        print("Instagram Auto-DM System")
        print("Usage:")
        print("  python auto_dm.py --poll        - Poll Instagram media for comments and reply")
        print("  python auto_dm.py --dashboard   - Run the local setup configuration panel")
        print("  python auto_dm.py --webhook     - Run the webhook listener server")
        print("Options:")
        print("  --port <number>                 - Custom port for servers (default: 8000)")
        print("  --profile <name>                - Active profile suffix for config/cache/logs")
        sys.exit(1)

    mode = sys.argv[1]
    port = 8000
    profile = ""
    
    # Parse port if provided
    if "--port" in sys.argv:
        try:
            port_index = sys.argv.index("--port")
            port = int(sys.argv[port_index + 1])
        except Exception:
            print("Error: Invalid port specified. Using default 8000.")

    # Parse profile if provided
    if "--profile" in sys.argv:
        try:
            profile_index = sys.argv.index("--profile")
            profile = sys.argv[profile_index + 1].strip()
        except Exception:
            print("Error: Invalid profile specified.")

    if profile:
        CURRENT_PROFILE = profile
        LOG_FILE = f"auto_dm_{profile}.log"

    bot = InstagramBot(profile=profile)

    if mode == "--poll":
        log("Execution Mode: Polling Scheduler")
        res = bot.run_polling()
        if not res["success"]:
            sys.exit(1)
            
    elif mode == "--webhook":
        log(f"Execution Mode: Webhook Server (Profile: {profile}, Port: {port})")
        log(f"Register webhook endpoint: http://your-domain-or-ngrok/webhook")
        log(f"Verification token: {bot.webhook_verify_token}")
        CustomServerHandler.profile = profile
        server = ThreadingHTTPServer(("0.0.0.0", port), CustomServerHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log("Webhook server stopped.")
            
    elif mode == "--dashboard":
        # Create web folders if not existing
        os.makedirs("web", exist_ok=True)
        log(f"Execution Mode: Setup Dashboard (Profile: {profile}, Port: {port})")
        log(f"Open browser and navigate to: http://localhost:{port}")
        CustomServerHandler.profile = profile
        server = ThreadingHTTPServer(("127.0.0.1", port), CustomServerHandler)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            log("Dashboard server stopped.")
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
