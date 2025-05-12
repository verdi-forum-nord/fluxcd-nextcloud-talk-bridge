#!/usr/bin/env python3
from flask import Flask, request, jsonify
import os
import json
import hmac
import hashlib
import base64
import requests
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
SHARED_SECRET = os.environ.get('SHARED_SECRET')

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    try:
        # Get the payload from FluxCD
        flux_data = request.json
        logger.info(f"Received webhook: {json.dumps(flux_data)}")

        # Extract relevant information
        severity = flux_data.get('severity', 'info')
        resource = flux_data.get('involvedObject', {})
        resource_kind = resource.get('kind', 'Unknown')
        resource_name = resource.get('name', 'Unknown')
        message = flux_data.get('message', 'No message provided')
        reason = flux_data.get('reason', 'Unknown')

        # Format message for Nextcloud Talk with some emoji for better visibility
        emoji_map = {
            'info': 'ℹ️',
            'error': '❌',
            'warning': '⚠️'
        }
        emoji = emoji_map.get(severity.lower(), '🔔')
        
        formatted_message = f"{emoji} *{severity.upper()}*: {resource_kind}/{resource_name}\n"
        formatted_message += f"*Reason*: {reason}\n\n"
        formatted_message += message

        # Send message to Nextcloud Talk
        result = send_nextcloud_talk_message(formatted_message)
        
        if result['success']:
            return jsonify({"status": "success", "message": "Notification sent to Nextcloud Talk"}), 200
        else:
            return jsonify({"status": "error", "message": result['error']}), 500
    
    except Exception as e:
        logger.exception("Error processing webhook")
        return jsonify({"status": "error", "message": str(e)}), 500

def send_nextcloud_talk_message(message, reply_to_id=None, reference_id=None, silent=False):
    """
    Send a message to a Nextcloud Talk room using the Bot API
    
    Args:
        message (str): Message content to send
        reply_to_id (int, optional): ID of message to reply to
        reference_id (str, optional): Reference string to identify message
        silent (bool, optional): Whether to send without notifications
        
    Returns:
        dict: Result with success status and error message if applicable
    """
    try:
        # Generate random string for signing
        random_bytes = os.urandom(64)
        random_string = base64.b64encode(random_bytes).decode('utf-8')
        
        # Prepare JSON payload
        payload = {"message": message}
        
        if reply_to_id:
            payload["replyTo"] = reply_to_id
            
        if reference_id:
            payload["referenceId"] = reference_id
            
        if silent:
            payload["silent"] = True
        
        # Create HMAC-SHA256 signature
        signature_input = random_string + message
        hmac_gen = hmac.new(
            SHARED_SECRET.encode('utf-8'),
            signature_input.encode('utf-8'),
            hashlib.sha256
        )
        signature = hmac_gen.hexdigest()
        
        # Set headers
        headers = {
            "Content-Type": "application/json",
            "OCS-APIRequest": "true",
            "Accept": "application/json",
            "X-Nextcloud-Talk-Bot-Random": random_string,
            "X-Nextcloud-Talk-Bot-Signature": signature
        }
        
        # Log what we're sending (for debugging)
        logger.info(f"Sending message to: {WEBHOOK_URL}")
        logger.info(f"Payload: {json.dumps(payload)}")
        logger.info(f"Random: {random_string}")
        logger.info(f"Signature: {signature}")
        
        # Make the request
        response = requests.post(
            WEBHOOK_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        # Check response
        response_data = response.json()
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response: {json.dumps(response_data)}")
        
        if response.status_code == 201 or (response_data.get('ocs', {}).get('meta', {}).get('status') == 'success'):
            return {"success": True}
        else:
            error_msg = f"Error {response.status_code}: {json.dumps(response_data)}"
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        logger.exception("Error sending Nextcloud Talk message")
        return {"success": False, "error": str(e)}

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    if not WEBHOOK_URL or not SHARED_SECRET:
        logger.error("Required environment variables WEBHOOK_URL and SHARED_SECRET must be set")
        exit(1)
        
    app.run(host='0.0.0.0', port=8080)