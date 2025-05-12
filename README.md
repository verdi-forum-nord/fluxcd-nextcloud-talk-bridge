# Flux CD Notification Controller `generic` (webhook) Alert Provider to Nextcloud Talk Bot bridge

TL;DR: This is the result of some iterations with GitHub Copilot to create a
simple answer to allow Flux sending notifications to Nextcloud Talk.

## Longer story

By using GitHub Copilot with the following prompt:

> create a bash script to send a message to a nextcloud talk room as a
> registered bot via webhook

Followed by another more specific prompt:

> According to the docs at <https://nextcloud-talk.readthedocs.io/en/latest/bots/>
> there is more to do, including generating an hmac to sign the contents. Have a
> look and update your suggestion!

A shell script got generated:

~~~bash
#!/bin/bash
# Script to send a message to a Nextcloud Talk room as a registered bot via webhook
# Usage: ./send_nextcloud_message.sh <webhook_url> "<message>" <shared_secret> [reply_to_id] [reference_id] [silent]

# Exit script if any command fails
set -e

# Check if required arguments are provided
if [ $# -lt 3 ]; then
    echo "Usage: $0 <webhook_url> \"<message>\" <shared_secret> [reply_to_id] [reference_id] [silent]"
    echo "Example: $0 https://nextcloud.example.com/ocs/v2.php/apps/spreed/api/v1/bot/<token>/message \"Hello from bot\" abcdef123456"
    echo ""
    echo "Parameters:"
    echo "  webhook_url   : URL for the bot webhook (format: https://nextcloud.example.com/ocs/v2.php/apps/spreed/api/v1/bot/<token>/message)"
    echo "  message       : The message to send"
    echo "  shared_secret : The shared secret used when the bot was installed"
    echo "  reply_to_id   : (Optional) ID of message to reply to"
    echo "  reference_id  : (Optional) A reference string to identify message (should be a random sha256)"
    echo "  silent        : (Optional) Set to 'true' to send without notifications"
    exit 1
fi

# Assign arguments to variables
WEBHOOK_URL="$1"
MESSAGE="$2"
SHARED_SECRET="$3"
REPLY_TO_ID="${4:-}"
REFERENCE_ID="${5:-}"
SILENT="${6:-false}"

# Check if webhook URL is valid
if [[ ! "$WEBHOOK_URL" =~ ^https?:// ]]; then
    echo "Error: Invalid webhook URL. It should start with http:// or https://"
    exit 1
fi

# Create a random string for signing
RANDOM_STRING=$(openssl rand -base64 64 | tr -d '\n')

# Prepare JSON payload
JSON_PAYLOAD="{"
JSON_PAYLOAD+="\"message\":\"$MESSAGE\""

# Add optional parameters if provided
if [ ! -z "$REPLY_TO_ID" ]; then
    JSON_PAYLOAD+=",\"replyTo\":$REPLY_TO_ID"
fi

if [ ! -z "$REFERENCE_ID" ]; then
    JSON_PAYLOAD+=",\"referenceId\":\"$REFERENCE_ID\""
fi

if [ "$SILENT" = "true" ]; then
    JSON_PAYLOAD+=",\"silent\":true"
fi

JSON_PAYLOAD+="}"

# Create HMAC-SHA256 signature
# Format: HMAC-SHA256(RANDOM + JSON_PAYLOAD, SHARED_SECRET)
SIGNATURE=$(echo -n "${RANDOM_STRING}${JSON_PAYLOAD}" | openssl dgst -sha256 -hmac "$SHARED_SECRET" | awk '{print $2}')

# Display what's being sent (for debugging)
echo "Sending message to Nextcloud Talk..."
echo "URL: $WEBHOOK_URL"
echo "Payload: $JSON_PAYLOAD"
echo "Random: $RANDOM_STRING"
echo "Signature: $SIGNATURE"

# Send the HTTP request
echo "Sending request..."
RESPONSE=$(curl -s -X POST \
     -H "Content-Type: application/json" \
     -H "OCS-APIRequest: true" \
     -H "Accept: application/json" \
     -H "X-Nextcloud-Talk-Bot-Random: $RANDOM_STRING" \
     -H "X-Nextcloud-Talk-Bot-Signature: $SIGNATURE" \
     -d "$JSON_PAYLOAD" \
     "$WEBHOOK_URL")

# Check for success
HTTP_CODE=$?

if [ $HTTP_CODE -eq 0 ]; then
    if [[ "$RESPONSE" == *"\"status\":\"success\""* || "$RESPONSE" == *"\"statuscode\":201"* ]]; then
        echo "Message sent successfully!"
        echo "Response: $RESPONSE"
        exit 0
    else
        echo "Error sending message."
        echo "Response: $RESPONSE"
        exit 1
    fi
else
    echo "Error: HTTP request failed with code $HTTP_CODE"
    exit 1
fi
~~~

It turned out, [only the `message` part of the JSON payload needs to be taken
into account when creating the HMAC
signature}(https://help.nextcloud.com/t/occ-talkinstall-which-url-cant-auth-to-send-msg-via-bot/178323/13)
though [the documentation states
differently](https://nextcloud-talk.readthedocs.io/en/latest/bots/#signing-and-verifying-requests):

~~~diff
@@ -58,7 +58,7 @@ JSON_PAYLOAD+="}"
 
 # Create HMAC-SHA256 signature
 # Format: HMAC-SHA256(RANDOM + JSON_PAYLOAD, SHARED_SECRET)
-SIGNATURE=$(echo -n "${RANDOM_STRING}${JSON_PAYLOAD}" | openssl dgst -sha256 -hmac "$SHARED_SECRET" | awk '{print $2}')
+SIGNATURE=$(echo -n "${RANDOM_STRING}${MESSAGE}" | openssl dgst -sha256 -hmac "$SHARED_SECRET" | awk '{print $2}')
 
 # Display what's being sent (for debugging)
 echo "Sending message to Nextcloud Talk..."
 ~~~

Following up another prompt to GitHub Copilot:

> Considering #file:send-nextcloud-talk-message.sh and
> <https://fluxcd.io/flux/components/notification/providers/> how to create a
> FluxCD Alert provider to send a message to a Nextcloud Talk room using the
> Bots Webhook API?

Asking:

> Where did you get your knowledge about 'FluxCD notification controller's
> "exec" proxy capability' from?

Getting a halluzinated answer, though again asking more specific:

> According to
> <https://fluxcd.io/flux/components/notification/providers/#https-proxy> the
> .spec.proxy field is only allowed to contain a http/https address. How do yo
> know that putting "exec" there results in running the command in the
> spec.exec.command?

GitHub Copilot regrets:

> You're absolutely right, and I made a significant error in my response. Thank
> you for pointing this out.
>
> After reviewing the documentation at
> <https://fluxcd.io/flux/components/notification/providers/#https-proxy> more
> carefully, I can see that I was incorrect. The .spec.proxy field is indeed
> only meant to contain an HTTP/HTTPS proxy address, not "exec" as I suggested.
>
> The FluxCD notification controller does not have an "exec" proxy capability as
> I incorrectly  stated. The documentation does not show any way to directly
> execute custom scripts as part of the notification process.
>
> I apologize for my mistake. My answer combined elements that don't actually
> exist in FluxCD's API and created a solution that wouldn't work as described.
>
> For integrating with Nextcloud Talk, you would need to:
>
> 1. Either use one of the existing provider types that FluxCD supports (like
>    generic webhooks)
> 2. Or create a separate service that acts as a bridge between FluxCD's
>    supported notification types and the Nextcloud Talk API I should have been
>    more accurate and not suggested capabilities that don't exist in the
>    FluxCD notification controller.

Following up with the prompts:

> I'd like to see you suggestion regarding "create a separate service that acts
> as a bridge between FluxCD's supported notification types and the Nextcloud
> Talk API". I'd go with the generic type and let the seperate service handle
> all the heavy lifting. Please suggest how to do so in a lightweight manner!

After getting a suggestion with a Python Flask webservice calling the Bash
script above and asking:

> Thanks a lot. As a follow up to your suggestion "Creating a Lightweight Bridge
> Service for FluxCD to Nextcloud Talk" can you integrate the functionality of
> the bash script into the python flask web service?

The script `app.py` got generated including some suggestions regarding a
`Dockerfile` and Kustomization examples.

**This is it.**
